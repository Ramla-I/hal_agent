#!/usr/bin/env python3
"""Expand derivedFrom peripherals in a COMPLETE verified datasheet.

The verified CSV is compact: a peripheral that derives from another (e.g. GPIOB <- GPIOA)
is not re-annotated — it carries only its own `base_address` row (with `derived_from`
naming the prototype) and inherits the prototype's register/field layout. This script
materializes that inheritance: for every derived peripheral it copies the prototype's
register/field rows under the derived peripheral's name, keeping the derived peripheral's
own base_address. The absolute address of any register is then base_address + address_offset.

Input stays untouched; the expansion is written to `<name>_expanded.csv` beside it, so the
compact CSV remains the source of truth. Idempotent: always run it on the compact CSV.

    source .venv/bin/activate
    python3 verified_datasheet/expand_derived.py verified_datasheet/stm/rm0041_stm32f100.csv
    # or with no args: expand every verified_datasheet/<mfg>/*.csv (skips *_old / *_expanded)
"""
import csv
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import annotate  # noqa: E402  (path set above)


def expand(csv_path):
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        rows = list(reader)

    def periph(r):
        return (r.get("peripheral") or "").lower()

    def is_layout(r):                         # a register/field row (not base_address / not marker)
        return bool(r.get("register"))

    def is_base(r):
        return (r.get("key") or "") == annotate.PERIPH_KEY and not r.get("register")

    # derived peripheral -> prototype, from any row carrying derived_from
    proto_of = {}
    for r in rows:
        d = (r.get("derived_from") or "").lower()
        if d:
            proto_of.setdefault(periph(r), d)

    if not proto_of:
        print(f"  {csv_path}: no derived peripherals — nothing to expand")
        return

    layout = {}                               # prototype -> its register/field rows, in order
    base_row = {}                             # peripheral -> its base_address row
    for r in rows:
        if is_layout(r):
            layout.setdefault(periph(r), []).append(r)
        elif is_base(r):
            base_row[periph(r)] = r

    # completeness warning (prototypes feed the copies, so surface unfinished ones)
    pending = sum(1 for r in rows if is_layout(r) and not (r.get("status") or ""))
    if pending:
        print(f"  WARNING {csv_path}: {pending} register/field cells still pending — "
              f"expanded copies inherit those blanks")

    missing = sorted(d for d in proto_of.values() if d not in layout)
    if missing:
        print(f"  WARNING {csv_path}: prototypes not found in CSV: {missing}")

    out, done, n_exp = [], set(), 0
    for r in rows:
        p = periph(r)
        if p in proto_of:
            if p in done:                     # other compact rows for this derived periph (markers, dups)
                continue
            done.add(p)
            proto = proto_of[p]
            if p in base_row:                 # keep the derived peripheral's own base address
                out.append(base_row[p])
            for lr in layout.get(proto, []):  # materialize the inherited layout
                nr = {k: lr.get(k, "") for k in fields}
                nr["peripheral"] = p
                if "derived_from" in nr:
                    nr["derived_from"] = proto
                nr["set_method"] = "derived-expanded"
                out.append(nr)
                n_exp += 1
            continue
        out.append(r)

    stem, ext = os.path.splitext(csv_path)
    out_path = f"{stem}_expanded{ext}"
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(out)
    print(f"  {csv_path}: expanded {len(proto_of)} derived peripherals "
          f"(+{n_exp} rows) -> {out_path}")


def main():
    if len(sys.argv) > 1:
        targets = sys.argv[1:]
    else:
        targets = [p for p in sorted(glob.glob(os.path.join(HERE, "*", "*.csv")))
                   if not p.endswith(("_old.csv", "_expanded.csv"))]
    if not targets:
        print("No verified CSVs found.")
        return
    for p in targets:
        expand(p)


if __name__ == "__main__":
    main()
