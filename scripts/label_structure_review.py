#!/usr/bin/env python3
"""Step through the candidate rows of a {rm}_structure_review.csv and label each
one TP (real SVD/generator bug) or FP, writing back into the `tp_fp` column
(optionally `correct_value`). Saves after every keystroke, so quitting or a crash
never loses work; resumes at the first unlabeled candidate.

Candidates are the rows with a blank `status` (the auto-FP rows are skipped).
Each shows the SVD-vs-generator disagreement plus the validator's advisory
verdict, so you can accept it with Enter or override.

    python scripts/label_structure_review.py evaluation/stm/rm0091/1/rm0091_structure_review.csv
    python scripts/label_structure_review.py --rm rm0091 --run 1
    python scripts/label_structure_review.py --rm rm0091 --all      # revisit labeled ones too

Controls per candidate:
    t / f      label TP / FP
    Enter      accept the validator's verdict (TP/FP); if none, skip
    s          skip (leave blank)
    c          set/edit correct_value (then still label t/f)
    e          edit the svd_files list — remove files that don't have the bug
    b          go back to the previous candidate
    g N        jump to candidate number N
    q          save & quit
"""
import argparse
import csv
import os
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_COLOR = sys.stdout.isatty()

# per-field palette
C_HEAD = "1"        # bold — [n/N] + RM
C_NAME = "1;36"     # bright cyan — peripheral.register.field
C_KEY = "0;36"      # cyan — the key (reset_value, bit_width, ...)
C_SVD = "1;33"      # bright yellow — SVD (ground truth) value
C_GEN = "1;35"      # bright magenta — generator value
C_TP = "1;32"       # green — TP
C_FP = "1;31"       # red — FP
C_DIM = "2"         # dim — meta (svd files, tally, current label)
C_PROMPT = "1;37"   # bold white — prompt


def _c(code, s):
    return f"\033[{code}m{s}\033[0m" if _COLOR else s


def _resolve_path(args) -> str:
    if args.csv:
        return args.csv
    if args.rm:
        return os.path.join(_REPO, "evaluation", args.manufacturer, args.rm, str(args.run),
                            f"{args.rm}_structure_review.csv")
    sys.exit("give a CSV path, or --rm (and optionally --run)")


def _load(path):
    with open(path, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        rows = list(r)
        fields = list(r.fieldnames or [])
    for col in ("tp_fp", "correct_value"):
        if col not in fields:
            fields.append(col)
            for row in rows:
                row.setdefault(col, "")
    return rows, fields


def _write(f, rows, fields):
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    for row in rows:
        w.writerow({k: row.get(k, "") for k in fields})


def _save(path, rows, fields):
    # Prefer atomic tmp+rename; fall back to an in-place rewrite when the dir
    # isn't writable (pipeline outputs are Docker-owned — the file may be chmod'd
    # writable but its directory is not).
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", newline="", encoding="utf-8") as f:
            _write(f, rows, fields)
        os.replace(tmp, path)
    except OSError:
        try:
            os.remove(tmp)
        except OSError:
            pass
        with open(path, "w", newline="", encoding="utf-8") as f:
            _write(f, rows, fields)


def _blank(v):
    return not (v or "").strip()


def _tally(cands):
    tp = sum(1 for r in cands if (r.get("tp_fp") or "").strip().upper() == "TP")
    fp = sum(1 for r in cands if (r.get("tp_fp") or "").strip().upper() == "FP")
    left = sum(1 for r in cands if _blank(r.get("tp_fp")))
    return tp, fp, left


def _vsplit(rows):
    """Split rows by the validator's advisory verdict (TP / FP / unjudged)."""
    tp = sum(1 for r in rows if (r.get("validator_verdict") or "").strip().upper() == "TP")
    fp = sum(1 for r in rows if (r.get("validator_verdict") or "").strip().upper() == "FP")
    return tp, fp, len(rows) - tp - fp


def _show(row, idx, n, cands):
    tp, fp, left = _tally(cands)
    name = f"{row['peripheral']}.{row['register']}" + (f".{row['field']}" if (row.get('field') or '').strip() else "")
    print("\n" + _c(C_DIM, "=" * 70))
    # header (each piece colored separately — nesting ANSI would reset the line early)
    print(_c(C_HEAD, f"[{idx + 1}/{n}]  {row['RM']}") + "  "
          + _c(C_NAME, name) + "  " + _c(C_KEY, row["key"])
          + _c(C_DIM, f"    (TP {tp} · FP {fp} · left {left})"))
    svds = row.get("svd_files", "")
    print(_c(C_SVD, "  SVD  " + (row.get("svd_value", "") or "(none)")))
    print(_c(C_DIM, f"       {row.get('svd_count', '?')} file(s): {svds}"))
    print(_c(C_GEN, "  GEN  " + (row.get("generator_value", "") or "(none)")))
    v = (row.get("validator_verdict") or "").strip()
    conf = (row.get("validator_confidence") or "").strip()
    if v:
        col = C_TP if v == "TP" else C_FP if v == "FP" else C_DIM
        print("  validator: " + _c(col, v) + (f"  (conf {conf})" if conf else "")
              + _c(C_DIM, "   [Enter to accept]"))
    else:
        print("  validator: " + _c(C_DIM, "(none)"))
    cur = (row.get("tp_fp") or "").strip()
    cv = (row.get("correct_value") or "").strip()
    if cur or cv:
        print(_c(C_DIM, f"  current: tp_fp={cur or '-'}  correct_value={cv or '-'}"))


def _edit_svd_files(row) -> bool:
    """Trim the `svd_files` column — remove the SVD files that don't have this bug
    (also updates `svd_count`). Returns True if changed."""
    names = [n.strip() for n in (row.get("svd_files") or "").split(";") if n.strip()]
    if not names:
        print(_c(C_DIM, "    (no svd_files listed)"))
        return False
    for i, nm in enumerate(names, 1):
        print(f"    {_c(C_SVD, str(i) + '.')} {nm}")
    try:
        raw = input(_c(C_PROMPT, "    remove which? (numbers, e.g. '2 3'; Enter cancels)> ")).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return False
    if not raw:
        return False
    try:
        drop = {int(x) for x in raw.replace(",", " ").split()}
    except ValueError:
        print(_c(C_FP, "    numbers only"))
        return False
    kept = [nm for i, nm in enumerate(names, 1) if i not in drop]
    if not kept:
        print(_c(C_FP, "    that removes all files — cancelled (the bug must be in at least one)"))
        return False
    if len(kept) == len(names):
        return False
    row["svd_files"] = ";".join(kept)
    row["svd_count"] = str(len(kept))
    print(_c(C_SVD, f"    svd_files -> {row['svd_files']}  ({len(kept)} file(s))"))
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("csv", nargs="?", help="path to a *_structure_review.csv")
    ap.add_argument("--rm", help="device, to build evaluation/{mfr}/{rm}/{run}/{rm}_structure_review.csv")
    ap.add_argument("--run", default="1")
    ap.add_argument("--manufacturer", default="stm")
    ap.add_argument("--all", action="store_true",
                    help="step through ALL candidates (default: only unlabeled)")
    ap.add_argument("--validator-tp", action="store_true",
                    help="only rows the datasheet validator flagged TP (validator_verdict==TP)")
    args = ap.parse_args()

    path = _resolve_path(args)
    if not os.path.isfile(path):
        sys.exit(f"not found: {path}")
    rows, fields = _load(path)
    cands = [r for r in rows if _blank(r.get("status"))]
    if not cands:
        sys.exit("no candidates (all rows have a status / are auto-FP)")

    work = cands if args.all else [r for r in cands if _blank(r.get("tp_fp"))]
    if args.validator_tp:
        work = [r for r in work if (r.get("validator_verdict") or "").strip().upper() == "TP"]
    tp0, fp0, _ = _tally(cands)
    flags = "".join(f for f, on in ((" (all)", args.all), (" [validator-TP only]", args.validator_tp)) if on)
    print(_c("1", f"{path}"))
    print(f"{len(cands)} candidates · {tp0 + fp0} already labeled · "
          f"{len(work)} to review{flags}")
    if not work:
        msg = "no validator-TP candidates to review." if args.validator_tp \
            else "nothing to review — all candidates labeled. Use --all to revisit."
        print(msg)
        return

    i = 0
    while 0 <= i < len(work):
        row = work[i]
        _show(row, i, len(work), cands)
        try:
            cmd = input(_c("1", "  label> ")).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        low = cmd.lower()
        if low == "q":
            break
        elif low == "t":
            row["tp_fp"] = "TP"; _save(path, rows, fields); i += 1
        elif low == "f":
            row["tp_fp"] = "FP"; _save(path, rows, fields); i += 1
        elif low == "s":
            i += 1
        elif low == "b":
            i = max(0, i - 1)
        elif low == "c":
            try:
                val = input("    correct_value> ").strip()
            except (EOFError, KeyboardInterrupt):
                print(); continue
            row["correct_value"] = val; _save(path, rows, fields)  # stay on this row to still label t/f
        elif low == "e":
            if _edit_svd_files(row):   # trim svd_files list; stay on this row, re-shows after
                _save(path, rows, fields)
        elif low.startswith("g"):
            try:
                j = int(cmd.split()[1]) - 1
                if 0 <= j < len(work):
                    i = j
                else:
                    print(_c("1;31", f"    out of range 1..{len(work)}"))
            except (ValueError, IndexError):
                print(_c("1;31", "    usage: g N"))
        elif cmd == "":
            v = (row.get("tp_fp_suggest") or row.get("validator_verdict") or "").strip()
            if v in ("TP", "FP"):
                row["tp_fp"] = v; _save(path, rows, fields); i += 1
            else:
                print(_c("2", "    no validator verdict to accept — 's' to skip"));
        else:
            print(_c(C_DIM, "    keys: t/f label · Enter accept · s skip · c correct_value · "
                            "e edit-svd-files · b back · g N jump · q quit"))

    tp, fp, left = _tally(cands)
    blanks = [r for r in cands if _blank(r.get("tp_fp"))]
    vt, vf, vo = _vsplit(blanks)
    print("\n" + "=" * 70)
    print(_c("1", f"saved {path}"))
    print(f"  labeled: {_c('1;32', f'TP {tp}')} · {_c('1;31', f'FP {fp}')} · {left} candidate(s) still blank")
    if blanks:
        print(f"  those {left} blank break down by validator verdict: "
              f"{_c(C_TP, f'{vt} TP')} · {_c(C_FP, f'{vf} FP')} · "
              f"{_c(C_DIM, f'{vo} unjudged (abstain/none)')}")


if __name__ == "__main__":
    main()
