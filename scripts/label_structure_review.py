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
    b          go back to the previous candidate
    g N        jump to candidate number N
    q          save & quit
"""
import argparse
import csv
import os
import sys

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TTY = sys.stdout.isatty()


def _c(code, s):
    return f"\033[{code}m{s}\033[0m" if _TTY else s


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


def _show(row, idx, n, cands):
    tp, fp, left = _tally(cands)
    name = f"{row['peripheral']}.{row['register']}" + (f".{row['field']}" if (row.get('field') or '').strip() else "")
    print("\n" + "=" * 70)
    print(_c("1;36", f"[{idx + 1}/{n}]  {row['RM']}  {name}  {_c('0;36', row['key'])}")
          + _c("2", f"    (TP {tp} · FP {fp} · left {left})"))
    svds = row.get("svd_files", "")
    print(f"  SVD  {_c('2', '(' + str(row.get('svd_count','?')) + ': ' + svds + ')')}")
    print(f"       {_c('1;33', row.get('svd_value',''))}")
    print(f"  GEN  {_c('1;35', row.get('generator_value',''))}")
    v = (row.get("validator_verdict") or "").strip()
    conf = (row.get("validator_confidence") or "").strip()
    if v:
        col = "1;32" if v == "TP" else "1;31" if v == "FP" else "0"
        print(f"  validator: {_c(col, v)}" + (f"  (conf {conf})" if conf else "") + _c("2", "  [Enter to accept]"))
    else:
        print(f"  validator: {_c('2', '(none)')}")
    cur = (row.get("tp_fp") or "").strip()
    cv = (row.get("correct_value") or "").strip()
    if cur or cv:
        print(_c("2", f"  current: tp_fp={cur or '-'}  correct_value={cv or '-'}"))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("csv", nargs="?", help="path to a *_structure_review.csv")
    ap.add_argument("--rm", help="device, to build evaluation/{mfr}/{rm}/{run}/{rm}_structure_review.csv")
    ap.add_argument("--run", default="1")
    ap.add_argument("--manufacturer", default="stm")
    ap.add_argument("--all", action="store_true",
                    help="step through ALL candidates (default: only unlabeled)")
    args = ap.parse_args()

    path = _resolve_path(args)
    if not os.path.isfile(path):
        sys.exit(f"not found: {path}")
    rows, fields = _load(path)
    cands = [r for r in rows if _blank(r.get("status"))]
    if not cands:
        sys.exit("no candidates (all rows have a status / are auto-FP)")

    work = cands if args.all else [r for r in cands if _blank(r.get("tp_fp"))]
    tp0, fp0, _ = _tally(cands)
    print(_c("1", f"{path}"))
    print(f"{len(cands)} candidates · {tp0 + fp0} already labeled · "
          f"{len(work)} to review{' (all)' if args.all else ''}")
    if not work:
        print("nothing to review — all candidates labeled. Use --all to revisit.")
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
            print(_c("2", "    keys: t/f label · Enter accept · s skip · c correct_value · b back · g N jump · q quit"))

    tp, fp, left = _tally(cands)
    print("\n" + "=" * 70)
    print(_c("1", f"saved {path}"))
    print(f"  labeled: {_c('1;32', f'TP {tp}')} · {_c('1;31', f'FP {fp}')} · {left} candidate(s) still blank")


if __name__ == "__main__":
    main()
