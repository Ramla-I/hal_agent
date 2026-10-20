# Step 2 — reinject the STM corpus with the new kinds, triage for new bugs

After shipping `write_once` / `sequence` / `delay` (plan §14), reinject the STM
generator corpus with these kinds enabled and look for a bug the pre-existing
`state_gate`-only pipeline could not see. **Result: no new real bug surfaced.**
The new-kind firings are dominated by documented false-positive classes.

## What the new kinds actually gate on real STM data

Corpus-wide hard-gating (bug-candidate) constraints across 48 manuals:

| kind (hard-gating variant) | count | what the registers are |
|---|---|---|
| gated `sequence` (same-reg, constant value) | 245 | FLASH KEYR/OPTKEYR, GPIO LCKR, RTC WPR/write-protect, SYSCFG keys — **handshake registers** |
| whole-register `write_once` | 49 | 33 security locks (SECCFGR/RCFGLOCKR/…), 11 "config once" (OTG_*CFG, FMC_SDRTR), 5 key/unlock |
| same-register `delay` (has `before`) | 12 | ordering on config registers |

Two structural facts blunt the bug yield:
1. **Sequence step-values are largely unextracted (`null`)** → the magic-value
   heuristic routes those to *advisory* (raw write stays open, no firing). Only
   245/901 sequences are same-register **and** carry a constant, i.e. gated.
2. The gated registers are **handshakes / locks / keys** — registers a correct
   HAL writes raw (it implements the unlock/sequence itself). The gate cannot
   tell a correct raw sequence from a wrong one; it only forbids raw access.

## Coverage (what could actually be compiled)

Injection into a svd2rust PAC + compiling that family's HAL needs (a) a PAC in a
dialect the injector supports and (b) a HAL pinned to that PAC version.

| family | manual | reachable? | outcome |
|---|---|---|---|
| F4 | rm0090 | ✅ stm32f4xx-hal (PAC 0.16) | clean — only advisory GPIO_LCKR/PWR_CR seqs, 0 firings |
| G4 | rm0440 | ✅ stm32g4xx-hal 0.1.0 (PAC 0.16) | 12 seq + 1 delay gated; 1 firing = trait-generic friction in `stm32-hrtim` (`MasterExt::ICRrs`), **not a bug** |
| G0 | rm0444 | ❌ stm32g0xx-hal pins PAC 0.14 | PAC 0.14 is a 3rd svd2rust dialect the injector doesn't recognize |
| F0 | rm0360 | ❌ stm32f0xx-hal pins PAC 0.14 | same dialect gap |
| U5/H5 | rm0456/rm0486 | ❌ no svd2rust HAL | the write_once-heavy families have embassy-only support |

Where a HAL couldn't be compiled, the bug-candidate `write_once` registers were
triaged **statically against their real drivers**.

## write_once triage (the only non-handshake bug class)

- **OTG_DCFG** ("do not change after initial programming", F4/H7/U5/H5) →
  **FALSE POSITIVE.** `synopsys-usb-otg` rewrites DCFG after init, but only the
  **DAD (device-address) field** — on bus reset and SET_ADDRESS, which USB
  *requires*. The datasheet caveat is about the speed/PHY fields (DSPD/PFIVL),
  not the address. A whole-register write_once is over-broad here (exactly why
  field-scoped write_once is handled separately and whole-register-only is the
  conservative default).
- **FMC_SDRTR** ("must not be reprogrammed after initialization") → **COMPLIANT.**
  `stm32-fmc` writes SDRTR once at init (sdram.rs step 6) and only reads it
  afterward. No violation.
- The remaining 33 whole-register write_once are **security-lock** registers
  (SECCFGR, RCFGLOCKR, DECPROT_LOCK, option bytes) — HALs don't touch them, so
  no firing and nothing to triage.

## Conclusion

The three new kinds compile and gate correctly (full test suite + a real-HAL
demo prove the mechanism). On the real STM corpus they surface **no new bug**:
the hard gates land on handshake/lock/key/config registers that correct drivers
write legitimately, and the one "config once" lead that a driver does rewrite
(OTG_DCFG) is a legit post-init address update. This mirrors the broader finding
that real driver bugs cluster in the `state_gate` clobber / configure-after-
enable classes, not in once/order/delay rules.

### Follow-ups surfaced
- **Injector dialect gap:** svd2rust `generic.rs` of the 0.14-era stm32g0/stm32f0
  PACs (early-style but comma-less where-clauses) is unrecognized — blocks the
  G0/F0 HALs. A `_DIALECTS` entry would unlock them (file as an issue).
- U5/H5 (the write_once-heavy families) need the embassy/chiptool arm to reach a
  downstream, but that arm only emits `state_gate` today.
