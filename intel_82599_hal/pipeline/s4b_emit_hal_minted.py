#!/usr/bin/env python3
"""Step 4 (alternate emitter) — the provenance-hardened variant of
s4_emit_hal.py --gated. It shares the ENTIRE structural engine (offsets, region
layout, array geometry, access typing, driver constants, and the whole gate
planner) with s4_emit_hal.py — the two can never disagree on register layout —
and differs in exactly one thing: HOW a witness token is minted.

Limitation #1 of the default emitter: an establish-minted witness mints from
any `&mut Volatile<u32>` the caller CLAIMS is the prerequisite register
(`Witness::establish(reg)`), so the type does not prove the token came from the
RIGHT register. This variant closes the register-TYPE hole: every witness is
minted THROUGH the prerequisite register's own newtype, so only that register
can produce the token.

  - A prerequisite register that is NOT itself gated becomes a `<Reg>Minter`
    newtype (plain read/write still available for unrelated bits) whose only
    minting method produces the token.
  - A prerequisite register that IS gated folds the minter into its `Gated*`
    impl (e.g. EEC's `check_ee_gnt`).
  - The gated register's `write_full(value, &Witness)` / `write(value, &Witness)`
    is unchanged — the token just can no longer come from the wrong register.

What this still does NOT prove (unchanged from the default, see
s4_emit_hal.py's KNOWN LIMITATIONS): register-INSTANCE / device binding (a token
minted from one RXCTRL instance type-checks against another — needs branded
lifetimes) and TOCTOU (the minter's plain write() can still change the field
after minting — needs a retained borrow). This is a TYPE-provenance fix, not a
value- or instance-level one.

Output: hal_out/<run>-gated-minted/regs.rs + emit_report.json (report gains a
`minted: true` flag and a `minters` map). Requires --gated (forced on).

Usage: python3 s4b_emit_hal_minted.py r006        # (--gated implied)
       python3 s4b_emit_hal_minted.py r006 --plain
"""
import s4_emit_hal


def main():
    args = s4_emit_hal.build_parser().parse_args()
    args.gated = True        # minting only makes sense for the gated configuration
    args.minted = True       # mint each witness through its prerequisite newtype
    s4_emit_hal.run(args)


if __name__ == "__main__":
    main()
