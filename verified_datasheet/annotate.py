#!/usr/bin/env python3
"""
annotate.py — CLI for building LAYOUT verified datasheets (the per-vendor ground-truth
slice that calibrates the pipeline and measures Validator precision).

Design (see CLAUDE.md / project notes):
  * Worklist is SVD-KEYED: every (peripheral, register, field, key) cell the SVD defines
    is a row to fill. The diff joins on these keys, so no datasheet<->SVD name mapping.
  * Dedup: peripherals with derivedFrom (e.g. GPIOB..G <- GPIOA) are NOT re-annotated;
    you fill the prototype once and a `derived_from` marker row records the inheritance.
  * Keys (layout only; enums OUT): address_offset, reset_value, size  (register-level)
                                   bit_offset, bit_width, access      (field-level)
  * The SVD value is shown as a confirm-or-override DEFAULT for speed. The Generator
    (agent) value is NEVER shown during annotation — it is the system under test, so
    anchoring on it would poison the metric. (It may be loaded internally only to TARGET
    blind annotation at SVD-vs-agent disagreements, the bug-candidate cells.)
  * Navigation: the tool opens the FULL datasheet in Preview and, per register, drives
    Preview's Find (Cmd-F) to jump to the register name (the first match may be an overview
    mention, so use Cmd-G in Preview to step to the authoritative definition). macOS only;
    needs Accessibility + Automation permission for your terminal (granted once).
  * Provenance is recorded per cell: set_method in {human-verified, overridden, blind};
    status in {verified, datasheet-ambiguous, not-specified, skipped}.
  * --blind / --blind-sample / --blind-disagreements hide the SVD value so you transcribe
    from the page: an unanchored check that fast-confirming did not bias you.

Output is a SINGLE CSV (no sidecar files). Columns (superset of the legacy schema, so the
existing diff pipeline still reads `correct_value`): peripheral, register, field_name, key,
correct_value, svd_value, agent_value, status, page, set_method, derived_from. derivedFrom
peripherals appear as compact marker rows whose `derived_from` names the prototype.

Usage:
  # interactive (audit mode: SVD value shown as default; Preview opens + searches per register)
  python annotate.py --svd devices/stm/rm0041/svd/stm32f100.svd \
                     --pdf devices/stm/rm0041/rm0041.pdf \
                     --out verified_datasheet/stm/rm0041_stm32f100.csv

  # blind on a 15% sample (unanchored bias check)
  python annotate.py ... --blind-sample 0.15

  # blind specifically on bug-candidate cells (SVD disagrees with the generator)
  python annotate.py ... --agent-output agent_output/stm/rm0041/<run> --blind-disagreements

  # non-interactive sanity check (no annotation): worklist size, dedup, page-hit rate
  python annotate.py --svd ... --pdf ... --stats
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

# ---------------------------------------------------------------------------
# Terminal colors (disabled when not a TTY, or when NO_COLOR is set)
# ---------------------------------------------------------------------------
_COLOR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None
def _c(code):
    def wrap(s):
        return f"\033[{code}m{s}\033[0m" if _COLOR else str(s)
    return wrap
REG_C   = _c("96")   # register / field — bright cyan
KEY_C   = _c("93")   # invariant key — bright yellow
SVD_C   = _c("92")   # SVD value — bright green
DIM_C   = _c("2")    # counter / hint — dim
BLIND_C = _c("95")   # blind banner — bright magenta

REG_KEYS = ["address_offset", "reset_value", "size"]
FIELD_KEYS = ["bit_offset", "bit_width", "access"]
OUTPUT_FIELDS = [
    "peripheral", "register", "field_name", "alt_name", "key",
    "correct_value", "svd_value", "agent_value",
    "status", "page", "set_method", "derived_from",
]
STATUS_VERIFIED = "verified"
STATUS_AMBIGUOUS = "datasheet-ambiguous"
STATUS_NOTSPEC = "not-specified"
STATUS_SKIPPED = "skipped"
STATUS_DERIVED = "derived"  # marker rows for derivedFrom peripherals (not annotated)

# CMSIS-SVD access vocabulary, plus convenient shorthands.
ACCESS_VOCAB = {
    "read-write": "read-write", "rw": "read-write",
    "read-only": "read-only", "ro": "read-only", "r": "read-only",
    "write-only": "write-only", "wo": "write-only", "w": "write-only",
    "read-writeonce": "read-writeOnce", "rwo": "read-writeOnce",
    "writeonce": "writeOnce", "woo": "writeOnce",
}


# ---------------------------------------------------------------------------
# SVD parsing -> SVD-keyed worklist (with derivedFrom dedup + scope fallback)
# ---------------------------------------------------------------------------

def _strip_ns(root: ET.Element) -> ET.Element:
    for el in root.iter():
        if isinstance(el.tag, str) and "}" in el.tag:
            el.tag = el.tag.split("}", 1)[1]
    return root


def _text(el, tag, default=None):
    child = el.find(tag)
    return child.text.strip() if child is not None and child.text else default


def _strip_prefix(reg_name: str, periph_name: str) -> str:
    prefix = periph_name + "_"
    return reg_name[len(prefix):] if reg_name.startswith(prefix) else reg_name


def parse_svd_worklist(svd_path: str):
    """Return (cells, derived_map).

    cells: ordered list of dicts {peripheral, register, field_name, key, svd_value}
    derived_map: {derived_peripheral: prototype_peripheral}  (these are NOT in `cells`)
    Resolves size/resetValue/access through register -> peripheral -> device scope.
    """
    root = _strip_ns(ET.parse(svd_path).getroot())
    dev_size = _text(root, "size")
    dev_reset = _text(root, "resetValue")
    dev_access = _text(root, "access")

    peripherals = root.find("peripherals")
    if peripherals is None:
        raise ValueError(f"No <peripherals> in {svd_path}")

    cells = []
    derived_map = {}
    for periph in peripherals.findall("peripheral"):
        pname = (_text(periph, "name") or "").lower()
        if not pname:
            continue
        derived = periph.get("derivedFrom")
        if derived:
            derived_map[pname] = derived.lower()
            continue  # dedup: annotate the prototype only

        p_size = _text(periph, "size", dev_size)
        p_reset = _text(periph, "resetValue", dev_reset)
        p_access = _text(periph, "access", dev_access)

        regs_elem = periph.find("registers")
        if regs_elem is None:
            continue
        for reg in regs_elem.findall("register"):
            rname = _strip_prefix((_text(reg, "name") or "").lower(), pname)
            if not rname:
                continue
            addr = _text(reg, "addressOffset")
            reset = _text(reg, "resetValue", p_reset)
            size = _text(reg, "size", p_size)
            r_access = _text(reg, "access", p_access)

            reg_vals = {"address_offset": addr, "reset_value": reset, "size": size}
            for key in REG_KEYS:
                cells.append(dict(peripheral=pname, register=rname, field_name="",
                                  key=key, svd_value=reg_vals[key] or ""))

            fields_elem = reg.find("fields")
            if fields_elem is None:
                continue
            for field in fields_elem.findall("field"):
                fname = (_text(field, "name") or "").lower()
                if not fname:
                    continue
                bit_off = _text(field, "bitOffset")
                # bitRange "[hi:lo]" fallback if no bitOffset/bitWidth
                bit_w = _text(field, "bitWidth")
                if bit_off is None and _text(field, "bitRange"):
                    br = _text(field, "bitRange").strip("[]")
                    hi, lo = (p.strip() for p in br.split(":"))
                    bit_off, bit_w = lo, str(int(hi) - int(lo) + 1)
                access = _text(field, "access", r_access)
                fld_vals = {"bit_offset": bit_off, "bit_width": bit_w, "access": access}
                for key in FIELD_KEYS:
                    cells.append(dict(peripheral=pname, register=rname, field_name=fname,
                                      key=key, svd_value=fld_vals[key] or ""))
    return cells, derived_map


# ---------------------------------------------------------------------------
# Datasheet text index — pick a good search term + page hint (no external index)
# + agent values (internal, never shown)
# ---------------------------------------------------------------------------

_PDF_CACHE = {}  # pdf_path -> list of lowercased per-page texts


def _pdf_page_texts(pdf_path):
    """Lazily extract and cache per-page text from the datasheet PDF (once per session)."""
    if not pdf_path:
        return []
    if pdf_path in _PDF_CACHE:
        return _PDF_CACHE[pdf_path]
    texts = []
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(pdf_path)
        texts = [doc[i].get_text().lower() for i in range(doc.page_count)]
    except ImportError:
        pass  # no PyMuPDF -> no page hint / term ranking; search still works
    except Exception as e:
        print(f"  (could not read {pdf_path}: {e})")
    _PDF_CACHE[pdf_path] = texts
    return texts


def _search_terms(peripheral, register):
    """Datasheet identifiers to look for, most specific first. Handles indexed peripherals
    (TIM1 -> TIMx) because datasheets describe shared registers with a generic name."""
    p, r = peripheral.upper(), register.upper()
    px = re.sub(r"\d+$", "x", p)  # TIM1 -> TIMx, USART2 -> USARTx
    terms = []
    for t in (f"{p}_{r}", f"{px}_{r}", f"{p} {r}", f"{px} {r}", r):
        if t and t not in terms:
            terms.append(t)
    return terms


def best_search_term(pdf_path, peripheral, register):
    """The most specific identifier from `_search_terms` that actually appears in the PDF,
    so Preview's Find lands on something. Falls back to PERIPH_REG."""
    texts = _pdf_page_texts(pdf_path)
    terms = _search_terms(peripheral, register)
    if texts:
        for t in terms:
            if any(t.lower() in tx for tx in texts):
                return t
    return terms[0]


def candidate_pages(pdf_path, peripheral, register, max_pages=6):
    """Pages that mention the register (a hint shown in the prompt + best-effort provenance).
    Empty if no PDF text / no match."""
    texts = _pdf_page_texts(pdf_path)
    if not texts:
        return []
    for term in (t.lower() for t in _search_terms(peripheral, register)):
        hits = [i + 1 for i, txt in enumerate(texts) if term in txt]
        if hits:
            return hits[:max_pages]
    return []


def load_agent_values(agent_output_dir):
    """Map (peripheral, register, field_name, key) -> agent value. Used ONLY to target
    blind annotation at disagreements; never displayed."""
    if not agent_output_dir or not os.path.isdir(agent_output_dir):
        return {}
    vals = {}
    for fn in os.listdir(agent_output_dir):
        fp = os.path.join(agent_output_dir, fn)
        if os.path.isdir(fp) or "_" not in fn or fn.endswith(".csv"):
            continue
        if fn.startswith(("summary", "usage", "reasoning")):
            continue
        periph, _, reg = fn.partition("_")
        try:
            data = json.load(open(fp))
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        p, r = periph.lower(), reg.lower()
        vals[(p, r, "", "address_offset")] = str(data.get("address_offset", ""))
        vals[(p, r, "", "reset_value")] = str(data.get("reset_value", ""))
        vals[(p, r, "", "size")] = str(data.get("size", ""))
        for sf in data.get("subfields", []) or []:
            bn = sf.get("bit_number", {}) or {}
            lo = min(bn.get("start_bit", 0), bn.get("end_bit", 0))
            w = abs(bn.get("end_bit", 0) - bn.get("start_bit", 0)) + 1
            fn_ = (sf.get("name", "") or "").lower()
            vals[(p, r, fn_, "bit_offset")] = str(lo)
            vals[(p, r, fn_, "bit_width")] = str(w)
    return vals


# ---------------------------------------------------------------------------
# Value canonicalization (overrides only; confirms keep the SVD's literal value)
# ---------------------------------------------------------------------------

def canonical(key, value):
    v = (value or "").strip()
    if v == "":
        return v
    if key in ("address_offset", "reset_value"):
        try:
            n = int(v, 0)
            return f"0x{n:x}"
        except ValueError:
            return v
    if key in ("size", "bit_offset", "bit_width"):
        try:
            return str(int(v, 0))
        except ValueError:
            return v
    if key == "access":
        return ACCESS_VOCAB.get(v.lower().replace("_", "-").replace(" ", ""), v)
    return v


# ---------------------------------------------------------------------------
# CSV load/save (atomic, resumable)
# ---------------------------------------------------------------------------

def cell_id(row):
    return (row["peripheral"], row["register"], row.get("field_name", ""), row["key"])


def load_existing(out_path):
    """Return {cell_id: row}. Rows with a non-empty correct_value but no status are
    treated as already-verified (imported) so a partially-built CSV resumes cleanly."""
    rows = {}
    if not os.path.exists(out_path):
        return rows
    with open(out_path, newline="") as f:
        for row in csv.DictReader(f):
            row = {k: (row.get(k) or "") for k in OUTPUT_FIELDS} | {
                "peripheral": (row.get("peripheral") or "").lower(),
                "register": (row.get("register") or "").lower(),
                "field_name": (row.get("field_name") or "").lower(),
                "key": row.get("key") or "",
            }
            if row["correct_value"] and not row["status"]:
                row["status"] = STATUS_VERIFIED
                row["set_method"] = row.get("set_method") or "imported"
            rows[cell_id(row)] = row
    return rows


def load_rows_ordered(out_path):
    """Return all rows from an existing CSV in file order, normalized to OUTPUT_FIELDS.

    Unlike load_existing (keyed by cell_id), this preserves the file verbatim: row
    order, manually-renamed field_names, deletions, and any rows the user added. Once
    the CSV exists it is the ground truth — the SVD is only used to seed it the first
    time, so the worklist is rebuilt from the CSV, not re-derived from the SVD."""
    rows = []
    with open(out_path, newline="") as f:
        for row in csv.DictReader(f):
            row = {k: (row.get(k) or "") for k in OUTPUT_FIELDS} | {
                "peripheral": (row.get("peripheral") or "").lower(),
                "register": (row.get("register") or "").lower(),
                "field_name": (row.get("field_name") or "").lower(),
                "key": row.get("key") or "",
            }
            if row["correct_value"] and not row["status"]:
                row["status"] = STATUS_VERIFIED
                row["set_method"] = row.get("set_method") or "imported"
            rows.append(row)
    return rows


def save_atomic(out_path, rows):
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(out_path) or ".", suffix=".tmp")
    with os.fdopen(fd, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in OUTPUT_FIELDS})
    os.replace(tmp, out_path)


# ---------------------------------------------------------------------------
# Open the FULL datasheet in Preview + drive its Find (Cmd-F) to a term.
# macOS only; needs Accessibility + Automation permission (prompted once).
# ---------------------------------------------------------------------------

def open_pdf_in_preview(pdf_path):
    """Open the whole datasheet in Preview once, so per-register searches are fast/warm."""
    if not pdf_path:
        print("  (no --pdf given — open the datasheet yourself)")
        return False
    cmd = ["open", "-a", "Preview", pdf_path] if sys.platform == "darwin" else ["xdg-open", pdf_path]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            print(f"  (could not open PDF: {r.stderr.strip() or r.returncode})")
            return False
        return True
    except FileNotFoundError:
        print("  (viewer not found; open the PDF manually)")
        return False


_ACCESSIBILITY = None  # cached: may this process synthesize keystrokes into other apps?


def accessibility_enabled():
    """Whether the controlling terminal has Accessibility permission (needed to auto-drive
    Preview's Find via synthesized keystrokes). Cached; macOS only."""
    global _ACCESSIBILITY
    if _ACCESSIBILITY is None:
        if sys.platform != "darwin":
            _ACCESSIBILITY = False
        else:
            try:
                r = subprocess.run(
                    ["osascript", "-e", 'tell application "System Events" to return UI elements enabled'],
                    capture_output=True, text=True)
                _ACCESSIBILITY = (r.returncode == 0 and r.stdout.strip().lower() == "true")
            except Exception:
                _ACCESSIBILITY = False
    return _ACCESSIBILITY


def _copy_to_clipboard(text):
    if sys.platform != "darwin":
        return False
    try:
        subprocess.run(["pbcopy"], input=text, text=True)
        return True
    except Exception:
        return False


def preview_find(term):
    """Jump Preview to `term`. Always copies the term to the clipboard (so you can press ⌘F
    then ⌘V — no typing) and, when the terminal has Accessibility permission, also drives
    Preview's Find automatically. The first match may be an overview mention — ⌘G steps on."""
    if sys.platform != "darwin" or not term:
        return
    copied = _copy_to_clipboard(term)
    if accessibility_enabled() and copied:
        # Open Find, select+replace any existing (possibly stale) text by PASTING the term
        # we just put on the clipboard, then search. Paste avoids mistypes and stale text.
        script = '''
        tell application "Preview" to activate
        delay 0.6
        tell application "System Events"
            tell process "Preview"
                set frontmost to true
                delay 0.3
                keystroke "f" using command down
                delay 0.4
                keystroke "a" using command down
                delay 0.1
                keystroke "v" using command down
                delay 0.2
                key code 36
            end tell
        end tell
        '''
        try:
            r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
            if r.returncode == 0:
                print(f"  -> searched Preview for \"{term}\"  (⌘G for the next match)")
                return
            msg = (r.stderr or "").strip().splitlines()
            print(f"  (auto-search failed: {msg[-1] if msg else 'unknown'})")
        except FileNotFoundError:
            pass
    if copied:
        print(f"  \"{term}\" copied — in Preview press ⌘F then ⌘V ↵ (replaces any old search)  (⌘G for next)")
    else:
        print(f"  search Preview (⌘F) for \"{term}\"")


# ---------------------------------------------------------------------------
# Blind selection
# ---------------------------------------------------------------------------

def is_blind(cell, args, agent_vals):
    if args.blind:
        return True
    if args.blind_disagreements and agent_vals:
        av = agent_vals.get(cell_id(cell), None)
        if av is not None and canonical(cell["key"], av) != canonical(cell["key"], cell["svd_value"]):
            return True
    if args.blind_sample > 0:
        h = hashlib.sha1(repr(cell_id(cell)).encode()).hexdigest()
        if (int(h[:8], 16) / 0xFFFFFFFF) < args.blind_sample:
            return True
    return False


# ---------------------------------------------------------------------------
# Interactive loop
# ---------------------------------------------------------------------------

def print_command_key():
    """The per-cell command legend, shown at session start and on `?`."""
    print("Commands (per cell):")
    print("  Enter    confirm the shown SVD value")
    print("  <value>  type a different value (override; canonicalized)")
    print("  f        re-run Preview's Find for this register (⌘G steps to next match)")
    print("  a        mark datasheet-ambiguous")
    print("  n        mark not-specified in the datasheet")
    print("  pn       mark the WHOLE peripheral not-specified (all its pending cells; e.g. NVIC mentioned but not detailed)")
    print("  r        record the datasheet's name for this field/register (alias; keeps SVD key)")
    print("  s        skip (leave pending for later)")
    print("  q        save and quit")
    print("  ?        show this command key")
    print("  (blind mode: SVD value hidden — Enter re-searches; type the value you read)")


def plan_order(rows, spread):
    """Order this session's pending cells for presentation.

    spread == 0 (default): worklist order — finish peripheral by peripheral.
    spread == N > 0: equalize-then-round-robin across peripherals, by COMPLETION PROPORTION,
    completing ONE WHOLE register at a time, until at least N cells are planned.

    Each step serves the peripheral with the LOWEST completion proportion (already-done +
    planned-this-session, over its total cells) its next whole register. When proportions are
    uneven this first lifts the laggards up to parity (a peripheral already further along is
    not served until the others catch up to it); once even it naturally round-robins. So a
    partial session leaves every peripheral at roughly the same completion, not just the first
    few finished. Registers stay whole (one Preview jump); the cap is honoured at the register
    boundary, so the plan may run a little past N rather than split a register.
    """
    from collections import OrderedDict
    pending = [r for r in rows if not r["status"]]
    if not spread:
        return pending

    # per-peripheral totals and already-done counts (from the full worklist, in order)
    total, done, order = OrderedDict(), {}, {}
    for r in rows:
        if not r["register"] or r["status"] == STATUS_DERIVED:
            continue
        p = r["peripheral"]
        if p not in total:
            total[p], done[p], order[p] = 0, 0, len(order)
        total[p] += 1
        if r["status"]:
            done[p] += 1

    # per-peripheral queues of pending register-chunks, in worklist order
    buckets = OrderedDict()
    for r in pending:
        buckets.setdefault(r["peripheral"], OrderedDict()).setdefault(r["register"], []).append(r)
    queues = {p: list(regs.values()) for p, regs in buckets.items()}

    planned = dict(done)                       # done count grows as we plan registers
    plan = []
    while len(plan) < spread:
        cands = [p for p in queues if queues[p]]
        if not cands:
            break
        # lowest completion proportion first; stable tie-break by worklist order (round-robin)
        p = min(cands, key=lambda p: (planned[p] / total[p], order[p]))
        chunk = queues[p].pop(0)               # this peripheral's next WHOLE register
        plan.extend(chunk)
        planned[p] += len(chunk)
    return plan                                # whole registers only — never truncated mid-register


def _marker_rows(derived_map):
    """One compact row per derivedFrom peripheral (never annotated). The diff expands it
    against the prototype's verified rows."""
    out = []
    for derived_p, proto_p in derived_map.items():
        row = {k: "" for k in OUTPUT_FIELDS}
        row["peripheral"] = derived_p
        row["derived_from"] = proto_p
        row["status"] = STATUS_DERIVED
        out.append(row)
    return out


def annotate(cells, derived_map, args):
    agent_vals = load_agent_values(args.agent_output)
    csv_exists = os.path.exists(args.out) and os.path.getsize(args.out) > 0

    if csv_exists:
        # The CSV is the ground truth once it exists. Load it verbatim (order, renames,
        # deletions, added rows preserved); do NOT re-derive the row set from the SVD.
        all_rows = load_rows_ordered(args.out)
        markers = [r for r in all_rows if r["status"] == STATUS_DERIVED]
        rows = [r for r in all_rows if r["status"] != STATUS_DERIVED]
    else:
        # First run: seed the worklist from the SVD.
        rows = []
        for c in cells:
            row = {k: "" for k in OUTPUT_FIELDS}
            row.update({k: c[k] for k in ("peripheral", "register", "field_name", "key")})
            row["svd_value"] = c["svd_value"]
            rows.append(row)
        markers = _marker_rows(derived_map)   # appended at save time; not annotated

    pending = [r for r in rows if not r["status"]]
    plan = plan_order(rows, args.spread)      # CLI presentation order only; file stays grouped
    print(f"\nWorklist: {len(rows)} cells across {len({(r['peripheral'], r['register']) for r in rows})} "
          f"registers (dedup hid {len(markers)} derived peripherals, kept as marker rows)."
          + ("  [source: existing CSV]" if csv_exists else "  [source: SVD — first run]"))
    print(f"Already done: {len(rows) - len(pending)}.  To annotate: {len(pending)}.")
    if args.spread:
        print(f"Spread mode: this session presents {len(plan)} cells round-robin across "
              f"{len({r['peripheral'] for r in plan})} peripherals "
              f"(of {len({r['peripheral'] for r in pending})} with pending cells); file order unchanged.")
    print()
    print_command_key()

    open_preview = bool(args.pdf) and not args.no_open
    if open_preview:
        open_pdf_in_preview(args.pdf)
        if accessibility_enabled():
            print("Per register the tool drives Preview's Find to the register name (also copied to the")
            print("clipboard — ⌘F ⌘V if the jump misses). First match may be an overview mention; ⌘G steps on.")
        else:
            print("Per register the register name is copied to the clipboard — in Preview press ⌘F then")
            print("⌘V ↵ (⌘G for next match). For fully automatic search, grant your terminal Accessibility")
            print("in System Settings ▸ Privacy & Security ▸ Accessibility, then restart it.")
    print()

    def _save():
        save_atomic(args.out, rows + markers)

    last_register = None
    for i, r in enumerate(plan, 1):
        if r["status"]:        # a bulk op (pn) earlier this session already resolved this cell
            continue
        pages = candidate_pages(args.pdf, r["peripheral"], r["register"])  # hint + provenance
        term = best_search_term(args.pdf, r["peripheral"], r["register"])
        blind = is_blind(r, args, agent_vals)

        reg_id = (r["peripheral"], r["register"])
        if reg_id != last_register and open_preview:
            preview_find(term)
        last_register = reg_id

        label = REG_C(f"{r['peripheral']}.{r['register']}") + (
            "." + REG_C(r["field_name"]) if r["field_name"] else "")
        hint = f"find: {term}" + (f" · pp.{','.join(map(str, pages[:6]))}" if pages else "")
        while True:
            alias = f"  {DIM_C('datasheet name: ' + r['alt_name'])}" if r.get("alt_name") else ""
            print(f"{DIM_C(f'[{i}/{len(plan)}]')}  {label}  :  {KEY_C(r['key'])}   {DIM_C(f'({hint})')}{alias}")
            if blind:
                prompt = f"  {BLIND_C('BLIND')} — read the page, enter value> "
            else:
                prompt = f"  SVD: {SVD_C(repr(r['svd_value']))}   {DIM_C('[Enter=confirm / value / f a n pn r s q]')} > "
            try:
                ans = input(prompt)
            except (EOFError, KeyboardInterrupt):
                print("\nSaving and quitting.")
                _save(); return
            cmd = ans.strip()

            if cmd == "?":                              # show the command key, re-prompt this cell
                print_command_key(); continue
            if cmd == "r":                              # record the datasheet's alias for this field/register
                what = f"{r['register']}.{r['field_name']}" if r["field_name"] else r["register"]
                svd_name = r["field_name"] or r["register"]
                cur = f" (currently {r['alt_name']!r})" if r.get("alt_name") else ""
                try:
                    alias = input(f"  datasheet's name for {what}{cur}, SVD says {svd_name!r}: ").strip()
                except (EOFError, KeyboardInterrupt):
                    print(); alias = ""
                if alias:
                    sib = (r["peripheral"], r["register"], r["field_name"])  # all cells of this field/register
                    n = 0
                    for x in rows:
                        if (x["peripheral"], x["register"], x["field_name"]) == sib:
                            x["alt_name"] = alias
                            n += 1
                    _save()
                    print(f"  recorded datasheet name {alias!r} for {what}  ({n} cells; SVD key unchanged)")
                else:
                    print("  (no alias entered — unchanged)")
                continue
            if cmd == "pn":                             # bulk: whole peripheral not-specified
                p = r["peripheral"]
                targets = [x for x in rows if x["peripheral"] == p and not x["status"]]
                try:
                    ok = input(f"  mark all {len(targets)} pending cells of {REG_C(p.upper())} "
                               f"as not-specified? [y/N] ").strip().lower()
                except (EOFError, KeyboardInterrupt):
                    print(); ok = ""
                if ok == "y":
                    method = "blind" if blind else "human-verified"
                    for x in targets:
                        x["status"], x["set_method"] = STATUS_NOTSPEC, method
                    _save()
                    print(f"  marked {len(targets)} cells of {p.upper()} not-specified.")
                    break                                # this cell is resolved; loop-skip handles the rest
                print("  (cancelled)")
                continue
            if cmd == "f" or (cmd == "" and blind):     # re-search (blank-in-blind is not a value)
                preview_find(term); continue
            if cmd == "q":
                _save()
                print(f"\nSaved {args.out}. Done: {sum(1 for x in rows if x['status'])}/{len(rows)}.")
                return
            if cmd == "a":
                r["status"], r["set_method"] = STATUS_AMBIGUOUS, "blind" if blind else "human-verified"
            elif cmd == "n":
                r["status"], r["set_method"] = STATUS_NOTSPEC, "blind" if blind else "human-verified"
            elif cmd == "s":
                break  # leave status empty -> remains pending
            elif cmd == "" and not blind:
                r["correct_value"] = r["svd_value"]
                r["status"] = STATUS_VERIFIED
                r["set_method"] = "human-verified"
            else:  # a typed value (override, or the blind answer)
                r["correct_value"] = canonical(r["key"], cmd)
                r["status"] = STATUS_VERIFIED
                r["set_method"] = "blind" if blind else "overridden"
            r["page"] = str(pages[0]) if pages else ""   # best-effort: first page mentioning the register
            _save()
            break

    _save()
    print(f"\nComplete. {sum(1 for x in rows if x['status'])}/{len(rows)} cells. Saved {args.out}.")


# ---------------------------------------------------------------------------
# Stats (non-interactive sanity check)
# ---------------------------------------------------------------------------

def stats(cells, derived_map, args):
    regs = {(c["peripheral"], c["register"]) for c in cells}
    if args.pdf:
        with_pages = sum(1 for (p, r) in regs if candidate_pages(args.pdf, p, r))
        page_hit = f"{with_pages}/{len(regs)} registers found in the PDF text (search-term hit)"
    else:
        page_hit = "n/a (pass --pdf to check search-term hit rate)"
    by_key = {}
    for c in cells:
        by_key[c["key"]] = by_key.get(c["key"], 0) + 1
    print(f"cells:        {len(cells)}")
    print(f"registers:    {len(regs)}")
    print(f"peripherals:  {len({p for p, _ in regs})} annotated + {len(derived_map)} derived (deduped)")
    print(f"derived_map:  {derived_map}")
    print(f"cells/key:    {by_key}")
    print(f"pdf-hit:      {page_hit}")
    print("\nsample cells:")
    for c in cells[:8]:
        lbl = f"{c['peripheral']}.{c['register']}" + (f".{c['field_name']}" if c["field_name"] else "")
        print(f"  {lbl:34} {c['key']:14} svd={c['svd_value']!r}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Build a layout verified datasheet from an SVD worklist (blind/audit).")
    ap.add_argument("--svd", required=True)
    ap.add_argument("--pdf", default="", help="datasheet PDF — opened in Preview; per-register Find jumps to the register")
    ap.add_argument("--out", default="")
    ap.add_argument("--agent-output", default="", help="dir of generator JSON (only to target blind at disagreements; never shown)")
    ap.add_argument("--blind", action="store_true", help="hide SVD value for ALL cells")
    ap.add_argument("--blind-sample", type=float, default=0.0, help="hide SVD value for a deterministic fraction (0..1)")
    ap.add_argument("--blind-disagreements", action="store_true", help="hide SVD value where the generator disagrees with the SVD")
    ap.add_argument("--no-open", action="store_true", help="do not open Preview / run searches")
    ap.add_argument("--spread", type=int, default=0, metavar="N",
                    help="annotate up to N pending cells this session, round-robin across ALL "
                         "peripherals so a partial run touches every peripheral (breadth-first)")
    ap.add_argument("--stats", action="store_true", help="print worklist stats and exit (no annotation)")
    args = ap.parse_args()

    if args.stats:
        cells, derived_map = parse_svd_worklist(args.svd)
        stats(cells, derived_map, args)
        return
    if not args.out:
        ap.error("--out is required for annotation (use --stats for a dry run)")
    if not args.pdf and not args.no_open:
        print("(no --pdf given; Preview won't open and there's no register search. add --no-open to silence.)")
    # The CSV is the ground truth once it exists; only parse the SVD to seed a new file.
    if os.path.exists(args.out) and os.path.getsize(args.out) > 0:
        cells, derived_map = [], {}
    else:
        cells, derived_map = parse_svd_worklist(args.svd)
    annotate(cells, derived_map, args)


if __name__ == "__main__":
    main()
