#!/usr/bin/env python3
"""
annotate_constraints.py — CLI for annotating the verified-CONSTRAINTS datasheet
(sibling of annotate.py; same conventions: atomic resumable CSV saves after every
answer, --stats, keyboard-driven loop).

The judgment is the CLOSED LOCAL task from the plan (§7.1/§7.2): for each row you
see the generator's encoding (target register/operation/fields, pre/postconditions,
severity, consequence) next to its verbatim datasheet quote, and you judge two
things — no PDF needed:

  1. Is the quote a genuine ACCESS/ORDERING REQUIREMENT?  (Not w1c flag semantics,
     access-width notes, privilege/secure notes, or validity/don't-care notes.)
  2. Does the encoding FAITHFULLY represent it?  (Right target, operation,
     polarity, fields, conditions — nothing dropped or inverted.)

Statuses:  c = confirmed (yes to both)            e = encoding_error (real
constraint, wrong/incomplete encoding)            n = not_constraint (quote is
not a requirement)                                m = quote_missing (quote not
found in the manual)                              u = unsure
s skips (row stays pending), q saves and quits.  e/n/m/u prompt for an optional
note.  Progress is saved atomically after EVERY answer — a crash loses nothing.

Rows are served in STRICT ROUND-ROBIN across reference manuals, so partial effort
covers all 30 RMs evenly (the plan's stratification for the retrospective α
measurement). ~20 s/row.

BLINDNESS: the CSV never contains an LLM-validator verdict, so there is nothing
machine-judged to anchor on; lint_flags are mechanical text/vocabulary flags only.

Usage:
  python3 verified_datasheet/annotate_constraints.py                  # annotate
  python3 verified_datasheet/annotate_constraints.py --stats          # progress
  python3 verified_datasheet/annotate_constraints.py --rm rm0008      # one RM
  python3 verified_datasheet/annotate_constraints.py --flagged-only   # lint-flagged rows
  python3 verified_datasheet/annotate_constraints.py --limit 25       # short session
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import textwrap
from collections import Counter, deque

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_constraints_datasheet import (  # single source for schema + IO
    COLUMNS, STATUSES, read_rows, save_atomic,
)

KEY_TO_STATUS = {
    "c": "confirmed",
    "e": "encoding_error",
    "n": "not_constraint",
    "m": "quote_missing",
    "u": "unsure",
}
NOTE_KEYS = ("e", "n", "m", "u")  # statuses that prompt for an optional note
SECONDS_PER_ROW = 20  # planning figure from the plan (§7.2)


# ---------------------------------------------------------------------------
# Colors (plain when not a TTY / NO_COLOR set, so --stats pipes cleanly)
# ---------------------------------------------------------------------------

def _color_enabled() -> bool:
    return sys.stdout.isatty() and not os.environ.get("NO_COLOR")


USE_COLOR = _color_enabled()
BOLD, DIM, RED, GREEN, YELLOW, MAGENTA, CYAN = "1", "2", "31", "32", "33", "35", "36"


def paint(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if USE_COLOR else text


# ---------------------------------------------------------------------------
# Row selection (pure — unit-tested without a TTY)
# ---------------------------------------------------------------------------

def select_pending(rows, rm=None, flagged_only=False, limit=None):
    """Pending (empty-status) rows in strict round-robin across reference manuals.

    RMs cycle in sorted order, one row per RM per cycle (rows keep their CSV
    order within an RM), so annotating any prefix spreads evenly over all RMs.
    """
    pending = [r for r in rows if not (r.get("status") or "").strip()]
    if rm:
        pending = [r for r in pending if r.get("reference_manual") == rm]
    if flagged_only:
        pending = [r for r in pending if (r.get("lint_flags") or "").strip()]

    buckets = {}
    for r in pending:
        buckets.setdefault(r.get("reference_manual", ""), deque()).append(r)
    order = sorted(buckets)
    out = []
    while any(buckets[name] for name in order):
        for name in order:
            if buckets[name]:
                out.append(buckets[name].popleft())
    return out[:limit] if limit else out


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def _parse_json(s, default):
    try:
        v = json.loads(s) if (s or "").strip() else default
        return v if isinstance(v, list) else default
    except ValueError:
        return default


def format_condition(c) -> str:
    if not isinstance(c, dict):
        return str(c)
    reg = c.get("register_name", "?") or "?"
    field = c.get("field_name", "")
    target = f"{reg}.{field}" if field else f"{reg} (whole register)"
    return f"{target}  ->  {c.get('required_state', '?') or '?'}"


def _wrap(text: str, indent: str = "  ", width: int = 96):
    return textwrap.wrap(text, width=width, initial_indent=indent,
                         subsequent_indent=indent) or [indent.rstrip()]


def show_row(row, pos: int, total: int):
    head = (f"[{pos}/{total}]  {row['reference_manual']} · "
            f"{row['peripheral']}.{row['register']}")
    prov = f"(id {row['id']} · ×{row['dup_count']} · {row['source_file']})"
    print()
    print(paint(head, BOLD + ";" + CYAN) + "  " + paint(prov, DIM))

    fields = _parse_json(row.get("target_fields", ""), [])
    fields_str = ", ".join(map(str, fields)) if fields else "(whole register)"
    print(f"  operation: {paint(row['target_operation'] or '?', BOLD)}"
          f"    fields: {fields_str}"
          f"    severity: {paint(row['severity'] or '?', RED if row['severity'] == 'error' else YELLOW)}")

    for label, col in (("preconditions", "preconditions"),
                       ("postconditions", "postconditions")):
        conds = _parse_json(row.get(col, ""), [])
        if conds:
            print(f"  {label}:")
            for c in conds:
                print(paint(f"    - {format_condition(c)}", GREEN))
        else:
            print(f"  {label}: " + paint("(none)", DIM))

    if (row.get("consequence") or "").strip():
        print("  consequence:")
        for line in _wrap(row["consequence"], indent="    "):
            print(paint(line, DIM))

    print(paint("  quote " + "─" * 70, DIM))
    quote = (row.get("datasheet_text") or "").strip() or "(empty datasheet_text)"
    for raw_line in quote.splitlines() or [quote]:
        for line in _wrap(raw_line, indent=""):
            print("  " + paint("│ ", DIM) + paint(line, YELLOW))
    print(paint("  " + "─" * 76, DIM))

    if (row.get("lint_flags") or "").strip():
        print("  flags: " + paint(row["lint_flags"], MAGENTA))


HELP = """
  Judge the quote and its encoding (no PDF needed — the quote is the evidence):
    c  confirmed       genuine access/ordering requirement AND encoding faithful
    e  encoding_error  real requirement, but target/operation/polarity/fields/
                       conditions are wrong or incomplete (note prompted)
    n  not_constraint  quoted text is not an access/ordering requirement — e.g.
                       w1c flag semantics, access width, privilege, validity
                       notes (note prompted)
    m  quote_missing   the quote does not exist in the reference manual
                       (note prompted)
    u  unsure          can't decide (note prompted)
    s  skip            leave the row pending for later
    q  quit            save and exit
"""


# ---------------------------------------------------------------------------
# Interactive loop
# ---------------------------------------------------------------------------

def annotate(rows, selected, csv_path):
    total_pending = sum(1 for r in rows if not (r.get("status") or "").strip())
    rms = {r["reference_manual"] for r in selected}
    print(f"\n{len(rows)} rows in {csv_path}")
    print(f"pending: {total_pending} · this session: {len(selected)} rows, "
          f"round-robin over {len(rms)} reference manuals")
    print("keys: c confirmed · e encoding_error · n not_constraint · "
          "m quote_missing · u unsure · s skip · q quit · ? help")

    done = 0
    prompt = "  [c/e/n/m/u/s/q/?] > "
    for pos, row in enumerate(selected, 1):
        show_row(row, pos, len(selected))
        while True:
            try:
                ans = input(prompt).strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\nSaving and quitting.")
                save_atomic(csv_path, rows)
                _session_summary(done, rows, csv_path)
                return
            if ans == "q":
                save_atomic(csv_path, rows)
                _session_summary(done, rows, csv_path)
                return
            if ans == "?":
                print(HELP)
                continue
            if ans == "s":
                break  # status stays empty -> remains pending
            if ans in KEY_TO_STATUS:
                row["status"] = KEY_TO_STATUS[ans]
                if ans in NOTE_KEYS:
                    try:
                        note = input("    note (optional) > ").strip()
                    except (EOFError, KeyboardInterrupt):
                        note = ""
                    if note:
                        row["note"] = note
                save_atomic(csv_path, rows)  # atomic save after EVERY answer
                done += 1
                break
            print(paint("  unrecognized — ? for help", RED))

    save_atomic(csv_path, rows)
    _session_summary(done, rows, csv_path)


def _session_summary(done, rows, csv_path):
    annotated = sum(1 for r in rows if (r.get("status") or "").strip())
    print(f"\nSaved {csv_path}. This session: {done} rows. "
          f"Total annotated: {annotated}/{len(rows)}.")


# ---------------------------------------------------------------------------
# Stats (non-interactive; works without a TTY)
# ---------------------------------------------------------------------------

def _fmt_duration(seconds: float) -> str:
    if seconds < 90 * 60:
        return f"{seconds / 60:.0f} min"
    return f"{seconds / 3600:.1f} h"


def stats(rows):
    by_rm = {}
    for r in rows:
        by_rm.setdefault(r.get("reference_manual", "?"), []).append(r)

    print(f"{'RM':10} {'annotated':>12}   breakdown")
    for rm in sorted(by_rm):
        group = by_rm[rm]
        counts = Counter((r.get("status") or "").strip() for r in group)
        annotated = len(group) - counts.get("", 0)
        breakdown = "  ".join(f"{s}={counts[s]}" for s in STATUSES if counts.get(s))
        print(f"{rm:10} {annotated:>6}/{len(group):<5}   {breakdown or '-'}")

    counts = Counter((r.get("status") or "").strip() for r in rows)
    pending = counts.get("", 0)
    annotated = len(rows) - pending
    flagged = sum(1 for r in rows if (r.get("lint_flags") or "").strip())
    print(f"\noverall: {annotated}/{len(rows)} annotated "
          f"({100.0 * annotated / len(rows):.1f}%)" if rows else "\noverall: empty CSV")
    if rows:
        breakdown = "  ".join(f"{s}={counts[s]}" for s in STATUSES if counts.get(s))
        print(f"by status: {breakdown or '-'}")
        print(f"lint-flagged rows: {flagged}")
        print(f"remaining: {pending} rows ≈ {_fmt_duration(pending * SECONDS_PER_ROW)} "
              f"at ~{SECONDS_PER_ROW} s/row")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _default_csv():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "constraints", "stm.csv")


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Annotate the verified-constraints datasheet (quote vs encoding; "
                    "round-robin across reference manuals; resumable).")
    ap.add_argument("--csv", default=_default_csv(),
                    help="constraints CSV (default: verified_datasheet/constraints/stm.csv)")
    ap.add_argument("--stats", action="store_true",
                    help="print per-RM progress and exit (no annotation)")
    ap.add_argument("--rm", default="",
                    help="only rows from this reference manual (e.g. rm0008)")
    ap.add_argument("--limit", type=int, default=0,
                    help="annotate at most N rows this session")
    ap.add_argument("--flagged-only", action="store_true",
                    help="only rows carrying at least one lint flag")
    args = ap.parse_args(argv)

    if not os.path.exists(args.csv):
        ap.error(f"{args.csv} not found — build it first:\n"
                 "  python3 verified_datasheet/build_constraints_datasheet.py <corpus_root>")
    rows = read_rows(args.csv)

    if args.stats:
        stats(rows)
        return

    selected = select_pending(rows, rm=args.rm or None,
                              flagged_only=args.flagged_only,
                              limit=args.limit or None)
    if not selected:
        print("Nothing pending for these filters — all done (or wrong --rm?).")
        stats(rows)
        return
    annotate(rows, selected, args.csv)


if __name__ == "__main__":
    main()
