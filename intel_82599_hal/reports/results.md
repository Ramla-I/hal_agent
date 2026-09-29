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

34 raw constraints → 29 grammar-valid across 26 registers (5 state_gate,
7 read_effect, 8 value_relation, 8 other, 1 delay); computed enforceability:
4 action_witnessed, 1 state_witnessed, 1 dynamic_check, 23 doc_only.
The deterministic whole-register action-witness rule (the pac_codegen default,
retargeted to MMIO newtypes) selects **2 gates**, both driver-relevant:

- **FCTRL** — "Before receive filters are updated/modified the RXCTRL.RXEN bit
  should be set to 0b." → `GatedFctrl::write(v, &RxctrlRxenCleared)`; the
  witness is minted by clearing RXEN and consumed by the re-enable.
- **TDH** — "The only time software should write to this register is after a
  reset and before enabling the transmit function." →
  `GatedTdh::write(v, &TxdctlEnableCleared)`; minting the proof *clears
  TXDCTL.ENABLE*, so the type forces the precondition.

**Enforcement demonstrated:** against the gated HAL the *unmodified* driver
fails to compile with exactly two E0061 errors at the two datasheet-relevant
write sites (`lib.rs:827` fctrl, `queue_registers.rs:74` set_tdh) — the gate
firing is the violation demo. After the +12/−5 driver diff both `cargo check`
and `cargo build` are green. The original driver satisfied both rules only
implicitly (RXEN happened to still be 0 during init); the gates make the
ordering structural.

Honest limits: gates are whole-register and type-level (a proof minted for
queue 3 type-checks a write to queue 5 — instance binding would need branded
lifetimes); EIAC/EIAM field-value gates and the CTRL 10 ms post-reset delay
remain runtime concerns; the SW/FW semaphore protocol for AUTOC is only
present as a doc_only note because §10.5.4 lies outside the register chapter
in our source md.

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
