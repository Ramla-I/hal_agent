#!/usr/bin/env python3
"""Close the loop: a generator RUN DIRECTORY in, an updated PAC out.

This is the end-to-end driver the pipeline stages plug into::

    generator run dir --> collect (lift + lint) --> select --> inject PAC

It runs collection (grammar-v2 lift plus the stage-0 lint) over the run
directory, then keeps only the constraints that BOTH survived collection AND
are compilable by the current emitter (state gates over observed hardware
state; sequences/action witnesses arrive with later roadmap steps), builds
one plan per register, and injects them all into the PAC in a single shot.

Everything that is dropped is dropped LOUDLY: the report lists every
constraint with its fate (injected / rejected-at-collection /
unsupported-by-emitter / peripheral-not-in-device) and the reason.

Usage:
    python applications/pac_codegen/inject_from_run.py \
        /path/to/agent_output/stm/rm0008/1 \
        --pac applications/pac_codegen/vendored/pac/stm32f1 \
        --device stm32f103 [--svd-dir <svd>] [--dry-run] \
        [--report out/report.json]

--dry-run performs everything except writing to the PAC (selection and plan
construction still run, so the report is complete).
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
import collect_constraints  # noqa: E402
import rust_codegen  # noqa: E402


def select_and_plan(collect_dir: Path, device_dir: Path) -> tuple[list, list[dict]]:
    """From a collection output dir, build injectable RegisterPlans.

    Returns (plans, report_rows). Selection is manifest-driven: only
    constraints collection accepted are considered; each register's accepted
    subset is then offered to the emitter, which may still refuse shapes it
    does not support yet — refusals become report rows, never crashes.
    """
    manifest = json.loads((collect_dir / "manifest.json").read_text())
    plans, rows = [], []

    for reg_entry in manifest["registers"]:
        peripheral = reg_entry["peripheral"]
        source = reg_entry["file"]
        accepted_idx = [
            c["v1_index"] for c in reg_entry["constraints"]
            if c.get("kinds") and not any(
                r.get("reason") for r in c.get("rejects", []))
        ]

        def row(fate: str, reason: str, indices=None):
            rows.append({
                "file": source, "peripheral": peripheral,
                "register": reg_entry["register"], "fate": fate,
                "reason": reason,
                "constraints": indices if indices is not None else accepted_idx,
            })

        for c in reg_entry["constraints"]:
            reasons = sorted({r["reason"] for r in c.get("rejects", [])})
            if reasons:
                row("rejected_at_collection", ";".join(reasons), [c["v1_index"]])

        if not accepted_idx:
            continue
        if not (device_dir / f"{peripheral}.rs").is_file():
            row("peripheral_not_in_device",
                f"{peripheral}.rs absent from {device_dir.name}")
            continue

        # Rebuild a v1 RegisterInfo holding ONLY the accepted constraints and
        # offer it to the emitter.
        out_file = collect_dir / Path(reg_entry["output_path"]).name
        data = json.loads(out_file.read_text())
        data["access_constraints"] = [
            data["access_constraints"][i] for i in accepted_idx]
        data.pop("access_constraints_v2", None)
        data.pop("constraint_reports", None)
        try:
            plan = rust_codegen.RegisterPlan(RegisterInfo(**data), peripheral)
        except NotImplementedError as e:
            row("unsupported_by_emitter", str(e))
            continue
        except ValueError as e:
            row("emitter_rejected", str(e))
            continue
        plans.append(plan)
        row("planned", f"gates: {sorted(op for _, _, op in plan.gated_ops())}")

    return plans, rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run_dir", help="generator run directory (one file per register)")
    ap.add_argument("--pac", required=True, help="PAC crate root to inject into")
    ap.add_argument("--device", required=True, help="device module, e.g. stm32f103")
    ap.add_argument("--svd-dir", default=None,
                    help="SVD file/dir for collection's name+width lint")
    ap.add_argument("--chunks", default=None, metavar="DIR",
                    help="chunked-datasheet root (e.g. .../chunked_datasheets/stm); "
                         "when given, every kept constraint's quote is verified "
                         "against the manual and UNANCHORED quotes drop their "
                         "gates (plan §7.1: no unverifiable evidence reaches a "
                         "crate)")
    ap.add_argument("--report", default=None, help="write the JSON report here")
    ap.add_argument("--save-constraints", default=None, metavar="PATH",
                    help="write the per-DEVICE constraints file (the durable, "
                         "reviewable artifact: exactly what this device's "
                         "crate enforces, plus provenance). Convention: "
                         "applications/pac_codegen/constraints/<device>.json")
    ap.add_argument("--dry-run", action="store_true",
                    help="select and plan, but do not touch the PAC")
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

        plans, rows = select_and_plan(collect_dir, device_dir)

        # Match the artifact and injection exactly: apply the access-mode
        # prune (write-only registers cannot carry modify/read gates) BEFORE
        # saving; injection re-runs it idempotently.
        plans = rust_codegen.prune_plans_for_device(device_dir, plans)

        quote_tiers = {}
        if args.chunks:
            rm = Path(args.run_dir.rstrip("/")).parent.name
            from constraint_validator import quote_anchor as qa
            matcher = qa.RMMatcher(
                rm, str(Path(args.chunks) / rm / "chunks" / "md"))
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
                        })
                        print(f"  note: {plan.peripheral}/{plan.reg_name}: "
                              f"dropped {op} gate — {fate}")
                quote_tiers[(plan.peripheral, plan.reg_name)] = tiers
                if plan.preconditions:
                    kept_plans.append(plan)
            plans = kept_plans

        if args.save_constraints:
            device_file = {
                "device": args.device,
                "source_run": args.run_dir,
                "svd_dir": args.svd_dir,
                "note": "constraints this device's crate enforces, post "
                        "collection-lint, emitter selection, access-mode "
                        "pruning, and (with --chunks) quote verification; "
                        "regenerate with inject_from_run.py",
                "quote_verified_against": args.chunks or None,
                "registers": [
                    {
                        "peripheral": p.peripheral,
                        "register": p.reg_name,
                        "gated_operations": sorted(
                            op for _, _, op in p.gated_ops()),
                        "preconditions": {
                            op: [pre.describe() for pre in pres]
                            for op, pres in p.preconditions.items()},
                        "datasheet_text": p.docs,
                        "quote_verification": quote_tiers.get(
                            (p.peripheral, p.reg_name)),
                    }
                    for p in plans
                ],
            }
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
