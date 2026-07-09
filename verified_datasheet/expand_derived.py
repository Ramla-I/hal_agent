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


def _periph(r):
    return str(r.get("peripheral") or "").lower()


def _is_layout(r):                            # a register/field row (not base_address / not marker)
    return bool(str(r.get("register") or "").strip())


def _is_base(r):
    return str(r.get("key") or "") == annotate.PERIPH_KEY and not str(r.get("register") or "").strip()


def expand_rows(rows, fields):
    """Pure derivedFrom expansion over a list of dict rows (the single implementation,
    shared by this CLI and optimization_validator/kfold.py).

    For every peripheral carrying a `derived_from` marker, copy the prototype's
    register/field layout rows under the derived peripheral's OWN (original-case) name,
    keeping the derived peripheral's own base_address row. `rows` is a list of dicts,
    `fields` the column order for the copied rows.

    Returns `(out_rows, info)` where info is
    `{"proto_of": {derived: prototype}, "n_expanded": int, "missing_prototypes": [str]}`.
    Callers do their own logging. Returns rows unchanged when nothing derives.
    """
    proto_of = {}                             # derived peripheral -> prototype it inherits from
    for r in rows:
        d = str(r.get("derived_from") or "").lower()
        if d:
            proto_of.setdefault(_periph(r), d)
    if not proto_of:
        return list(rows), {"proto_of": {}, "n_expanded": 0, "missing_prototypes": []}

    layout = {}                               # prototype -> its register/field rows, in order
    base_row = {}                             # peripheral -> its base_address row
    for r in rows:
        if _is_layout(r):
            layout.setdefault(_periph(r), []).append(r)
        elif _is_base(r):
            base_row[_periph(r)] = r

    missing = sorted(d for d in set(proto_of.values()) if d not in layout)

    out, done, n_exp = [], set(), 0
    for r in rows:
        p = _periph(r)
        if p in proto_of:
            if p in done:                     # other compact rows for this derived periph (markers, dups)
                continue
            done.add(p)
            proto = proto_of[p]
            if p in base_row:                 # keep the derived peripheral's own base address
                out.append(base_row[p])
            for lr in layout.get(proto, []):  # materialize the inherited layout
                nr = {k: lr.get(k, "") for k in fields}
                nr["peripheral"] = r.get("peripheral")   # derived peripheral's own (original-case) name
                if "derived_from" in nr:
                    nr["derived_from"] = proto
                nr["set_method"] = "derived-expanded"
                out.append(nr)
                n_exp += 1
            continue
        out.append(r)
    return out, {"proto_of": proto_of, "n_expanded": n_exp, "missing_prototypes": missing}


def expand(csv_path):
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        rows = list(reader)

    out, info = expand_rows(rows, fields)
    if not info["proto_of"]:
        print(f"  {csv_path}: no derived peripherals — nothing to expand")
        return

    # completeness warning (prototypes feed the copies, so surface unfinished ones)
    pending = sum(1 for r in rows if _is_layout(r) and not (r.get("status") or ""))
    if pending:
        print(f"  WARNING {csv_path}: {pending} register/field cells still pending — "
              f"expanded copies inherit those blanks")
    if info["missing_prototypes"]:
        print(f"  WARNING {csv_path}: prototypes not found in CSV: {info['missing_prototypes']}")

    n_exp = info["n_expanded"]
    proto_of = info["proto_of"]
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
