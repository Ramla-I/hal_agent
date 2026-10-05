# Results — Intel 82599 intralingual-HAL case study

**One line:** the extraction pipeline generated the complete register model of
a 10 GbE NIC from its datasheet; dropped into the real Theseus `ixgbe` driver
it compiled after exactly 3 adaptations (1 rename, 2 adjudicated RO-vs-init-write
divergences), it found one real bit-position bug in the hand-written HAL, and
its extracted access constraints became compile-time witness gates the original
HAL never had — at a driver-diff cost of 2 files, +12/−5 lines.

## Setup (reproduction identifiers at the bottom)

- **Targets:** the 75 registers of Theseus `regs.rs` (63 touched by the current
  driver); recall denominator: the PF BAR0 register summary (Table 8-2),
  406 rows / 380 unique registers, parsed deterministically from `82599.md`.
- **Pipeline:** vendored evolved retriever (per-register chunk selection) →
  gpt-oss-120b, batch size 1, Intel prompt variant with the unchanged
  grammar-v2 constraint schema; bounded completion passes with full-page
  context expansion; final pass escalates 5 registers to gpt-5.2.
  97 LLM calls, 693 k input / 199 k output tokens (≲ $1).

## Structural recall (compile metric)

| Check | Result |
|---|---|
| First drop-in compile errors | **3** (1 naming, 2 access divergences — see friction ledger C1/C2) |
| After 1 name_map entry + 2 adjudicated overrides | **green** (`cargo check` and full `cargo build -p ixgbe`, Theseus target, unmodified driver) |
| Region size asserts (7 structs + whole-space 0x20000) | **all pass** — byte-exact 128 KiB layout, so every padding run derived from extracted offsets is correct |
| Extracted offsets vs deterministic Table 8-2 parse | **75/75 agree**, 0 fallbacks, 0 collisions |
| Driver constants (71 referenced) | **54 field-derived from extraction** (53 agree with the reference, 1 disagreement = finding 1), 17 policy values kept verbatim |
| Register access types vs reference | 65/75 identical; 8 divergences are *stricter-than-reference* datasheet typing (RC/RO statistics and link registers the driver only reads → `ReadOnly`), 2 are C1/C2 |

Retrieval/extraction failure modes were measurable and attributable: the saved
per-register contexts show every initial miss came from bit tables running past
chunk/page boundaries (fixed by the completion pass for 10, then 5, then 3
registers — the last 3 needed model escalation, not more context).

## Findings (real divergences, adjudicated against the datasheet)

1. **Theseus bug — `RDRXCTL_CRC_STRIP = 1` sets a reserved bit.** The datasheet
   has RDRXCTL.CRCStrip at **bit 1** (bit 0 is not a field) and states "This
   bit must be set the same as HLREG0.RXCRCSTRP". The driver sets HLREG0 bit 1
   correctly but RDRXCTL bit 0, so CRC stripping is never enabled in the Rx
   DMA unit and the stated consistency rule is violated. Found as the single
   derived-vs-reference constant disagreement; our extraction also captured
   the consistency rule itself as a `value_relation` constraint on both
   registers. The generated HAL's field-derived constant silently repairs it.
2. **RDH/TDH: datasheet RO vs. required init write.** The compile surfaced the
   contradiction; TDH's own description contains the authorization ("only
   after a reset and before enabling"), which the constraint layer turns into
   the witness-gated write — a more faithful type than either the reference's
   plain `Volatile` or naive RO typing.
3. **Grammar-as-validator:** 5 of 34 raw constraints were rejected by strict
   schema parsing; one rejection caught a real misattribution — FWSM's "only
   firmware may write this register" note attached to SW_FW_SYNC (the register
   the driver's semaphore protocol must write). A lenient collector would have
   produced a false driver-breaking gate.
4. **Datasheet-internal inconsistencies** (from the two-source cross-check):
   GPRC/GPTC access codes swapped between summary and detail; EITR second
   range printed as `n=24...128`.

## Constraint encoding (the safety the hand-written HAL lacks)

34 raw constraints → 29 grammar-valid across 26 registers. Encoding is
**field-level by default** (a case-study extension of the settled 4-class
enforceability taxonomy, which stays untouched in `defs.py`): a gated register
loses its raw `write()` — it exposes `write_preserving()` (structurally cannot
change protected bits; never-set bits forced to 0) plus, where a witness
exists, `write_full(value, &Witness)`; whole-register gates (`target_fields=[]`)
expose only `write(value, &Witness)`.

**8 of 29 constraints encoded, on 8 registers:**

| Register | Constraint | Encoding |
|---|---|---|
| FCTRL | write only while RXCTRL.RXEN=0 | whole-register witness (`RxctrlRxenCleared`: establish clears RXEN, release re-enables) |
| TDH | write only after reset, before TXDCTL.ENABLE | whole-register witness (`TxdctlEnableCleared`; minting clears ENABLE — the type forces the precondition) |
| EEC | EE_SK/EE_CS/EE_DI/EE_REQ usable only when EE_GNT=1 (hardware-established) | field gate + **check-minted state witness**: `check_ee_gnt() -> Option<EecEeGntSet>` |
| EIAM | Auto Mask bits require GPIE.EIAME set | field gate + set-mode action witness (`GpieEiameSet::establish`, no release — condition must persist) |
| EIAC | bits that share the MSI-X vector "should never set auto clear" | **never-set clamp**: `write_preserving` forces them to 0 — the illegal value is unrepresentable |
| HLREG0 + RDRXCTL | RXCRCSTRP "must be set the same as" CRCStrip (2 constraints, stated on both sides) | **coupled setter** `set_rxcrcstrp_crcstrip(a, b, enable)`; independent writes preserve both bits — the inconsistent state (finding 1!) is unwritable |
| DMATXCTL | "software must not change" the VT field | **hold mask**: no API can change it |

**The 21 not encoded, with computed/deterministic reasons** (all recorded in
`emit_report.json`): 7 `read_effect` + 6 `other` + CTRL's bare delay are
doc/runtime-tier by the computed taxonomy; 5 `value_relation`s whose semantics
live in the value (RDBAL/TDBAL 128-byte alignment, SRRCTL and EITR
conditionals, FCRTH inequality) are invisible at `u32` granularity — they need
typed value builders (runtime-checked constructors) and stay runtime-tier; 1
`state_gate` shape (TXDCTL's WTHRESH note arrived as `other`) fits no rule.

**Enforcement demonstrated:** the *unmodified* driver against the gated HAL
fails with **9 errors at 9 sites — every one a datasheet-relevant write**
(fctrl, set_tdh, the two CRC-strip lines, the second hlreg0 site, both
dmatxctl TE toggles, eiac). The adoption diff is **2 files, +27/−15** — and it
*deletes the CRC-strip bug*: the two independent ORs (one with the wrong bit)
become one `set_rxcrcstrp_crcstrip(..., true)` call, so finding 1 cannot be
re-introduced. After the diff, `cargo check` and `cargo build` are green.

Honest limits: witnesses are type-level, not instance-bound (a witness token minted
for queue 3 type-checks a write to queue 5); minting/checking still reads
hardware at runtime (TOCTOU parity with a correct handwritten driver, as
settled for the MCU arm); the AUTOC SW/FW-semaphore protocol remains doc-only
because §10.5.4 is outside the register chapter in our source md.

## Reproduction

```bash
cd intel_82599_hal/pipeline
python3 enumerate_targets.py                 # targets/ (committed)
python3 generate.py                          # run rNNN (gpt-oss-120b, batch 1)
python3 generate.py --complete-from rNNN --max-output-per-reg 12000
python3 generate.py --complete-from rNNN+1 --extra-pages 4 --max-output-per-reg 12000
python3 generate.py --complete-from rNNN+2 --model gpt-5.2 --extra-pages 4 --max-output-per-reg 12000
python3 collect_constraints_intel.py rFINAL
python3 emit_hal.py rFINAL                   # structural  -> hal_out/rFINAL/regs.rs
python3 emit_hal.py rFINAL --gated           # constraint  -> hal_out/rFINAL-gated/regs.rs
# eval: clone theseus-os/Theseus @ 1fbfe567, init submodules, swap regs.rs,
#   cargo check -p ixgbe -Z unstable-options -Z build-std=core,alloc \
#     -Z build-std-features=compiler-builtins-mem --target x86_64-unknown-theseus
# gated config: also apply pipeline/driver_diff_gated.patch
```

Identifiers: runs r003–r006 (per-run `run_manifest.jsonl` with content hashes);
retriever sha256 `76079e03…ad655` (v6_82599_seed42); generator gpt-oss-120b
(Groq), escalation gpt-5.2 (OpenAI); driver reference theseus-os/Theseus
`1fbfe567`; toolchain nightly-2023-10-27, target x86_64-unknown-theseus.
