# Validator — paper paragraph drafts

Draft prose for the paper. Notation is consistent across all four: V = validator
judgment, c = confidence, s = pseudo-score, C = ground-truth correctness, α/β =
sensitivity/specificity, π = prevalence, r̂ = observed positive (acceptance) rate.

---

## 1. Verified datasheets

A *verified datasheet* is a human-curated, ground-truth slice of a device's
register-layout specification. We record each one as a single tall CSV in which each row
captures one invariant *cell* and keys it by the device's SVD coordinates
`(peripheral, register, field, key)`. We restrict the scope to six layout keys—
`address_offset`, `reset_value`, and `size` at the register level, and `bit_offset`,
`bit_width`, and `access` at the field level—and we store, alongside the SVD-asserted
value, the human-confirmed datasheet value (`correct_value`), a `status` label that gates
trustworthiness (`verified`, `not-specified`, `datasheet-ambiguous`, or pending), and
provenance metadata (`set_method`: human-confirmed, overridden, or transcribed blind)
that lets us weight rows by how much we can trust them. To avoid circular ground truth—
where the system under test contaminates the reference that measures it—we hide the
generator's value from the annotator entirely; we may show the SVD value as a
confirmation default for speed, but we annotate a sampled subset fully un-anchored,
transcribing it directly from the datasheet page. We annotate SVD-inherited peripherals
(`derivedFrom`) once on their prototype, but we **materialize** them for evaluation—
copying the prototype's register/field layout under every derived peripheral (keeping its
own base address)—so the benchmark covers every peripheral instance the generator actually
extracts. This matters because the generator processes each peripheral as a separate task
(it is prompted for `GPIOA`, `GPIOB`, … independently, with its own name, base address,
and retrieved context), so the validator must independently confirm each in production;
the expanded benchmark therefore matches the real workload rather than only the compact
prototypes. We admit only `status = verified` rows into the evaluation.

Because every verified row records a *true* fact, we synthesize the negative class the
benchmark needs by injecting controlled noise: we corrupt a fixed fraction (30%) of the
verified invariants—**stratified by peripheral** so the negative class spans every
peripheral proportionally rather than clustering in a few from a global uniform draw—
replacing each chosen value in place rather than adding a parallel wrong copy, so that no
invariant appears as both a true and a false instance and the validator cannot exploit a
matched pair. We make the noise *realistic* and *type-aware*
rather than uniformly random, drawing on per-register context so that each false fact
stays plausible: we perturb a `bit_offset` or `bit_width` to another value within the
register's actual bit range, flip a nibble of or step to a neighbour of a hexadecimal
`address_offset` or `reset_value` while preserving its `0x` width, swap a `size` for
another common width in {8, 16, 32, 64}, exchange an `access` code for a different valid
encoding, and replace a `field_name` with a real sibling field from the same register or
a single-edit typo. We deliberately avoid naive noise—an out-of-range bit width, a
gibberish name—because the validator rejects it trivially and it would inflate the
measured specificity; plausible, in-distribution corruptions instead produce a harder
negative class that better reflects the generator errors the validator must actually
catch. We guarantee that every corruption differs from its original and leave the
remaining invariants as verified positives, yielding a fully labeled benchmark of true
and false facts from which we measure the validator's error rates and set the precision
target it must clear before we trust its judgments on unverified devices.

## 2. Tuning the validator

The validator is an LLM that reads an invariant together with datasheet context
retrieved for its register and emits a binary judgment V ∈ {0,1} ("matches the
datasheet") and a self-reported confidence c ∈ [0,1]; we collapse these into a single
pseudo-score s = c if V=1 else 1−c, which we read as the validator's estimated
probability that the invariant is correct. To tune and evaluate it without contamination,
we draw on the labeled benchmark of Section 1—the expanded set of verified positives plus
the peripheral-stratified corruptions—and we partition it into k=5 folds at the
*(peripheral, register)* granularity so that correlated invariants from one register
never straddle the train/test split. We tune two levers, and we fit both on the training
folds alone. First, we **mine in-context examples**: for each held-out fold we collect
the validator's mistakes on the remaining folds—false positives (accepted corruptions)
and false negatives (rejected correct invariants)—and we append a balanced sample of
them, with their verified labels, as few-shot exemplars to the system prompt, teaching
the model the corner cases it gets wrong. Second, we **select the threshold**: we pick
the decision threshold τ on the pseudo-score that, on the training folds, gives the
lowest cutoff whose precision meets a target (95%), which maximizes recall subject to
that precision constraint. Both levers are applied in a single round: we mine the
exemplars once and choose τ with one exhaustive sweep of the training scores—which
already explores the entire precision–recall curve—so there is no iterative threshold
search. We then judge each held-out fold with its mined exemplars, score it at its
trained τ, and rotate over all folds.

## 3. Reported metrics

Aggregating the held-out confusion matrices across folds gives us an unbiased estimate of
the validator as a noisy binary labeler, which we characterize by its **sensitivity**
α = P(V=1 | C=1) and **specificity** β = P(V=0 | C=0); we require α+β > 1 (better than
chance) so that the labeler stays identifiable for the calibration in Section 4. Because
we use the validator as a precision filter feeding human review rather than as an
auto-classifier, we lead with two numbers: the **gate precision** P(C=1 | V=1)—the
fraction of accepted invariants that are genuinely correct, i.e. how clean the pile a
reviewer sees is—and the **yield** (recall) α, the fraction of correct invariants the
gate keeps. We report yield alongside precision because we discard rejected invariants
unreviewed, so every false negative is a permanently lost candidate. Because we *select*
τ to meet the 95% target on the training folds but *measure* precision on the held-out
folds, the reported gate precision is an out-of-sample estimate—the precision we actually
achieved, which may land slightly above or below the target—and we report it (with its
yield) rather than assuming the target was met. We additionally
characterize the *ranking* quality of the confidence score with a precision@k curve over
the accepted set (what fraction of the top-k ranked candidates are real) and a
reliability diagram that compares mean confidence to empirical precision per bin, which
tells us whether we can read the confidence as a probability for prioritization. Together
these capture the three operational properties we care about: how clean the accepted pile
is (gate precision), how many real cases survive (yield), and whether the score orders
them usefully (ranking and calibration).

## 4. The validator in practice

On an *unverified* device, the generator extracts a set of register-layout facts—one
claimed value per `(peripheral, register, field, key)` cell—and the validator examines
each fact in turn, judging whether the datasheet supports it. The validator never
compares the generator against the SVD; it checks each generated fact for truth against
the datasheet directly, and so acts as a precision filter over the generator's own
output. We gate each fact at the frozen per-vendor threshold τ: we keep the facts the
validator judges true with confidence s ≥ τ, drop the rest unseen, and rank the survivors
by confidence. Because we calibrated τ to a 95% precision target, we expect the retained
facts to hold that cleanliness, so a human—who always reviews before we file a patch—
works the ranked queue top-down, spends scarce review effort on the highest-probability
facts first, and stops when the labor budget runs out; the facts that survive review are
the trustworthy datasheet values we then act on (for example, to correct an SVD or PAC
where they disagree). The benchmark-measured error rates also let us make a quantitative
claim about a device we never annotated: we observe the validator's raw acceptance rate r̂
over the generated facts and apply the Rogan–Gladen correction
π̂ = (r̂ − (1−β)) / (α + β − 1), which recovers an estimate of π, the true fraction of
generated facts that are correct—that is, the generator's extraction accuracy on this
device—net of the validator's own false-positive and false-negative behavior. We stress
that π is a **count, not a selector**: it estimates how many of the generated facts are
correct (≈ πN), not which ones, and reviewing "the top π fraction" recovers them only
under a perfect ranking; the precision@k curve, not π, governs what a given review depth
actually catches. This calibration assumes that α and β, which we estimate on a vendor's
verified devices, transfer to its unverified ones—the per-vendor amortization that lets a
fixed annotation cost (≈two devices per vendor) underwrite validation across the rest—and
it gives us an immediate internal estimate of extraction accuracy while the external
ground truth, upstream merge acceptance, accrues slowly.

## 5. When the target precision is unmet

The 95% figure is a target we enforce during threshold selection, not a guarantee, and
two cases arise. If the target is reachable but only at a stricter threshold, the sweep
simply returns that higher τ and we pay for the cleaner pile in lower yield—more correct
facts fall below the line and are dropped unseen. If no threshold reaches the target—the
validator's precision ceiling on a vendor sits below 95%—we fall back to the
highest-precision operating point available and report the shortfall; further
thresholding cannot help, because the entire precision–recall curve sits too low.
Recovering then means *lifting* the curve rather than sliding along it: better in-context
exemplars, improved retrieval, name- and notation-aliasing, or a stronger model—not more
tuning iterations, since one sweep already finds the best threshold. Operationally, the
shortfall is not catastrophic: because a human reviews every candidate before we file, a
sub-target validator never ships a bad patch—it only spends more reviewer time per real
defect—so when the curve cannot be lifted enough we have three graceful options. We can
lower the precision bar for that vendor when review is cheap; we can gate the vendor to
fully manual review, treating the measured precision as the go/no-go signal for
automation; or we can apply per-class gates, auto-filing the keys the validator handles
reliably (e.g. `address_offset`, `reset_value`) while routing the weaker ones (e.g.
`access`, field-level) to human review.

## 6. Results (to report)

> Numbers below are placeholders `[··]` pending the runs in
> `optimization_validator/README.md` § EXPERIMENTS (A–E). Each is labeled with the
> experiment that produces it.

We report, for one representative device per vendor after a single tuning round, the
validator's operating point both as a noisy labeler and as a precision filter. **(A1)** On
the STM slice (`rm0041`, k = 5 folds, `[N_stm]` invariants, 30% peripheral-stratified
corruption) the tuned validator reaches a gate precision of `[P_stm]`% at a yield (recall)
of `[Y_stm]`%, with sensitivity α = `[α_stm]` and specificity β = `[β_stm]`; on the NXP
slice (`ke04`, `[N_nxp]` invariants) it reaches `[P_nxp]`% precision at `[Y_nxp]`% yield
(α = `[α_nxp]`, β = `[β_nxp]`). **(B1)** The single round of in-context example mining
moves the held-out operating point from `[base_metric]` to `[tuned_metric]` (Δ =
`[+Δ_tune]`), and **(B2–B4)** the name-aliasing and access-notation handling each raise
yield by `[+Δ_alt]` / `[+Δ_legend]` at a specificity cost of `[−Δ_alt]` / `[−Δ_legend]`,
while OpenEvolve retrieval improves precision over file-search by `[+Δ_retr]`; **(B5)** the
gain from added exemplars saturates at `[k_ex]` per class, after which prompt growth buys
nothing. **(E1)** Broken down by invariant class, precision is highest on register-level
keys (`address_offset`, `reset_value`: `[P_addr]`%) and lowest on `[weak_key]`
(`[P_weak]`%), which is what motivates per-class gating. **(A1, ranking)** Reviewing the
top `[k_pct]`% of the confidence-ranked queue recovers `[recall_at_k]`% of the true facts
(precision@`[k_pct]`% = `[prec_at_k]`%), so a reviewer reaches most defects from a small
fraction of the queue. **(C1)** Crucially, applying the α, β measured at 30% corruption to
a held-out slice corrupted at 50%, the Rogan–Gladen estimate recovers π̂ = `[pi_hat]`
against a true prevalence of 0.50 (error `[±pi_err]`), showing the correction works across
prevalences rather than reducing to an identity. **(C2)** Freezing the per-vendor–
calibrated validator and applying it unchanged to a second device of the same vendor
(STM `rm0041`→`rm0090`, NXP `ke04`→`s32k116`) holds gate precision at `[P_transfer_stm]`%
and `[P_transfer_nxp]`% respectively—within `[Δ_transfer]` of the in-vendor figure—
supporting the claim that a single per-vendor calibration transfers across that vendor's
devices and amortizes the annotation cost. **(A2)** Across `[models]` the tuned gate
precision spans `[P_lo]`–`[P_hi]`% at comparable yield, with `[best_model]` strongest, and
**(E2)** all figures are reported as means over `[n_seeds]` corruption seeds with 95%
intervals of `[±ci]`. **(D1)** Finally, of the `[N_filed]` STM corrections filed from
validator-confirmed facts, `[N_merged]` have been accepted upstream to date, linking the
internal precision estimate to the external ground truth.
