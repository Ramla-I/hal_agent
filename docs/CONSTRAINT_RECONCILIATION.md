# Constraint Reconciliation — when one register has several rules

A register rarely arrives with exactly one rule. A manual may state two
different conditions for it; the same sentence may be extracted twice at
different precision; and every *copy* of a peripheral (I2C1, I2C2, I2C3) is
scanned separately, so one rule can arrive three times.

In Rust those copies share one piece of code — `i2c2`'s `TIMEOUTR` **is**
`i2c1::timeoutr::TIMEOUTRrs`, the same type — so gating is all-or-nothing per
register. We must settle on one answer.

This document is the normative account of how. The grammar itself is specified
in [`REGISTER_ACCESS_CONSTRAINTS_GRAMMAR.md`](REGISTER_ACCESS_CONSTRAINTS_GRAMMAR.md);
the workflow in [`INJECTION.md`](INJECTION.md). The implementation is
`RegisterPlan._emit_state_gate` and `resolve_instance_collisions` in
`applications/pac_codegen/rust_codegen.py`.

## The one rule

> **Rules add up. Readings of one rule compete, and the narrower one wins.**

Everything below follows from that, plus one asymmetry in why:

- **Over-gating invents a finding.** A gate the datasheet never asked for makes
  correct downstream code fail to compile, and every user pays.
- **Under-gating loses one.** A missing gate is a violation we do not catch.

They are not symmetric costs, which is why precision beats coverage at every
branch, and why genuinely contradictory evidence buys no gate at all.

## The tree

```
SEVERAL RULES FOR ONE REGISTER
│
├─ (A) all from ONE FILE
│      One file = one register on one copy of a peripheral. Nothing competes.
│      Every rule applies.
│
│      ├─ whole-register rules only
│      │     Conditions pooled into one requirement. One witness for the
│      │     register, minted only when every condition holds at once.
│      │     More rules = stricter gate, never looser.
│      │
│      ├─ field rules only
│      │     One witness per named field, carrying only that field's own
│      │     conditions. A rule naming three fields gives all three the same
│      │     conditions. A field named by two sentences collects both. A field
│      │     NEVER inherits a condition from a neighbour it was not named
│      │     alongside.
│      │
│      └─ both kinds
│            Both apply: writing a gated field needs two witnesses, the
│            register's and the field's. Correct when the rules really differ.
│
└─ (B) from SEVERAL FILES for the same register
       │
       ├─ all from the SAME copy of the peripheral
       │    (a secure alias, a naming variant: rng_htcr / rng_s_htcr)
       │    │
       │    ├─ ONE sentence at two precisions
       │    │     One file named the fields, another did not.
       │    │     NARROW WINS. The register-wide version is the coarser
       │    │     extraction of that sentence and is discarded, not merged.
       │    │     fate: same_instance_rules_unioned
       │    │
       │    └─ genuinely different sentences
       │          Different rules; they stack, as in (A).
       │          fate: same_instance_rules_unioned
       │
       └─ from DIFFERENT copies
            │
            ├─ they agree ──► keep one (the module's own copy preferred)
            │
            └─ they differ
                 │
                 ├─ ONE sentence at two precisions
                 │     NARROW WINS; named fields unioned.
                 │     fate: instance_merged_for_review
                 │
                 └─ genuinely different answers
                       NOTHING is gated, for any copy.
                       fate: instance_conflict_dropped
```

## Worked examples

**I2C_OAR2 — why narrow must win.** *"These bits can be written only when
OA2EN = 0"* scopes to the address fields, not to `OA2EN` itself. 94 of 103
extractions in the corpus resolved it correctly to `['OA2MSK','OA2']`; 9 lost
the field list. Taking a register-wide reading gates `OA2EN` on itself: set it
once and the register can never be written again, because clearing it is a
write the gate forbids. See *Same-register refusal* below.

**RNG_HTCR — narrow wins within one copy.** Three files (`rng_htcr`,
`rng_s_htcr`, `sec_rng_htcr`), one sentence, one condition pair. Only the first
named a field. Result: `HTCFG` alone carries the gate; the two register-wide
readings are dropped.

**I2C_TXDR — narrow wins across copies.** `I2C2` and `I2C3` resolved *"these
bits"* to `TXDATA`; `I2C1` said "the whole register". Result: `TXDATA`.

**CRS_CR — both kinds, correctly.** The register may not be written while `CEN`
is set; its `TRIM` field may not be written while `AUTOTRIMEN` is set. Two
different sentences, two different conditions, so both apply and writing `TRIM`
needs both witnesses.

**USART_CR2 (rm0008) — irreconcilable.** One copy reads the identical quote as
`CR1.TE cleared`, another as `CR1.UE cleared`. One is wrong and nothing
distinguishes them. Unioning would demand a precondition the manual does not;
picking one gates on a condition we have equal reason to think is wrong. Both
are dropped.

## Deduplication

Two layers, at different scopes:

| where | what | key |
|---|---|---|
| collect (`core/collect_constraints.py`) | whole constraints, before the emitter | the linted-constraint id |
| the emitter, case (A) | conditions across constraints | `(source register, field, kind, value)` |

The emitter's key is *semantic*, so the same condition phrased differently or
listed in a different order is stored once. Datasheet quotes, by contrast, are
deduplicated by **exact string**, so two extractions of one sentence differing
by a word both survive into the generated doc comment. Cosmetic — it does not
affect what is enforced — but inconsistent with `_norm_quote`, which normalises
markdown, curly quotes and articles before comparing.

## Same-register refusal

Independent of the tree, a whole-register `write`/`modify` gate whose
precondition is a field **of that same register**, restored by **software**, is
refused outright (`fate: same_register_software_gate`). It is a one-way door:
once the field leaves the required state the register can never be written
again. A hardware-restored precondition is exempt — the peripheral clears it
without our help, so the register comes back.

Two shapes produce this, and both are review outcomes rather than codegen
outcomes: an extraction that lost its field list, or a genuine lock bit, which
belongs in the `write_once` kind rather than `state_gate`.

## Known limitations

- **Ordering.** Reconciliation runs *after* the validator gate — so every
  competing plan is already judge-`enforce`, and the tie-break never chooses
  between a confirmed and an unconfirmed extraction — but *before* the
  attribution check. If the kept plan's quote fails to anchor, its gate is
  dropped and a discarded twin whose quote would have anchored is already gone.
  No case in the corpus hits this today.
- **Field-scoped read gates are not enforced.** Field gating works by adding a
  witness parameter to the *writer* accessor; a read has no writer to gate. The
  emitter warns and skips.
- **Quote-identity is textual.** `_quotes_are_one_sentence` tests containment
  of the shortest normalised quote in every other. It tolerates different
  windows around a sentence, and (since articles are normalised away) small
  function-word differences inside one — but two paraphrases of one rule still
  read as two rules.
