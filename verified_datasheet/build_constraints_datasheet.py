#!/usr/bin/env python3
"""
build_constraints_datasheet.py — seed the verified-CONSTRAINTS datasheet from the
extraction corpus (plan §7.2: the "separate dependency-verified file" that
verified_datasheet/README.md reserves as the escape from its layout-only scope).

What it does:
  * Walks a corpus root shaped like  <corpus_root>/<rm>/<run>/{peripheral}_{register}
    (e.g. hal_agent-phase-1d/agent_output/stm) and pulls every entry of each
    register file's "access_constraints" list (v1 schema).
  * Dedups to ONE ROW PER UNIQUE CONSTRAINT PER REFERENCE MANUAL. Dedup key:
      (reference_manual, target_register, target_operation,
       sorted preconditions, sorted postconditions, datasheet_text)
    dup_count records how many raw occurrences (across runs, peripheral
    instances, and per-bit fan-out) collapsed into the row; source_file is the
    first-seen example. `id` = first 12 hex chars of sha256 over the dedup key,
    so it is stable across rebuilds.
  * Derives mechanical, informational lint_flags (off-vocab op/state, empty
    conditions, %s placeholder names, >3 postconditions, w1c / read-to-clear
    text patterns). They stratify annotation; they are NOT judgments.
  * Is re-runnable/idempotent: on rebuild, existing annotations are preserved
    (matched by id; a non-empty status/note is never clobbered), machine columns
    are refreshed, new rows are added, and rows whose id no longer appears in
    the corpus are kept untouched.

BLINDNESS RULE (plan §7.2): the CSV carries generator output + provenance + the
mechanical lint flags above and NOTHING else — no LLM-validator verdict of any
kind may ever appear in or near this file. The builder therefore reads only the
register files themselves (subdirectories such as validator/ and info/ inside
run dirs are skipped wholesale).

Usage:
  python3 verified_datasheet/build_constraints_datasheet.py \
      /home/ramla/hal_agent-phase-1d/agent_output/stm \
      [--out verified_datasheet/constraints/stm.csv]

Annotate the result with verified_datasheet/annotate_constraints.py.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import tempfile
from collections import Counter

# Column order is the schema (see constraints/README.md). Machine columns first,
# then the two human annotation columns.
COLUMNS = [
    "id", "reference_manual", "run", "source_file", "peripheral", "register",
    "target_operation", "target_fields", "preconditions", "postconditions",
    "severity", "consequence", "datasheet_text", "dup_count", "lint_flags",
    "status", "note",
]

# status vocabulary (written by annotate_constraints.py; empty = unannotated)
STATUS_CONFIRMED = "confirmed"          # genuine constraint, encoding faithful (TP)
STATUS_ENCODING_ERROR = "encoding_error"  # real constraint, wrong/incomplete encoding
STATUS_NOT_CONSTRAINT = "not_constraint"  # quoted text is not an access/ordering requirement (FP)
STATUS_QUOTE_MISSING = "quote_missing"  # quote not found in the manual
STATUS_UNSURE = "unsure"
STATUSES = [STATUS_CONFIRMED, STATUS_ENCODING_ERROR, STATUS_NOT_CONSTRAINT,
            STATUS_QUOTE_MISSING, STATUS_UNSURE]

OP_VOCAB = {"write", "read", "modify"}

# run-dir entries that are not register files
SKIP_PREFIXES = ("summary", "usage", "reasoning")
SKIP_SUFFIXES = (".csv", ".txt", ".json")

_EQUALS_NUMERIC = re.compile(r"^(0[xX][0-9a-fA-F]+|0[bB][01]+|[0-9]+)$")

_Q = "['\"‘’“”]"  # straight + smart quotes around a literal 1
W1C_PATTERNS = [  # write-1-to-clear / cleared-by-writing phrasings
    re.compile(rf"writ\w*\s+(?:a\s+)?{_Q}?1{_Q}?\b[^.;]{{0,60}}?\bclear", re.I),
    re.compile(r"clear(?:ed|s)?\s+by\s+(?:software\s+)?writ\w*", re.I),
    re.compile(rf"reset\s+by\s+writ\w*\s+(?:a\s+)?{_Q}?1{_Q}?", re.I),
    re.compile(r"\brc_w1\b|\bw1c\b", re.I),
]
READ_CLEAR_PATTERNS = [  # flag cleared after/by a read
    re.compile(r"clear(?:ed|s)?\s+(?:by|after|on|when|following)\b[^.;]{0,60}?\bread", re.I),
    re.compile(r"\bread(?:ing)?\b[^.;]{0,60}?\bclear(?:s|ed)?\b", re.I),
    re.compile(r"reset\s+by\s+(?:a\s+)?read", re.I),
]


# ---------------------------------------------------------------------------
# Dedup key + stable id
# ---------------------------------------------------------------------------

def _cond_triples(conds):
    """Order-independent (register, field, state) triples for one condition list."""
    trips = []
    for c in conds or []:
        if isinstance(c, dict):
            trips.append([str(c.get("register_name", "")),
                          str(c.get("field_name", "")),
                          str(c.get("required_state", ""))])
        else:  # malformed entry — keep it distinguishable rather than dropping it
            trips.append(["", "", str(c)])
    return sorted(trips)


def dedup_key(rm: str, ac: dict):
    """One row per unique constraint per reference manual (plan §7.2)."""
    return [
        rm,
        str(ac.get("target_register", "")),
        str(ac.get("target_operation", "")),
        _cond_triples(ac.get("preconditions")),
        _cond_triples(ac.get("postconditions")),
        str(ac.get("datasheet_text", "")),
    ]


def constraint_id(key) -> str:
    """First 12 hex chars of sha256 over the canonical key — stable across rebuilds."""
    blob = json.dumps(key, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]


# ---------------------------------------------------------------------------
# Mechanical lint flags (informational, never judgments)
# ---------------------------------------------------------------------------

def _state_ok(state: str) -> bool:
    s = state.strip().lower()
    if s in ("cleared", "set"):
        return True
    if s.startswith("equals:"):
        return bool(_EQUALS_NUMERIC.fullmatch(s[len("equals:"):].strip()))
    return False


def lint_constraint(ac: dict, source_filename: str) -> set:
    """Machine-derived flags for one raw constraint occurrence."""
    flags = set()
    op = str(ac.get("target_operation", "")).strip().lower()
    if op not in OP_VOCAB:
        flags.add("off_vocab_op")

    pre = [c for c in (ac.get("preconditions") or []) if isinstance(c, dict)]
    post = [c for c in (ac.get("postconditions") or []) if isinstance(c, dict)]
    if any(not _state_ok(str(c.get("required_state", ""))) for c in pre + post):
        flags.add("off_vocab_state")
    if not pre and not post:
        flags.add("empty_conditions")
    if len(post) > 3:
        flags.add("many_postconditions")

    names = [source_filename, str(ac.get("target_register", ""))]
    names += [str(f) for f in (ac.get("target_fields") or [])]
    for c in pre + post:
        names += [str(c.get("register_name", "")), str(c.get("field_name", ""))]
    if any("%s" in n for n in names):
        flags.add("placeholder_source")

    text = str(ac.get("datasheet_text", ""))
    if any(p.search(text) for p in W1C_PATTERNS):
        flags.add("w1c_suspect")
    if op == "read" and any(p.search(text) for p in READ_CLEAR_PATTERNS):
        flags.add("read_clear_suspect")
    return flags


# ---------------------------------------------------------------------------
# Corpus walk
# ---------------------------------------------------------------------------

def _run_sort_key(name: str):
    return (0, int(name)) if name.isdigit() else (1, name)


def iter_corpus(corpus_root: str):
    """Yield (rm, run, filename, constraint dict) for every raw constraint occurrence.

    Reads ONLY register files ({peripheral}_{register}, no extension) inside
    <rm>/<run>/. Subdirectories (info/, validator/, ...) and bookkeeping files
    are skipped — see the blindness rule in the module docstring.
    """
    for rm in sorted(os.listdir(corpus_root)):
        rmdir = os.path.join(corpus_root, rm)
        if not os.path.isdir(rmdir):
            continue
        runs = sorted((d for d in os.listdir(rmdir)
                       if os.path.isdir(os.path.join(rmdir, d))), key=_run_sort_key)
        for run in runs:
            rundir = os.path.join(rmdir, run)
            for fn in sorted(os.listdir(rundir)):
                fp = os.path.join(rundir, fn)
                if os.path.isdir(fp) or "_" not in fn:
                    continue
                if fn.startswith(SKIP_PREFIXES) or fn.endswith(SKIP_SUFFIXES):
                    continue
                try:
                    with open(fp, encoding="utf-8") as f:
                        data = json.load(f)
                except Exception as e:
                    print(f"  (skipping unreadable {rm}/{run}/{fn}: {e})", file=sys.stderr)
                    continue
                if not isinstance(data, dict):
                    continue
                for ac in data.get("access_constraints") or []:
                    if isinstance(ac, dict):
                        yield rm, run, fn, ac


# ---------------------------------------------------------------------------
# Row construction
# ---------------------------------------------------------------------------

def _compact(obj) -> str:
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False)


def _conds_json(conds) -> str:
    """First-seen condition list, original order, canonical 3 keys, compact JSON."""
    out = []
    for c in conds or []:
        if isinstance(c, dict):
            out.append({"register_name": str(c.get("register_name", "")),
                        "field_name": str(c.get("field_name", "")),
                        "required_state": str(c.get("required_state", ""))})
    return _compact(out)


def build_rows(corpus_root: str):
    """Scan the corpus; return (rows in first-seen order, scan-stats dict)."""
    rows = {}      # id -> row dict
    order = []     # ids in first-seen order
    flags_by_id = {}
    scan = {"raw": 0, "rms": set(), "runs": set()}

    for rm, run, fn, ac in iter_corpus(corpus_root):
        scan["raw"] += 1
        scan["rms"].add(rm)
        scan["runs"].add((rm, run))
        cid = constraint_id(dedup_key(rm, ac))
        flags = lint_constraint(ac, fn)
        if cid in rows:
            rows[cid]["dup_count"] += 1
            # union: a later duplicate may live in a %s-placeholder file etc.
            flags_by_id[cid] |= flags
            continue
        peripheral, _, register = fn.partition("_")
        rows[cid] = {
            "id": cid,
            "reference_manual": rm,
            "run": run,
            "source_file": f"{rm}/{run}/{fn}",
            "peripheral": peripheral,
            "register": register,
            "target_operation": str(ac.get("target_operation", "")),
            "target_fields": _compact([str(f) for f in (ac.get("target_fields") or [])]),
            "preconditions": _conds_json(ac.get("preconditions")),
            "postconditions": _conds_json(ac.get("postconditions")),
            "severity": str(ac.get("severity", "")),
            "consequence": str(ac.get("consequence", "")),
            "datasheet_text": str(ac.get("datasheet_text", "")),
            "dup_count": 1,
            "lint_flags": "",
            "status": "",
            "note": "",
        }
        flags_by_id[cid] = flags
        order.append(cid)

    for cid in order:
        rows[cid]["lint_flags"] = ";".join(sorted(flags_by_id[cid]))
    return [rows[cid] for cid in order], scan


def merge_with_existing(new_rows, existing_rows):
    """Preserve annotations by id; keep rows that vanished from the corpus.

    Non-empty status/note in the existing CSV always wins; machine columns of
    matched rows are refreshed from the new build.
    """
    stats = {"new": 0, "matched": 0, "annotations_preserved": 0, "orphans": 0}
    by_id = {r["id"]: r for r in existing_rows}
    for row in new_rows:
        old = by_id.pop(row["id"], None)
        if old is None:
            stats["new"] += 1
            continue
        stats["matched"] += 1
        if (old.get("status") or "").strip():
            row["status"] = old["status"]
        if (old.get("note") or "").strip():
            row["note"] = old["note"]
        if (old.get("status") or "").strip() or (old.get("note") or "").strip():
            stats["annotations_preserved"] += 1
    orphans = [r for r in existing_rows if r["id"] in by_id]
    stats["orphans"] = len(orphans)
    merged = new_rows + orphans
    merged.sort(key=lambda r: (r["reference_manual"], r["peripheral"],
                               r["register"], r["id"]))
    return merged, stats


# ---------------------------------------------------------------------------
# CSV load/save (atomic, resumable — same shape as annotate.py)
# ---------------------------------------------------------------------------

def read_rows(path: str):
    with open(path, newline="", encoding="utf-8") as f:
        return [{k: (r.get(k) or "") for k in COLUMNS} for r in csv.DictReader(f)]


def save_atomic(path: str, rows):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path) or ".", suffix=".tmp")
    with os.fdopen(fd, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in COLUMNS})
    os.replace(tmp, path)


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def print_summary(rows, scan, merge_stats, out_path):
    per_rm = Counter(r["reference_manual"] for r in rows)
    flag_hist = Counter()
    for r in rows:
        for fl in (r.get("lint_flags") or "").split(";"):
            if fl:
                flag_hist[fl] += 1
    annotated = sum(1 for r in rows if (r.get("status") or "").strip())

    print(f"\nwrote {out_path}: {len(rows)} rows "
          f"({merge_stats['new']} new, {merge_stats['matched']} refreshed, "
          f"{merge_stats['orphans']} orphaned kept, "
          f"{merge_stats['annotations_preserved']} annotations preserved)")
    print(f"scanned: {scan['raw']} raw constraints across "
          f"{len(scan['rms'])} reference manuals ({len(scan['runs'])} runs)")
    print("per-RM rows:")
    line = "  "
    for rm, n in sorted(per_rm.items()):
        chunk = f"{rm}={n}  "
        if len(line) + len(chunk) > 100:
            print(line.rstrip())
            line = "  "
        line += chunk
    if line.strip():
        print(line.rstrip())
    print("lint flags (rows carrying each; informational, not judgments):")
    for fl, n in flag_hist.most_common():
        print(f"  {fl:22} {n}")
    if not flag_hist:
        print("  (none)")
    print(f"annotated: {annotated}/{len(rows)}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _default_out():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "constraints", "stm.csv")


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Build/refresh the verified-constraints datasheet CSV from an "
                    "extraction corpus (re-runnable; existing annotations preserved).")
    ap.add_argument("corpus_root",
                    help="corpus root, e.g. .../hal_agent-phase-1d/agent_output/stm "
                         "(layout: <rm>/<run>/{peripheral}_{register})")
    ap.add_argument("--out", default=_default_out(),
                    help="output CSV (default: verified_datasheet/constraints/stm.csv)")
    args = ap.parse_args(argv)

    if not os.path.isdir(args.corpus_root):
        ap.error(f"corpus root not found: {args.corpus_root}")

    new_rows, scan = build_rows(args.corpus_root)
    existing = read_rows(args.out) if os.path.exists(args.out) else []
    merged, merge_stats = merge_with_existing(new_rows, existing)
    save_atomic(args.out, merged)
    print_summary(merged, scan, merge_stats, args.out)


if __name__ == "__main__":
    main()
