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
  context expansion; final pass escalates to gpt-5.2.
  97 LLM calls, 693 k input / 199 k output tokens (≲ $1).

### Generator retry cadence (across the 75 registers)

The batched first pass extracted 65 of 75 registers cleanly. The rest were
recovered by the enhanced retry mechanism, and the cadence itself is a result —
most registers need nothing, and model escalation is reserved for the genuine
residue:

| Outcome | Count | Registers |
|---|---:|---|
| Clean on the first batched pass (no retry) | 65 | — |
| Needed ≥1 **context-expansion** retry (runs r004/r005) | 10 | AUTOC, EICR, HLREG0, L34TIMIR, LINKS, RTTDCS, SRRCTL, SWSM, SW_FW_SYNC, TXDCTL |
| Of those, **escalated to gpt-5.2** (run r006) | 5 | AUTOC, HLREG0, L34TIMIR, LINKS, TXDCTL |
| — genuine unresolved miss that gpt-5.2 actually fixed | 3 | L34TIMIR, LINKS, TXDCTL |
| — swept in by the conservative `hi<31` coverage trigger, no real miss | 2 | AUTOC, HLREG0 |

The expansion trigger fires when a register's extracted subfields fail to span
bits 0–31 **or** a driver-needed field is missing. The two "no real miss" cases
(AUTOC, HLREG0) are false positives of the first clause: their datasheet field
tables legitimately end below bit 31 (at 24 and 19), with no fields documented
above, so `hi<31` holds and the gate flags them — the full subfield census
confirms 0 missed fields for both, and gpt-5.2 reproduced the same coverage.
Separately, 2 registers (AUTOC, LINKS) hit a `NO JSON` truncation on the base
pass and were recovered by a same-model budget resume (larger output-token
limit, same context) before any expansion; both are already in the 10 above.

## Structural recall (compile metric)

| Check | Result |
|---|---|
| First drop-in compile errors | **3** (1 naming, 2 access divergences — see friction ledger C1/C2) |
| After 1 name_map entry + 2 adjudicated overrides | **green** (`cargo check` and full `cargo build -p ixgbe`, Theseus target, unmodified driver) |
| Region size asserts (7 structs + whole-space 0x20000) | **all pass** — byte-exact 128 KiB layout, so every padding run derived from extracted offsets is correct |
| Extracted offsets vs deterministic Table 8-2 parse | **75/75 agree**, 0 fallbacks, 0 collisions |
| Register access codes vs datasheet section headings | **75/75 match** (RW/RO/WO/RC); field-level RO/WO/RW typing derives from them |
| Reset values (from the per-field Init Val column) | **55/75 defined**; the other 20 are correctly null (datasheet Init Val `X`/undefined) |
| Subfield bit positions (start + width), full datasheet-table census | **404/406 (99.5%)** correct; 2 spurious fields in reserved bits (see subfield census) |
| Driver constants (71 referenced) | **54 field-derived from extraction** (53 agree with the reference, 1 disagreement = finding 1), 17 policy values kept verbatim |
| Register access types vs reference | 65/75 identical; 8 divergences are *stricter-than-reference* datasheet typing (RC/RO statistics and link registers the driver only reads → `ReadOnly`), 2 are C1/C2 |

Retrieval/extraction failure modes were measurable and attributable: the saved
per-register contexts show every initial miss came from bit tables running past
chunk/page boundaries (fixed by the completion pass for 10, then 5, then 3
registers — the last 3 needed model escalation, not more context).

> **Structure audit (`pipeline/audit_structure.py` → `reports/audit_structure.json`, added 2026-10-07).** A standalone datasheet referee for the non-subfield dimensions (parallel to the subfield audits): **offsets 75/75** and **access codes 75/75** agree with the datasheet headings; **reset values 71/75 exact, 0 wrong** — the 4 non-matches are benign (3 `missing`: extraction nulled a defined reset FCRTL/HLREG0/RDRXCTL; 1 `extra`: AUTOC2 gave 0x0 vs a `*`-soft default), and reset values aren't consumed by this HAL. Closes the one structure dimension that previously had only a coverage count.

## Findings (real divergences, adjudicated against the datasheet)

1. **Theseus bug — `RDRXCTL_CRC_STRIP = 1` sets a reserved bit.** The datasheet
   has RDRXCTL.CRCStrip at **bit 1** (bit 0 is not a field) and states "This
   bit must be set the same as HLREG0.RXCRCSTRP". The driver sets HLREG0 bit 1
   correctly but RDRXCTL bit 0, so CRC stripping is never enabled in the Rx
   DMA unit and the stated consistency rule is violated. Found as the single
   derived-vs-reference constant disagreement; our extraction also captured
   the consistency rule itself as a `value_relation` constraint on both
   registers. The generated HAL's field-derived constant silently repairs it.
2. **Theseus bug — RXCSUM (and the RSS block) written while the receiver is
   enabled.** Found by re-scanning the drivers against a constraint the first
   extraction missed and the recall improvement recovered: RXCSUM's
   `state_gate` "This register should only be initialized (written) when the
   receiver is not enabled … RXCTRL.RXEN = 0b" (enforceability
   *action_witnessed*). `rx_init` ends by enabling the receiver, then
   `enable_rss` (lib.rs:912) writes `rxcsum` — and MRQC/RSSRK/RETA — with no
   re-disable. Same configure-after-enable root cause as the FCTRL promiscuous
   bug; Theseus-only (ixy/Redox/RedLeaf don't configure RXCSUM). The 9th bug,
   and a direct demonstration that improving constraint recall yields new bugs.
3. **RDH/TDH: datasheet RO vs. required init write.** The compile surfaced the
   contradiction; TDH's own description contains the authorization ("only
   after a reset and before enabling"), which the constraint layer turns into
   the witness-gated write — a more faithful type than either the reference's
   plain `Volatile` or naive RO typing.
4. **Grammar-as-validator:** 5 of the 34 constraints found in run r006 were
   rejected by strict schema parsing (EICR, EITR, RETA, RTTDCS, SW_FW_SYNC);
   one rejection caught a real misattribution — FWSM's "only
   firmware may write this register" note attached to SW_FW_SYNC (the register
   the driver's semaphore protocol must write). A lenient collector would have
   produced a false driver-breaking gate.
5. **Datasheet-internal inconsistencies** (from the two-source cross-check):
   GPRC/GPTC access codes swapped between summary and detail; EITR second
   range printed as `n=24...128`.

## Constraint encoding (the safety the hand-written HAL lacks)

> **Durable list + update (2026-10-07).** **39 access constraints were found** in total —
> 29 grammar-valid + 5 schema-dropped in run r006, plus **5 recovered** by the
> constraint-recall improvement (RXCSUM, RDLEN, TDLEN, DAQF, SDPQF) in a later run. The
> **5 dropped** (EICR, EITR, RETA, RTTDCS, SW_FW_SYNC) failed grammar-v2 schema parsing;
> the **34 kept** (29 canonical + 5 recovered) are recorded in
> **`reports/constraints_found.{md,json}`**. Improving constraint recall also surfaced a **9th driver bug**: the
> recovered RXCSUM `state_gate` ("write only when RXCTRL.RXEN=0b", enforceability
> *action_witnessed*) is violated by **Theseus** — `rx_init` enables the receiver, then
> `enable_rss` writes RXCSUM (and the RSS block) with no re-disable; same configure-after-
> enable root cause as the FCTRL promiscuous bug. ixy/Redox/RedLeaf don't configure RXCSUM.


Of the **39 constraints found** (34 in run r006 + 5 recovered later), **5 were
dropped** for grammar-v2 schema inconsistency, leaving **34 kept** — the 29
grammar-valid from run r006 plus the 5 recovered, folded together (the recovered
set is committed as `config/recovered_constraints.json` and folded in with
`s4_emit_hal.py --gated --extra-constraints`). The gated emitter encodes over
this combined **34**. Encoding is **field-level by default** (a case-study extension of the settled 4-class
enforceability taxonomy, which stays untouched in `defs.py`): a gated register
loses its raw `write()` — it exposes `write_preserving()` (structurally cannot
change protected bits; never-set bits forced to 0) plus, where a witness
exists, `write_full(value, &Witness)`; whole-register gates (`target_fields=[]`)
expose only `write(value, &Witness)`.

**9 of those 34 encoded, on 9 registers:**

| Register | Constraint | Encoding |
|---|---|---|
| FCTRL | write only while RXCTRL.RXEN=0 | whole-register witness (`RxctrlRxenCleared`: establish clears RXEN, release re-enables) |
| RXCSUM | write only while RXCTRL.RXEN=0 (recovered constraint; = bug #9) | whole-register witness (same `RxctrlRxenCleared`); the constraint that *found* bug #9 is now an *enforced* gate |
| TDH | write only after reset, before TXDCTL.ENABLE | whole-register witness (`TxdctlEnableCleared`; minting clears ENABLE — the type forces the precondition) |
| EEC | EE_SK/EE_CS/EE_DI/EE_REQ usable only when EE_GNT=1 (hardware-established) | field gate + **check-minted state witness**: `check_ee_gnt() -> Option<EecEeGntSet>` |
| EIAM | Auto Mask bits require GPIE.EIAME set | field gate + set-mode action witness (`GpieEiameSet::establish`, no release — condition must persist) |
| EIAC | bits that share the MSI-X vector "should never set auto clear" | **never-set clamp**: `write_preserving` forces them to 0 — the illegal value is unrepresentable |
| HLREG0 + RDRXCTL | RXCRCSTRP "must be set the same as" CRCStrip (2 constraints, stated on both sides) | **coupled setter** `set_rxcrcstrp_crcstrip(a, b, enable)`; independent writes preserve both bits — the inconsistent state (finding 1!) is unwritable |
| DMATXCTL | "software must not change" the VT field | **hold mask**: no API can change it |

**The 25 not encoded, with computed/deterministic reasons** (all recorded in
`emit_report.json`): 7 `read_effect` + 10 `other` + CTRL's bare delay are
doc-only/dynamic-check by the computed taxonomy (18 total, including TXDCTL's
WTHRESH note that arrived as `other` and DAQF/SDPQF's "init by software"); 7
`value_relation`s whose semantics live in the value (RDBAL/TDBAL/RDLEN/TDLEN
128-byte alignment, SRRCTL and EITR conditionals, FCRTH inequality) are
invisible at `u32` granularity and are **not encoded — no runtime check is
emitted** (enforcing them would need typed value builders, i.e. runtime-checked
constructors).

**Enforcement demonstrated:** the *unmodified* driver against the gated HAL
fails with **10 errors at 10 sites — every one a datasheet-relevant write**
(fctrl, set_tdh, the two CRC-strip lines + the RDRXCTL RSCFRSTSIZE line, the
second hlreg0 site, both dmatxctl TE toggles, eiac, and **rxcsum** — the gate
from the recovered constraint, = finding 2/bug #9). The adoption diff is
**2 files, +40/−18** — and it *deletes the CRC-strip bug*: the two independent
ORs (one with the wrong bit) become one `set_rxcrcstrp_crcstrip(..., true)`
call, so finding 1 cannot be re-introduced; it also *fixes bug #9* by moving the
RSS/RXCSUM config into a witness window where RXCTRL.RXEN is cleared. After the
diff, `cargo check` and `cargo build` are green.

Honest limits (all reported by the emitter, never silently assumed — see the
`KNOWN LIMITATIONS` block in `s4_emit_hal.py`):
- **Register provenance (#1).** In the default emitter an establish-minted
  witness mints from any `&mut Volatile<u32>` the caller *claims* is the
  prerequisite register — the type does not prove it is the right register. A
  variant emitter, `s4b_emit_hal_minted.py`, closes the register-**type** hole:
  it mints each witness through the prerequisite register's own newtype (a
  non-gated prerequisite becomes a `<Reg>Minter`; a gated one folds the minter
  into its `Gated*` impl), so only that register can produce the token. This
  variant **compiles green** against Theseus (the generated HAL itself builds —
  layout asserts pass — and the driver adoption is the gated diff plus exactly 3
  one-for-one lines: `RxctrlRxenCleared::establish(&mut regs.rxctrl)` becomes
  `regs.rxctrl.clear_rxen()`, same for TDH/TXDCTL, and the release;
  `driver_diff_gated_minted.patch`). Register-**instance**/device binding
  (branded lifetimes) and TOCTOU (a retained borrow) remain future work; minting
  and checking still read hardware at runtime (TOCTOU parity with a correct
  handwritten driver, as settled for the MCU arm). Witnesses are still
  type-level, not queue-instance-bound (a token minted for queue 3 type-checks a
  write to queue 5).
- **Single witness slot (#2)** and **uninstantiable check witness (#3).** Each
  gated register carries one witness token type; a second, different witness and
  a check witness whose prerequisite register is not itself gated are both
  detected and recorded (`witness_conflicts`, `uninstantiable_witnesses` in
  `emit_report.json`) rather than silently mis-encoded — neither fires on r006.
- **Coupled setter atomicity (#4).** A coupled relation setter is two separate
  volatile writes; the two registers are momentarily unequal between them. The
  invariant holds at rest, not continuously.
- The AUTOC SW/FW-semaphore protocol remains doc-only because §10.5.4 is outside
  the register chapter in our source md.

## Reproduction

```bash
cd intel_82599_hal/pipeline
python3 s1_enumerate_targets.py                 # targets/ (committed)
python3 s2_generate.py                          # run rNNN (gpt-oss-120b, batch 1)
python3 s2_generate.py --complete-from rNNN --max-output-per-reg 12000
python3 s2_generate.py --complete-from rNNN+1 --extra-pages 4 --max-output-per-reg 12000
python3 s2_generate.py --complete-from rNNN+2 --model gpt-5.2 --extra-pages 4 --max-output-per-reg 12000
python3 s3_collect_constraints.py rFINAL
python3 s4_emit_hal.py rFINAL                   # structural  -> hal_out/rFINAL/regs.rs
python3 s4_emit_hal.py rFINAL --gated           # constraint  -> hal_out/rFINAL-gated/regs.rs
python3 s4b_emit_hal_minted.py rFINAL           # provenance  -> hal_out/rFINAL-gated-minted/regs.rs
# eval: clone theseus-os/Theseus @ 1fbfe567, init submodules, swap regs.rs,
#   cargo check -p ixgbe -Z unstable-options -Z build-std=core,alloc \
#     -Z build-std-features=compiler-builtins-mem --target x86_64-unknown-theseus
# gated config: also apply theseus_retrofit/driver_diff_gated.patch
# provenance config: swap the -gated-minted regs.rs + apply driver_diff_gated_minted.patch
```

Identifiers: runs r003–r006 (per-run `run_manifest.jsonl` with content hashes);
retriever sha256 `76079e03…ad655` (v6_82599_seed42); generator gpt-oss-120b
(Groq), escalation gpt-5.2 (OpenAI); driver reference theseus-os/Theseus
`1fbfe567`; toolchain nightly-2023-10-27, target x86_64-unknown-theseus.
