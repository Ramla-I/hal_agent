#!/usr/bin/env python3
"""Step through the constraints in a {rm}_constraints_review.jsonl and label each
one TP (a real, correctly-extracted register-access constraint) or FP, writing
back into the `tp_fp` field. Saves after every keystroke, so quitting or a crash
never loses work; resumes at the first unlabeled constraint.

Each constraint shows its kind, the target operation/register, the datasheet quote
it was extracted from, its preconditions / steps / timing, and the validator's
advisory verdict + enforcement, so you can accept it with Enter or override.

    python scripts/label_constraints_review.py --rm rm0008
    python scripts/label_constraints_review.py evaluation/stm/rm0008/1/rm0008_constraints_review.jsonl
    python scripts/label_constraints_review.py --rm rm0008 --confirmed   # only validator-confirmed
    python scripts/label_constraints_review.py --rm rm0008 --all         # revisit labeled ones too

Controls per constraint:
    t / f      label TP / FP
    Enter      accept the validator's verdict (confirmed -> TP, not_constraint -> FP); else skip
    s          skip (leave blank)
    b          go back to the previous constraint
    g N        jump to constraint number N
    q          save & quit
"""
import argparse
import json
import os
import sys
import textwrap

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_COLOR = sys.stdout.isatty()

# per-field palette (mirrors label_structure_review.py)
C_HEAD = "1"        # bold — [n/N] + RM
C_NAME = "1;36"     # bright cyan — peripheral.register
C_KIND = "0;36"     # cyan — constraint kind
C_TGT = "1;35"      # bright magenta — target operation/register (what is gated)
C_CONS = "0;37"     # white — the plain-English consequence
C_QUOTE = "1;33"    # bright yellow — the datasheet quote (the evidence / ground truth)
C_TP = "1;32"       # green — TP / confirmed
C_FP = "1;31"       # red — FP / not_constraint
C_DIM = "2"         # dim — meta (preconditions, enforcement, tally, current label)
C_PROMPT = "1;37"   # bold white — prompt


def _c(code, s):
    return f"\033[{code}m{s}\033[0m" if _COLOR else s


def _resolve_path(args) -> str:
    if args.jsonl:
        return args.jsonl
    if args.rm:
        return os.path.join(_REPO, "evaluation", args.manufacturer, args.rm, str(args.run),
                            f"{args.rm}_constraints_review.jsonl")
    sys.exit("give a JSONL path, or --rm (and optionally --run)")


def _load(path):
    recs = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            recs.append(json.loads(line))
    for r in recs:
        r.setdefault("tp_fp", "")
    return recs


def _save(path, recs):
    # Atomic tmp+rename; fall back to in-place rewrite when the dir isn't writable
    # (pipeline outputs are Docker-owned — the file may be chmod'd writable, the dir not).
    def _write(fp):
        for r in recs:
            fp.write(json.dumps(r, ensure_ascii=False) + "\n")
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            _write(f)
        os.replace(tmp, path)
    except OSError:
        try:
            os.remove(tmp)
        except OSError:
            pass
        with open(path, "w", encoding="utf-8") as f:
            _write(f)


def _blank(v):
    return not (str(v) or "").strip()


def _tally(recs):
    tp = sum(1 for r in recs if str(r.get("tp_fp") or "").strip().upper() == "TP")
    fp = sum(1 for r in recs if str(r.get("tp_fp") or "").strip().upper() == "FP")
    left = sum(1 for r in recs if _blank(r.get("tp_fp")))
    return tp, fp, left


def _cond(p) -> str:
    """Render one pre/post-condition: e.g. ADC_CR.ADEN=set or FLASH_SR (whole reg)."""
    if not isinstance(p, dict):
        return str(p)
    reg = p.get("register", "?")
    fld = p.get("field")
    state = p.get("state") or p.get("value") or ""
    loc = reg + (f".{fld}" if fld and not p.get("whole_register") else "")
    return f"{loc}={state}" if state != "" else loc


def _detail_lines(c) -> list:
    """Kind-specific body lines (preconditions, steps, timing, read effects)."""
    out = []
    pre = c.get("preconditions") or []
    if pre:
        out.append("when: " + ", ".join(_cond(p) for p in pre))
    post = c.get("postconditions") or []
    if post:
        out.append("then: " + ", ".join(_cond(p) for p in post))
    steps = c.get("steps") or []
    if steps:
        out.append("steps: " + " -> ".join(
            str((s.get("description") or s.get("register") or s) if isinstance(s, dict) else s)
            for s in steps))
    for k in ("after", "before", "duration"):
        if c.get(k):
            out.append(f"{k}: {c[k]}")
    if c.get("read_register"):
        out.append(f"read: {c['read_register']}")
    if c.get("effects"):
        out.append(f"effects: {c['effects']}")
    return out


def _show(rec, idx, n, pool):
    # tally over the pool being stepped through (the work list), so TP+FP+left == n
    # and `left` stays accurate under filters like --confirmed.
    tp, fp, left = _tally(pool)
    c = rec.get("constraint") or {}
    kind = c.get("kind", "?")
    name = f"{rec.get('peripheral', '?')}.{rec.get('register', '?')}"
    print("\n" + _c(C_DIM, "=" * 70))
    print(_c(C_HEAD, f"[{idx + 1}/{n}]  {rec.get('rm', '')}") + "  "
          + _c(C_NAME, name) + "  " + _c(C_KIND, kind)
          + _c(C_DIM, f"    (TP {tp} · FP {fp} · left {left})"))
    # what is gated
    op = c.get("target_operation")
    tgt = c.get("target_register")
    tf = c.get("target_fields") or []
    if tgt or op:
        line = f"  {(op or '?')} {tgt or ''}"
        if tf:
            line += "." + ",".join(tf)
        print(_c(C_TGT, line.rstrip()))
    cons = str(c.get("consequence") or "").strip()
    if cons:
        print("  " + _c(C_CONS, cons))
    for ln in _detail_lines(c):
        print(_c(C_DIM, "    " + ln))
    quote = str(c.get("datasheet_text") or "").strip()
    if quote:
        wrapped = textwrap.fill(quote, width=76, initial_indent="  quote: ", subsequent_indent="         ")
        print(_c(C_QUOTE, wrapped))
    # validator advisory
    v = str(rec.get("verdict") or "").strip()
    conf = str(rec.get("confidence") or "").strip()
    enf = str(rec.get("enforcement") or "").strip()
    tier = str(rec.get("anchor_tier") or "").strip()
    vcol = C_TP if v == "confirmed" else C_FP if v in ("not_constraint", "encoding_error") else C_DIM
    acceptable = v in ("confirmed", "not_constraint")
    print("  validator: " + _c(vcol, v or "(none)")
          + (f"  conf {conf}" if conf else "")
          + _c(C_DIM, f"   · enforce={enf or '-'} · anchor={tier or '-'}")
          + (_c(C_DIM, "   [Enter to accept]") if acceptable else ""))
    cur = str(rec.get("tp_fp") or "").strip()
    if cur:
        print(_c(C_DIM, f"  current: tp_fp={cur}"))
    # Full constraint object (indented JSON) — nothing hidden; the summary above is
    # just the highlights. Includes severity/enforceability + all kind-specific fields.
    print(_c(C_DIM, "  constraint (full):"))
    for ln in json.dumps(c, indent=2, ensure_ascii=False).splitlines():
        print(_c(C_DIM, "    " + ln))


def _accept_verdict(rec) -> str:
    """Map the validator verdict to a TP/FP the reviewer can accept with Enter."""
    v = str(rec.get("verdict") or "").strip()
    return "TP" if v == "confirmed" else "FP" if v == "not_constraint" else ""


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("jsonl", nargs="?", help="path to a *_constraints_review.jsonl")
    ap.add_argument("--rm", help="device, to build evaluation/{mfr}/{rm}/{run}/{rm}_constraints_review.jsonl")
    ap.add_argument("--run", default="1")
    ap.add_argument("--manufacturer", default="stm")
    ap.add_argument("--all", action="store_true",
                    help="step through ALL constraints (default: only unlabeled)")
    ap.add_argument("--confirmed", action="store_true",
                    help="only constraints the validator confirmed (verdict==confirmed)")
    args = ap.parse_args()

    path = _resolve_path(args)
    if not os.path.isfile(path):
        sys.exit(f"not found: {path}")
    recs = _load(path)
    if not recs:
        sys.exit("no constraints in file")

    work = recs if args.all else [r for r in recs if _blank(r.get("tp_fp"))]
    if args.confirmed:
        work = [r for r in work if str(r.get("verdict") or "").strip() == "confirmed"]
    tp0, fp0, _ = _tally(recs)
    flags = "".join(f for f, on in ((" (all)", args.all), (" [confirmed only]", args.confirmed)) if on)
    print(_c("1", f"{path}"))
    print(f"{len(recs)} constraints · {tp0 + fp0} already labeled · {len(work)} to review{flags}")
    if not work:
        print("no constraints to review." if args.confirmed
              else "nothing to review — all constraints labeled. Use --all to revisit.")
        return

    i = 0
    while 0 <= i < len(work):
        rec = work[i]
        _show(rec, i, len(work), work)
        try:
            cmd = input(_c(C_PROMPT, "  label> ")).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        low = cmd.lower()
        if low == "q":
            break
        elif low == "t":
            rec["tp_fp"] = "TP"; _save(path, recs); i += 1
        elif low == "f":
            rec["tp_fp"] = "FP"; _save(path, recs); i += 1
        elif low == "s":
            i += 1
        elif low == "b":
            i = max(0, i - 1)
        elif low.startswith("g"):
            try:
                i = max(0, min(len(work) - 1, int(cmd[1:].strip()) - 1))
            except ValueError:
                print(_c(C_FP, "  usage: g N"))
        elif cmd == "":
            v = _accept_verdict(rec)
            if v:
                rec["tp_fp"] = v; _save(path, recs); i += 1
            else:
                i += 1  # no verdict to accept -> skip
        else:
            print(_c(C_DIM, "  keys: t/f label · Enter accept · s skip · b back · g N jump · q quit"))

    tp, fp, left = _tally(recs)
    blanks = [r for r in recs if _blank(r.get("tp_fp"))]
    conf = sum(1 for r in blanks if str(r.get("verdict") or "").strip() == "confirmed")
    notc = sum(1 for r in blanks if str(r.get("verdict") or "").strip() == "not_constraint")
    other = len(blanks) - conf - notc
    print("\n" + _c("1", f"saved {path}"))
    print(f"  labeled: {_c(C_TP, f'TP {tp}')} · {_c(C_FP, f'FP {fp}')} · {left} constraint(s) still blank")
    if blanks:
        print(f"  those {left} blank break down by validator verdict: "
              f"{_c(C_TP, f'{conf} confirmed')} · {_c(C_FP, f'{notc} not_constraint')} · "
              f"{_c(C_DIM, f'{other} unjudged (encoding_error/none)')}")


if __name__ == "__main__":
    main()
