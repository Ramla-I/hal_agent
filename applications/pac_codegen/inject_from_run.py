#!/usr/bin/env python3
"""Close the loop: a generator RUN DIRECTORY in, an updated PAC out.

This is the end-to-end driver the pipeline stages plug into::

    generator run dir --> collect (lift + lint) --> select --> inject PAC

It runs collection (grammar-v2 lift plus the stage-0 lint) over the run
directory, then keeps only the constraints that BOTH survived collection AND
are compilable by the current emitter (state gates over observed hardware
state; sequences/action witnesses arrive with later roadmap steps), builds
one plan per register, and injects them all into the PAC in a single shot.

Drops are reported rather than silent: each is a fate row (injected /
rejected-at-collection / unsupported-by-emitter / peripheral-not-in-device)
with its reason, joinable to the durable artifact by constraint id.

Usage:
    python applications/pac_codegen/inject_from_run.py \
        /path/to/agent_output/stm/rm0008/1 \
        --pac applications/pac_codegen/vendored/pac/stm32f1 \
        --device stm32f103 [--svd-dir <svd>] [--dry-run] \
        [--report out/report.json]

--dry-run performs everything except writing to the PAC (selection and plan
construction still run, so the report is produced either way).
"""

import argparse
import json
import sys
import tempfile
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_DIR.parent.parent))
sys.path.insert(0, str(APP_DIR))

from defs import RegisterInfo  # noqa: E402
from core import collect_constraints  # noqa: E402
from core.constraint_pipeline import new_constraint_id  # noqa: E402
import rust_codegen  # noqa: E402


def _load_gate_map(path: Path, rm: str) -> dict:
    """id -> effective codegen gate from a chained ``validated.jsonl`` or a
    human-labelled ``*_constraints_review.jsonl``. The judge decision
    (``enforcement`` = enforce|doc_only|drop) is overridden by the reviewer's
    ``tp_fp``: ``FP`` forces drop; ``TP`` rescues a dropped row to doc_only.
    Only ``enforce`` reaches the emitter as a compile-time gate."""
    gate: dict = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        enf = r.get("enforcement", "")
        tp = r.get("tp_fp", "")
        if tp == "FP":
            enf = "drop"
        elif tp == "TP" and enf == "drop":
            enf = "doc_only"
        gate[r["id"]] = enf
    return gate


def _kind_counts(gates) -> dict:
    """grammar-v2 kind -> how many of these constraints, for report accounting."""
    out: dict = {}
    for g in gates:
        k = g.get("kind", "")
        out[k] = out.get(k, 0) + 1
    return out


def select_and_plan(collect_dir: Path, device_dir: Path,
                    field_level_gating: bool = True,
                    disabled_kinds=None, gate_map=None, rm: str = "") -> tuple[list, list[dict]]:
    """From a collection output dir, build injectable RegisterPlans.

    Returns (plans, report_rows). Selection is manifest-driven: only
    constraints collection accepted are considered; each register's accepted
    subset is then offered to the emitter, which may still refuse shapes it
    does not support yet — refusals become report rows, never crashes.

    ``field_level_gating`` is the default: field-scoped constraints are enforced
    at field granularity. Pass False (the CLI ``--register-only`` baseline) to
    gate whole registers only and skip field-scoped constraints.

    ``gate_map`` (opt-in, from ``--constraints``) keys the constraint validator's
    codegen decision by the linted-constraint id: only ``enforce`` constraints
    are emitted as compile-time gates; ``doc_only`` / ``drop`` / unknown are
    excluded and reported. Without it, no validator gating is applied.
    """
    manifest = json.loads((collect_dir / "manifest.json").read_text())
    plans, rows = [], []
    # instance -> register-block module (I2C2 lives in i2c1.rs; see
    # rust_codegen.peripheral_instance_map). Without it, every constraint on a
    # non-first instance is thrown away as "peripheral not in device".
    instance_map = rust_codegen.peripheral_instance_map(device_dir)
    # stm32h7 keeps peripherals in a shared src/common/ tree; DeviceLayout
    # resolves either layout (see rust_codegen.DeviceLayout).
    layout = rust_codegen.DeviceLayout(device_dir)

    for reg_entry in manifest["registers"]:
        peripheral = reg_entry["peripheral"]
        source = reg_entry["file"]
        # Every constraint this register carries, by the same id the validator
        # ledger and the saved artifact use. Filled once the collected file is
        # read below (the manifest holds lint REPORTS, not the constraints);
        # rows written before that -- a file that failed to load at all --
        # legitimately have none. A row concerning a subset passes its own.
        all_ids: list = []
        def row(fate: str, reason: str, indices=None, ids=None, **extra):
            # `kind`/`kinds` carry the grammar-v2 kind(s) STRUCTURALLY, so
            # accounting never has to parse the human-readable reason string.
            #
            # `constraint_ids` is what makes this row joinable to the durable
            # artifact. Without it the only way to ask "why did THIS register
            # lose its gate" is to match names, and the two files do not agree
            # on any of them: the artifact records the Rust MODULE (usart1) and
            # the prefix-stripped register (CR1), while a row records the
            # SOURCE INSTANCE (uart4) and the run-file name (cr1_disabled). One
            # constraint, four different strings, and a join that misses looks
            # exactly like a register that lost its gate for no reason.
            r = {
                "file": source, "peripheral": peripheral,
                "register": reg_entry["register"], "fate": fate,
                "reason": reason,
                "constraints": indices if indices is not None else [],
                "constraint_ids": sorted(ids) if ids else all_ids,
            }
            r.update(extra)
            rows.append(r)

        for c in reg_entry["constraints"]:
            reasons = sorted({r["reason"] for r in c.get("rejects", [])})
            if reasons:
                # `kinds` is [] when the constraint failed grammar validation
                # outright -- there is no parsed kind to report. The tracking
                # table recovers it from the raw generator output by index.
                row("rejected_at_collection", ";".join(reasons),
                    [c.get("v2_index", c.get("v1_index"))],
                    kind=(c.get("kinds") or [""])[0])

        # Collection already emits ONLY the accepted, linted grammar-v2 gates in
        # access_constraints_v2 (rejects/duplicates are not appended), so
        # acceptance is simply "present here". The emitter enforces state gates;
        # `enforceability` is a collection annotation, not a grammar field.
        out_file = collect_dir / Path(reg_entry["output_path"]).name
        try:
            data = json.loads(out_file.read_text())
        except (OSError, ValueError) as e:
            # One unreadable collected file must not abort the whole run: report
            # it as its own fate and move on. all_ids is still empty here, so
            # this row legitimately carries no ids.
            row("read_error", f"could not read {out_file.name}: {e}")
            continue
        all_v2 = data.get("access_constraints_v2") or []
        all_ids[:] = sorted({
            new_constraint_id(rm, peripheral, reg_entry["register"], g)
            for g in all_v2 if isinstance(g, dict)})
        # Offer only kinds the emitter supports and are not disabled; skipped
        # kinds become report rows (never crashes). Single source of truth:
        # rust_codegen.enabled_kinds.
        enabled = rust_codegen.enabled_kinds(disabled_kinds)
        gates = [g for g in all_v2 if g.get("kind") in enabled]
        for g in all_v2:
            if g.get("kind") not in enabled:
                why = ("no codegen emitter yet"
                       if g.get("kind") not in rust_codegen.SUPPORTED_KINDS
                       else "codegen disabled for this kind")
                row("kind_not_emitted", f"{g.get('kind')}: {why}",
                    ids=[new_constraint_id(rm, peripheral, reg_entry["register"], g)],
                    kind=g.get("kind", ""))

        # Constraint-validator gate (opt-in): keep only constraints the judge
        # confirmed AND that are witness-enforceable (enforcement == "enforce"),
        # honouring any human tp_fp override. doc_only/drop are documented, not
        # compile-enforced.
        if gate_map is not None:
            kept = []
            for g in gates:
                cid = new_constraint_id(rm, peripheral, reg_entry["register"], g)
                decision = gate_map.get(cid)
                if decision == "enforce":
                    kept.append(g)
                else:
                    row("gated_out_by_validator",
                        f"{g.get('kind')}: {decision or 'not_in_validated'}",
                        ids=[cid],
                        kind=g.get("kind", ""), decision=decision or "not_in_validated")
            gates = kept
        for g in gates:
            g.pop("enforceability", None)
        if not gates:
            continue
        # Resolve the instance to the module that owns its register types.
        module = peripheral
        if not layout.module_file(module).is_file():
            aliased = instance_map.get(peripheral)
            if aliased and layout.module_file(aliased).is_file():
                module = aliased
            else:
                row("peripheral_not_in_device",
                    f"{peripheral}.rs absent from {device_dir.name}"
                    + ("" if not instance_map else
                       " (and no register-block alias for it)"),
                    kinds=_kind_counts(gates))
                continue

        # Rebuild a RegisterInfo holding ONLY the accepted state gates and offer
        # it to the emitter.
        data["access_constraints_v2"] = gates
        data.pop("constraint_reports", None)
        try:
            plan = rust_codegen.RegisterPlan(
                RegisterInfo(**data), module,
                field_level_gating=field_level_gating,
                disabled_kinds=disabled_kinds)
            plan.source_instance = peripheral
            # The review-ledger ids of the constraints that survived to become
            # this plan. Without them the durable artifact says WHAT a crate
            # gates but not WHICH ledger rows produced it, so a reviewer going
            # the other way -- "these gates are wrong, mark them FP" -- has to
            # join on (peripheral, register) and guess among a register's
            # several constraints.
            plan.constraint_ids = [
                new_constraint_id(rm, peripheral, reg_entry["register"], g)
                for g in gates]
        except rust_codegen.UnsatisfiableGate as e:
            # Not a codegen gap: a gate that could never pass, withdrawn.
            # (Subclasses ValueError -- catch before the generic handler.)
            row("unsatisfiable_gate", str(e), kinds=_kind_counts(gates))
            continue
        except rust_codegen.SameRegisterSoftwareGate as e:
            # A refusal on safety grounds, not a codegen gap: kept as its own
            # fate so the count is visible rather than buried in
            # emitter_rejected. (Subclasses ValueError -- catch before the
            # generic handler.)
            row("same_register_software_gate", str(e),
                kinds=_kind_counts(gates))
            continue
        except rust_codegen.FieldGatingDisabled as e:
            # A switched-off feature, not a codegen gap -- kept separate so the
            # emitter's real limits are readable. (Subclasses ValueError, so it
            # must be caught before the generic handler below.)
            row("field_gating_disabled", str(e), kinds=_kind_counts(gates))
            continue
        except NotImplementedError as e:
            row("unsupported_by_emitter", str(e), kinds=_kind_counts(gates))
            continue
        except ValueError as e:
            row("emitter_rejected", str(e), kinds=_kind_counts(gates))
            continue
        plans.append(plan)
        # Record enforcement granularity: whole-register gated ops and, when
        # field-level gating is on, the per-field gates (enforced_as: field).
        detail = f"gates: {sorted(op for _, _, op in plan.gated_ops())}"
        if plan.field_gates:
            detail += f"; field_gates: {sorted(plan.field_gates)}"
        if module != peripheral:
            detail += (f"; via instance alias {peripheral} -> {module} "
                       "(gates every instance of this block)")
        row("planned", detail, kinds=_kind_counts(gates),
            via_alias=(module != peripheral))

    return plans, rows


def device_constraints_file(device, run_dir, svd_dir, chunks,
                            field_level_gating, plans, quote_tiers) -> dict:
    """The durable per-device record: exactly what this device's crate gates.

    Its own function so the shape can be asserted on without a run directory,
    a PAC and a toolchain. The field-gate section below was silently absent
    until a field-mode file was read closely, precisely because nothing could
    reach this code to test it.
    """
    return {
        "device": device,
        "source_run": run_dir,
        "svd_dir": svd_dir,
        "note": "constraints this device's crate enforces, post "
                "collection-lint, emitter selection, access-mode pruning, "
                "and (with --attribution-check) quote anchoring plus target "
                "attribution; regenerate with "
                "inject_from_run.py. Whole-register gates are in "
                "`gated_operations`/`preconditions`; field-scoped ones are "
                "in `gated_fields` and gate a single writer accessor, "
                "leaving sibling fields untouched",
        "attribution_checked_against": chunks or None,
        # Which gating mode produced this set. The two modes plan DIFFERENT
        # gates, and without this the file cannot be told apart from the
        # other mode's after the fact.
        "field_level_gating": bool(field_level_gating),
        "registers": [
            {
                "peripheral": p.peripheral,
                "register": p.reg_name,
                # Operations reachable with a witness.
                "gated_operations": sorted(p.preconditions),
                "preconditions": {
                    op: [pre.describe() for pre in pres]
                    for op, pres in p.preconditions.items()},
                "datasheet_text": p.docs,
                # Review-ledger ids: `tp_fp = FP` on any of these removes this
                # register's gate on the next injection.
                "constraint_ids": sorted(getattr(p, "constraint_ids", []) or []),
                # Field gates live in their own structure: they gate
                # `w.<field>()`, not the register's write/modify, so folding
                # them into gated_operations would claim the whole register
                # is constrained. Omitting them made a field-mode file list a
                # register with an EMPTY gate list -- present, unexplained.
                "gated_fields": {
                    fg.field: {
                        # One accessor serves both surfaces, so a field gate
                        # always covers write and modify.
                        "operations": ["write", "modify"],
                        "preconditions": [pre.describe()
                                          for pre in fg.preconditions],
                        "datasheet_text": fg.docs,
                    }
                    for _, fg in sorted(p.field_gates.items())
                },
                "quote_verification": quote_tiers.get(
                    (p.peripheral, p.reg_name)),
            }
            for p in plans
        ],
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run_dir", help="generator run directory (one file per register)")
    ap.add_argument("--pac", required=True, help="PAC crate root to inject into")
    ap.add_argument("--device", required=True, help="device module, e.g. stm32f103")
    ap.add_argument("--svd-dir", default=None,
                    help="SVD file/dir for collection's name+width lint")
    ap.add_argument("--attribution-check", "--verify-evidence", "--chunks",
                    dest="attribution_check",
                    default=None, metavar="DIR",
                    help="chunked-datasheet root (e.g. "
                         ".../chunked_datasheets/stm). Verify that each kept "
                         "constraint's supporting quote (a) exists in the "
                         "manual and (b) actually attributes to the register "
                         "the constraint claims. Failing either drops the "
                         "gate (plan §7.1: no unverifiable evidence reaches a "
                         "crate). (b) is the check that earns its keep: "
                         "datasheets say \"this bit\" far more often than "
                         "they name the register, so a quote that names no "
                         "register AND anchors outside the target's section "
                         "supports the claim neither textually nor "
                         "positionally. (a) is usually already enforced by "
                         "--constraints, whose judge never confirms an "
                         "unanchorable quote. --verify-evidence and "
                         "--chunks are the old names.")
    ap.add_argument("--constraints", "--validated", dest="constraints",
                    default=None, metavar="PATH",
                    help="chained validated.jsonl (or a *_constraints_review.jsonl): "
                         "gate codegen on the constraint validator — only "
                         "judge-confirmed, witness-enforceable constraints "
                         "(enforcement=='enforce', honouring human tp_fp) are "
                         "emitted as compile-time gates; doc_only/drop are excluded "
                         "and reported. Without it, no validator gating is applied.")
    ap.add_argument("--report", default=None, help="write the JSON report here")
    ap.add_argument("--save-constraints", default=None, metavar="PATH",
                    help="write the per-DEVICE constraints file (the durable, "
                         "reviewable artifact: exactly what this device's "
                         "crate enforces, plus provenance). Convention: "
                         "applications/pac_codegen/constraints/"
                         "<rm>_<device>.json -- keyed by MANUAL and device, "
                         "because two manuals can project onto the same "
                         "family and one manual onto two devices")
    ap.add_argument("--dry-run", action="store_true",
                    help="select and plan, but do not touch the PAC")
    ap.add_argument("--register-only", action="store_true",
                    help="BASELINE MODE: gate whole registers only, skipping "
                         "every field-scoped constraint. This was the default "
                         "until field gating was shown to recover 602 "
                         "registers and 1068 obligations the policy discarded; "
                         "it is kept because every previously published number "
                         "was measured this way and the comparison should be "
                         "runnable, not asserted.")
    ap.add_argument("--field-level-gating", action="store_true",
                    help=argparse.SUPPRESS)   # now the default; accepted as a no-op
    ap.add_argument("--disable-kind", action="append", default=[],
                    metavar="KIND",
                    help="disable codegen for a grammar-v2 kind (repeatable); "
                         "its constraints are skipped and reported, not "
                         "emitted. Default: all supported kinds enabled.")
    args = ap.parse_args()

    pac_root = Path(args.pac)
    device_dir = pac_root / "src" / args.device
    if not device_dir.is_dir():
        sys.exit(f"device module not found: {device_dir}")

    with tempfile.TemporaryDirectory() as td:
        collect_dir = Path(td) / "collected"
        argv = [args.run_dir, "--output-dir", str(collect_dir)]
        if args.svd_dir:
            argv += ["--svd-dir", args.svd_dir]
        collect_constraints.main(argv)

        rm = Path(args.run_dir.rstrip("/")).parent.name
        gate_map = _load_gate_map(Path(args.constraints), rm) if args.constraints else None
        plans, rows = select_and_plan(
            collect_dir, device_dir,
            field_level_gating=(not args.register_only),
            disabled_kinds=set(args.disable_kind),
            gate_map=gate_map, rm=rm)

        # Match the artifact and injection exactly: apply the device-level
        # prune (access mode + field-reader shape) BEFORE saving; injection
        # re-runs it idempotently. Registers it empties out were reported as
        # `planned` a moment ago, so correct their fate — a report that still
        # calls them planned would overstate what the crate enforces.
        # (manifest register names are lowercase; plan.reg_lower is the same
        # name with any peripheral prefix stripped — key on that, and simply
        # skip any row that does not resolve rather than mislabel it.)
        # Instances share register types, so two plans can now target one
        # Rust type; emitting both would define the same witness twice.
        # Ids for the post-loop rows below. They are appended outside the
        # per-register loop, so they never pass through row() and would carry
        # none -- and these are precisely the rows that explain why a register
        # lost its gate, so a name-based join was the only way to read them.
        ids_by_reg: dict = {}
        for _p in plans:
            ids_by_reg.setdefault((_p.peripheral, _p.reg_lower), set()).update(
                getattr(_p, "constraint_ids", ()) or ())

        def _ids(module, register):
            return sorted(ids_by_reg.get((module, str(register).lower()), ()))

        plans, collisions, merges = rust_codegen.resolve_instance_collisions(plans)
        for m in merges:
            # Two different events, so two fates. A reviewer filtering for
            # "instances disagreed and we picked" must not also get "one
            # instance stated two rules and they stack" -- nothing competed in
            # the second, and it needs no adjudication.
            if m.get("kind") == "same_instance_union":
                rows.append({
                    "file": "", "peripheral": m["module"],
                    "register": m["register"],
                    "fate": "same_instance_rules_unioned",
                "constraint_ids": _ids(m["module"], m["register"]),
                    "reason": f"{m['resolution']}: {m['detail']} "
                              f"(gate sets {m['field_sets']})",
                    "constraints": [],
                })
                continue
            rows.append({
                "file": "", "peripheral": m["module"], "register": m["register"],
                "fate": "instance_merged_for_review",
                "constraint_ids": _ids(m["module"], m["register"]),
                "reason": f"instances {m['instances']} named different fields "
                          f"{m['field_sets']} for the same rule — "
                          f"{m['resolution']}; {m['detail']}",
                "constraints": [],
            })
            print(f"  note: {m['module']}/{m['register']}: instances "
                  f"{m['instances']} named different fields {m['field_sets']} "
                  f"— {m['resolution']}, FLAGGED FOR REVIEW")
        for c in collisions:
            rows.append({
                "file": "", "peripheral": c["module"], "register": c["register"],
                "fate": "instance_conflict",
                "constraint_ids": _ids(c["module"], c["register"]),
                "reason": f"instances {c['instances']} disagree — {c['detail']}",
                # what each instance claimed, so the row is reviewable
                "readings": c.get("readings", []),
                "same_datasheet_text": c.get("same_datasheet_text"),
                "constraints": [],
            })
            print(f"  note: {c['module']}/{c['register']}: instances "
                  f"{c['instances']} disagree — gate dropped entirely")
            # EVERY contributing instance loses its gate, not just the losers:
            # contradictory readings of one datasheet sentence buy no
            # compile-time obligation. Agreeing instances need no correction —
            # their rule IS enforced, by the very same Rust type.
            for r in rows:
                if (r["fate"] == "planned"
                        and r["register"].lower() == c["register"]
                        and r["peripheral"] in c["instances"]):
                    r["fate"] = "instance_conflict_dropped"
                    r["reason"] = (
                        f"{c['module']}/{c['register']}: instances "
                        f"{c['instances']} disagree on the gate; dropped "
                        "rather than unioned or arbitrarily picked")

        # A plan's gates are register-level ops AND field gates. Counting only
        # gated_ops() made every FIELD-ONLY plan look pruned: its register-op
        # list is empty before and after, and `if not kept` is true for an
        # empty list. That mislabelled 513 of 891 rows -- registers that are
        # gated in the finished crate, reported as dropped.
        def sig(p):
            return (sorted(op for _, _, op in p.gated_ops()),
                    sorted(p.field_gates))

        before = {(p.peripheral, p.reg_lower): sig(p) for p in plans}
        # prune_plans_for_device computes a reason per dropped gate
        # (`field:TRIM [...]`); keep them instead of a generic sentence.
        why = {}
        plans = rust_codegen.prune_plans_for_device(device_dir, plans,
                                                    reasons=why)
        after = {(p.peripheral, p.reg_lower): sig(p) for p in plans}
        for r in rows:
            if r["fate"] != "planned":
                continue
            key = (r["peripheral"], r["register"].lower())
            if key not in before:
                continue
            kept = after.get(key)
            had = before[key][0] or before[key][1]
            has = bool(kept and (kept[0] or kept[1]))
            detail = "; ".join(why.get(key, [])) or (
                "access mode or field reader shape")
            if had and not has:
                r["fate"] = "pruned_for_device"
                r["reason"] = (f"all gates dropped, not expressible against "
                               f"the generated PAC: {detail}")
            elif kept and kept != before[key]:
                lost_ops = sorted(set(before[key][0]) - set(kept[0]))
                lost_f = sorted(set(before[key][1]) - set(kept[1]))
                bits = ([f"ops {lost_ops}"] if lost_ops else []) + \
                       ([f"fields {lost_f}"] if lost_f else [])
                if bits:
                    r["reason"] = (f"kept ops {kept[0]} fields {kept[1]}; "
                                   f"dropped {' and '.join(bits)} at the "
                                   f"device: {detail}")

        quote_tiers = {}
        if args.attribution_check:
            from core import quote_anchor as qa
            matcher = qa.RMMatcher(
                rm, str(Path(args.attribution_check) / rm / "chunks" / "md"))
            before_qa = {(p.peripheral, p.reg_lower): sig(p) for p in plans}
            kept_plans = []
            for plan in plans:
                tiers = {}
                for op in list(plan.preconditions):
                    op_tiers = []
                    drop_reason = None
                    for quote in plan.docs.get(op, []):
                        rec = qa.anchor_row(matcher, {
                            "datasheet_text": quote,
                            "register": plan.reg_name,
                            "peripheral": plan.peripheral,
                        })
                        op_tiers.append(rec["tier"])
                        if rec["tier"] == "unanchored":
                            drop_reason = ("quote_unanchored",
                                           "supporting quote not found in the "
                                           f"{rm} datasheet markdown")
                        elif (rec.get("self_referential")
                              and not rec.get("target_located")):
                            # The quote never names the register ("This
                            # register ...") AND the page it lives on is not
                            # the target's section — the target cannot be
                            # verified textually OR positionally.
                            drop_reason = ("target_unverified_by_location",
                                           "self-referential quote anchored "
                                           "outside the target register's "
                                           "section")
                    tiers[op] = op_tiers
                    if drop_reason:
                        fate, why = drop_reason
                        del plan.preconditions[op]
                        plan.docs.pop(op, None)
                        rows.append({
                            "file": "", "peripheral": plan.peripheral,
                            "register": plan.reg_name,
                            "fate": fate,
                            "reason": f"{op}: {why}",
                            "constraints": [],
                            "constraint_ids": sorted(
                                getattr(plan, "constraint_ids", ()) or ()),
                        })
                        print(f"  note: {plan.peripheral}/{plan.reg_name}: "
                              f"dropped {op} gate — {fate}")
                # Field gates live in plan.field_gates, not plan.preconditions,
                # and their quotes need the same check: a field-scoped
                # constraint is evidence about a register just as much as a
                # register-scoped one. Until this ran, a plan whose gates were
                # ALL field-scoped had empty preconditions and was dropped by
                # the test below -- silently, with no fate row -- so enabling
                # the attribution check disabled field-level gating entirely.
                for fname in list(plan.field_gates):
                    fg = plan.field_gates[fname]
                    ftiers, drop = [], None
                    for quote in fg.docs:
                        rec = qa.anchor_row(matcher, {
                            "datasheet_text": quote,
                            "register": plan.reg_name,
                            "peripheral": plan.peripheral,
                        })
                        ftiers.append(rec["tier"])
                        if rec["tier"] == "unanchored":
                            drop = ("quote_unanchored",
                                    "supporting quote not found in the "
                                    f"{rm} datasheet markdown")
                        elif (rec.get("self_referential")
                              and not rec.get("target_located")):
                            drop = ("target_unverified_by_location",
                                    "self-referential quote anchored outside "
                                    "the target register's section")
                    tiers[f"field:{fg.field}"] = ftiers
                    if drop:
                        fate, why = drop
                        del plan.field_gates[fname]
                        rows.append({
                            "file": "", "peripheral": plan.peripheral,
                            "register": plan.reg_name,
                            "fate": fate,
                            "reason": f"field {fg.field}: {why}",
                            "constraints": [],
                            "constraint_ids": sorted(
                                getattr(plan, "constraint_ids", ()) or ()),
                        })
                        print(f"  note: {plan.peripheral}/{plan.reg_name}: "
                              f"dropped field gate on {fg.field} — {fate}")
                quote_tiers[(plan.peripheral, plan.reg_name)] = tiers
                if plan.preconditions or plan.field_gates:
                    kept_plans.append(plan)
            plans = kept_plans
            # Revise the `planned` rows the attribution check emptied or
            # narrowed -- the same correction the device prune does above -- so
            # the report (and the tracking table that reads its `planned` rows)
            # stops counting a quote-rejected register as still enforced.
            after_qa = {(p.peripheral, p.reg_lower): sig(p) for p in plans}
            for r in rows:
                if r["fate"] != "planned":
                    continue
                key = (r["peripheral"], r["register"].lower())
                if key not in before_qa:
                    continue
                kept = after_qa.get(key)
                had = before_qa[key][0] or before_qa[key][1]
                has = bool(kept and (kept[0] or kept[1]))
                if had and not has:
                    r["fate"] = "quote_rejected"
                    r["reason"] = ("all gates dropped by the attribution check "
                                   "(quote unanchored, or self-referential and "
                                   "anchored outside the target's section)")
                elif kept and kept != before_qa[key]:
                    lost_ops = sorted(set(before_qa[key][0]) - set(kept[0]))
                    lost_f = sorted(set(before_qa[key][1]) - set(kept[1]))
                    bits = ([f"ops {lost_ops}"] if lost_ops else []) + \
                           ([f"fields {lost_f}"] if lost_f else [])
                    if bits:
                        r["reason"] += ("; attribution check then dropped "
                                        f"{' and '.join(bits)}")

        if args.save_constraints:
            device_file = device_constraints_file(
                args.device, args.run_dir, args.svd_dir, args.attribution_check,
                (not args.register_only), plans, quote_tiers)
            out = Path(args.save_constraints)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(device_file, indent=1) + "\n")
            print(f"device constraints file: {out}")

        summary = {
            "run_dir": args.run_dir,
            "pac": str(pac_root), "device": args.device,
            "registers_planned": len(plans),
            "fates": {},
            "rows": rows,
        }
        for r in rows:
            summary["fates"][r["fate"]] = summary["fates"].get(r["fate"], 0) + 1

        if plans and not args.dry_run:
            rust_codegen.inject_into_pac(pac_root, args.device, plans)
            summary["injected"] = True
        else:
            summary["injected"] = False

    print(json.dumps({k: v for k, v in summary.items() if k != "rows"}, indent=1))
    if args.report:
        Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report).write_text(json.dumps(summary, indent=1) + "\n")
        print(f"report: {args.report}")


if __name__ == "__main__":
    main()
