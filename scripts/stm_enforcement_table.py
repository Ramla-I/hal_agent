#!/usr/bin/env python3
"""stm_enforcement_table.py -- the enforcement-arm results table, in LaTeX.

The companion to the SVD register-structure table. That one counts BUGS, and
every row is a defect. This one counts COMPILE ERRORS, and a compile error is
not a defect by itself: the gate demands a witness, so a driver that satisfies
the datasheet some other way still fails to build. The category columns exist
to keep that distinction visible --

    gate fired        a compile error naming a constrained register
      already guarded the driver DOES establish the precondition (in the
                      enclosing function, a helper one level up, or an RAII
                      scope guard) -- correct code, caught by a blunt gate
      possible bug    it does not; this is the column worth reading
      untriaged       the static pass could not resolve the precondition
                      fields, so it is evidence of neither
    generic friction  the error landed on an associated type in generic code
                      (`<Self as UartRB>::SRrs`), not on a concrete register

Nothing is hardcoded: every number is read from the sweep artifacts in
applications/pac_codegen/experiments/out/.

Usage:
    python scripts/stm_enforcement_table.py                  # default gating
    python scripts/stm_enforcement_table.py --mode field     # field-level
    python scripts/stm_enforcement_table.py --mode both      # both, stacked
    python scripts/stm_enforcement_table.py --csv out.csv
"""

import argparse
import collections
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "applications" / "pac_codegen" / "experiments" / "out"

# Several files per mode, merged in order with later winning, so a target
# re-measured on its own does not require re-running the whole sweep.
MODES = {
    "default": (["sweep_wholereg_build.json", "sweep_rm0041_wholereg.json"],
                "whole-register gating"),
    "field": (["sweep_fieldgate_49.json", "sweep_rm0041_field.json"],
              "field-level gating"),
}


def _n(v):
    return v if isinstance(v, int) else 0


def load(mode):
    names, label = MODES[mode]
    merged = {}
    for name in names:
        p = OUT / name
        if not p.is_file():
            continue
        for r in json.loads(p.read_text()):
            merged[(r["rm"], r.get("device", ""))] = r
    if not merged:
        sys.exit(f"no sweep artifact for {mode!r} in {OUT}\n"
                 f"run stm_sweep.py"
                 f"{' --field-level-gating' if mode == 'field' else ''} first")
    return list(merged.values()), label


def tally(sweep):
    """Per driver crate, plus the corpus-level denominators.

    Registers are counted per CHIP, not per pairing: two crates paired with the
    same chip see the same gates, and adding them twice would inflate the
    injection side to flatter the enforcement side."""
    rows = collections.defaultdict(lambda: collections.Counter())
    chips = collections.defaultdict(set)
    pacs = collections.defaultdict(set)
    regs_by_chip, gates_by_chip = {}, {}
    unmeasurable = collections.Counter()

    for r in sweep:
        if r.get("inject") != "ok":
            continue
        chip = (r["rm"], r["device"])
        regs_by_chip[chip] = _n(r.get("planned"))
        for h in r.get("hal_results") or []:
            crate = h.get("crate")
            # A pairing whose driver does not build against the PRISTINE chip
            # crate is broken for its own reasons; anything measured on top of
            # it would be miscounted as ours.
            if h.get("baseline") != "PASS":
                unmeasurable[crate] += 1
                continue
            chips[crate].add(chip)
            pacs[crate].add(r["pac"])
            c = rows[crate]
            c["pairings"] += 1
            c["fired"] += _n(h.get("true_enforcement"))
            c["guarded"] += _n(h.get("guarded"))
            c["candidate"] += _n(h.get("candidate"))
            c["friction"] += _n(h.get("generic_friction"))
            c["other"] += _n(h.get("other"))
    for crate, c in rows.items():
        # Every PAC crate is stm32<family> 0.16.0, so the shared prefix and the
        # version are stated once in the caption and the cell carries only what
        # differs between rows.
        c["pacs"] = ", ".join(sorted(s.replace("stm32", "", 1)
                                     for s in pacs[crate]))
        c["regs"] = sum(regs_by_chip.get(k, 0) for k in chips[crate])
        c["chips"] = len(chips[crate])
        # Neither a guard nor a bug -- reported, never folded into either.
        c["untriaged"] = max(0, c["fired"] - c["guarded"] - c["candidate"])
    corpus = {
        "targets": sum(1 for r in sweep if r.get("inject") == "ok"),
        "pac_pass": sum(1 for r in sweep
                        if r.get("inject") == "ok" and r.get("probe") == "PASS"),
        "regs": sum(regs_by_chip.values()),
        "unmeasurable": sum(unmeasurable.values()),
    }
    return rows, corpus


# "chips" is deliberately absent: every crate pairs with each chip exactly
# once, so it would restate "pairings" in a second column.
_COLS = ["pacs", "regs", "fired", "guarded", "candidate", "untriaged",
         "friction", "pairings"]


def latex(per_mode, label_mode=False):
    L = [r"\begin{table*}[t]", r"\centering",
         r"\caption{Datasheet access constraints compiled into vendor PAC "
         r"crates, and the compile-time obligations they place on unmodified "
         r"driver crates. A gate that fires is not a defect: it reports that "
         r"the driver performed a constrained operation without a witness, "
         r"which correct code can also do. Only \emph{possible bug} counts "
         r"sites where no precondition check was found. Every PAC crate is "
         r"\texttt{stm32<family>} version 0.16.0; the column lists the "
         r"families each driver was compiled against.}",
         r"\label{tab:pac_enforcement}", r"\footnotesize",
         r"\begin{tabular}{l" + ("l" if label_mode else "") + "lrrrrrrr}",
         r"\toprule",
         r"\textbf{Driver crate} &" + (r" \textbf{Gating} &" if label_mode else ""),
         r"\textbf{PAC crates} &",
         r"\textbf{Registers} &",
         r"\multicolumn{4}{c}{\textbf{Gate fired}} &",
         r"\textbf{Generic} &",
         r"\textbf{Chip} \\"]
    a = 5 if label_mode else 4
    L += [r"\cmidrule(lr){%d-%d}" % (a, a + 3),
          (r"&" + (r" &" if label_mode else "")) + r" & \textbf{gated} &",
          r"\textbf{total} & \textbf{already} & \textbf{possible} & "
          r"\textbf{un-} & \textbf{friction} & \textbf{pairings} \\[-0.5ex]",
          (r"&" + (r" &" if label_mode else "")) + r" & &",
          r"& \textbf{guarded} & \textbf{bug} & \textbf{triaged} & & \\",
          r"\midrule"]

    crates = sorted({c for rows, _ in per_mode.values() for c in rows},
                    key=lambda c: -max(rows.get(c, {}).get("fired", 0)
                                       for rows, _ in per_mode.values()))
    for crate in crates:
        for i, (mode, (rows, ml)) in enumerate(per_mode.items()):
            c = rows.get(crate)
            name = _tex(crate) if i == 0 else ""
            cells = ([_tex(ml)] if label_mode else []) + [
                (r"\texttt{%s}" % _tex(c[k]) if c and k == "pacs"
                 else str(c[k]) if c else "--")
                for k in _COLS]
            L.append(f"{name} & " + " & ".join(cells) + r" \\")
        if label_mode:
            L.append(r"\addlinespace[2pt]")
    L.append(r"\midrule")
    for mode, (rows, ml) in per_mode.items():
        tot = {k: sum(c[k] for c in rows.values())
               for k in _COLS if k != "pacs"}
        # A union of PAC crates across drivers is not a meaningful total; the
        # corpus-wide count of injected crates lives in the caption instead.
        tot["pacs"] = "--"
        cells = ([_tex(ml)] if label_mode else []) + [str(tot[k]) for k in _COLS]
        L.append(r"\textbf{Total} & " + " & ".join(cells) + r" \\")
    L += [r"\bottomrule", r"\end{tabular}", r"\end{table*}"]
    return "\n".join(L)


def _tex(s):
    return str(s).replace("_", r"\_")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mode", choices=["default", "field", "both"],
                    default="default")
    ap.add_argument("--csv", help="also write the raw numbers here")
    args = ap.parse_args()

    modes = ["default", "field"] if args.mode == "both" else [args.mode]
    per_mode, corpora = {}, {}
    for m in modes:
        sweep, label = load(m)
        rows, corpus = tally(sweep)
        per_mode[m] = (rows, label)
        corpora[m] = corpus

    print(latex(per_mode, label_mode=(args.mode == "both")))
    for m in modes:
        c = corpora[m]
        print(f"% {MODES[m][1]}: {c['targets']} chip crates injected, "
              f"{c['pac_pass']}/{c['targets']} compile, "
              f"{c['regs']} registers gated corpus-wide; "
              f"{c['unmeasurable']} pairing(s) excluded (baseline fails "
              f"against the pristine crate).", file=sys.stderr)

    if args.csv:
        import csv
        with open(args.csv, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["mode", "crate"] + _COLS)
            for m in modes:
                rows, _ = per_mode[m]
                for crate, c in sorted(rows.items()):
                    w.writerow([m, crate] + [c[k] for k in _COLS])
        print(f"csv: {args.csv}", file=sys.stderr)


if __name__ == "__main__":
    main()
