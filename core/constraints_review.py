"""Join adapter: collected constraints + constraint-validator verdicts -> the
per-RM constraints-review JSONL a human labels.

The constraint chain is: Generator -> collect_constraints (linted per-register
constraint files + enforceability) -> Constraint Validator (quote anchor + LLM
judge -> anchors.jsonl / judgments.jsonl). Both derive from the same generator
run and share the validator's constraint id
    id = sha1(f"{rm}|{register}|{kind}|{datasheet_text}")[:12]
so this joins them by that id and writes one JSONL record per constraint with the
FULL constraint object (nothing duplicated as a sibling column), the validation
result, a devices list (prefilled from rm_device_mapping.xml), and a tp_fp label.

Output: evaluation/{mfr}/{rm}/{run}/{rm}_constraints_review.jsonl
Reviewer edits `tp_fp` (and trims `devices` for device-specific exceptions);
both are preserved across re-runs, keyed on id.

Stdlib only (json/glob/os/xml/hashlib) — host-testable.
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import xml.etree.ElementTree as ET
from typing import Optional

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def constraint_id(rm: str, register: str, kind: str, datasheet_text: str) -> str:
    """Replicates run_constraint_validation_phase's id so the join lines up."""
    return hashlib.sha1(f"{rm}|{register}|{kind}|{datasheet_text}".encode()).hexdigest()[:12]


def rm_devices(rm: str, repo_root: str = _REPO_ROOT, manufacturer: str = "stm") -> list[str]:
    """SVD device stems mapped to an RM (from devices/{mfr}/rm_device_mapping.xml),
    e.g. rm0091 -> ['stm32f0x1','stm32f0x2','stm32f0x8']. Falls back to the RM's
    svd/ dir if the mapping file is absent."""
    mapping = os.path.join(repo_root, "devices", manufacturer, "rm_device_mapping.xml")
    if os.path.isfile(mapping):
        try:
            root = ET.parse(mapping).getroot()
            for node in root.iter("reference_manual"):
                if (node.get("rm") or "").lower() == rm.lower():
                    return [os.path.splitext(sf.text.strip())[0]
                            for sf in node.iter("svd_file") if sf.text and sf.text.strip()]
        except Exception:
            pass
    svd_dir = os.path.join(repo_root, "devices", manufacturer, rm, "svd")
    return sorted(os.path.splitext(os.path.basename(p))[0]
                  for p in glob.glob(os.path.join(svd_dir, "*.svd")) + glob.glob(os.path.join(svd_dir, "*.xml")))


def _index_jsonl(path: str, keep: tuple) -> dict:
    """id -> {kept fields} from a validator jsonl (anchors/judgments)."""
    out: dict = {}
    if not os.path.isfile(path):
        return out
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            if "id" in r:
                out[r["id"]] = {k: r.get(k) for k in keep}
    return out


def _split_peripheral_register(fname: str) -> tuple[str, str]:
    stem = fname[:-5] if fname.endswith(".json") else fname
    peripheral, _, register = stem.partition("_")
    return peripheral, register


def build_constraints_review(rm: str, run: str, collect_dir: str, validator_dir: str,
                             out_path: str, repo_root: str = _REPO_ROOT,
                             manufacturer: str = "stm") -> int:
    """Write {rm}_constraints_review.jsonl. Returns the number of records."""
    anchors = _index_jsonl(os.path.join(validator_dir, "anchors.jsonl"), ("tier",))
    judgments = _index_jsonl(os.path.join(validator_dir, "judgments.jsonl"),
                             ("verdict", "confidence"))
    devices_default = rm_devices(rm, repo_root, manufacturer)

    # Preserve reviewer-owned fields (tp_fp, devices edits) across re-runs, by id.
    preserved: dict = {}
    if os.path.isfile(out_path):
        for line in open(out_path, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            if r.get("id"):
                preserved[r["id"]] = {"tp_fp": r.get("tp_fp", ""), "devices": r.get("devices")}

    records: list[dict] = []
    for path in sorted(glob.glob(os.path.join(collect_dir, "*.json"))):
        if os.path.basename(path) == "manifest.json":
            continue
        peripheral, register = _split_peripheral_register(os.path.basename(path))
        try:
            data = json.load(open(path, encoding="utf-8"))
        except Exception:
            continue
        for c in (data.get("access_constraints_v2") or []):
            if not isinstance(c, dict):
                continue
            cid = constraint_id(rm, register, c.get("kind", "state_gate"),
                                c.get("datasheet_text", ""))
            judged = judgments.get(cid, {})
            prev = preserved.get(cid, {})
            records.append({
                "id": cid,
                "rm": rm, "peripheral": peripheral, "register": register,
                "source_file": f"{rm}/{run}/{peripheral}_{register}",
                "devices": prev.get("devices") if prev.get("devices") is not None else list(devices_default),
                "constraint": c,                                  # full object; nothing duplicated
                "anchor_tier": (anchors.get(cid) or {}).get("tier", "unanchored"),
                "verdict": judged.get("verdict", ""),             # "" = never reached the judge (unanchored)
                "confidence": judged.get("confidence"),
                "tp_fp": prev.get("tp_fp", ""),
            })

    records.sort(key=lambda r: (r["peripheral"], r["register"], r["id"]))
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    tmp = out_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=True) + "\n")
    os.replace(tmp, out_path)
    return len(records)


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser(description="Build the per-RM constraints-review JSONL")
    ap.add_argument("--rm", required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument("--manufacturer", default="stm")
    ap.add_argument("--collect-dir", default=None,
                    help="collect_constraints output (default constraints/collected/{rm}_{run})")
    ap.add_argument("--validator-dir", default=None,
                    help="constraint_validation dir (default agent_output/{mfr}/{rm}/{run}/constraint_validation)")
    ap.add_argument("--out", default=None,
                    help="output jsonl (default evaluation/{mfr}/{rm}/{run}/{rm}_constraints_review.jsonl)")
    args = ap.parse_args()

    collect_dir = args.collect_dir or os.path.join(
        _REPO_ROOT, "applications", "pac_codegen", "constraints", "collected", f"{args.rm}_{args.run}")
    validator_dir = args.validator_dir or os.path.join(
        _REPO_ROOT, "agent_output", args.manufacturer, args.rm, args.run, "constraint_validation")
    out_path = args.out or os.path.join(
        _REPO_ROOT, "evaluation", args.manufacturer, args.rm, args.run, f"{args.rm}_constraints_review.jsonl")

    n = build_constraints_review(args.rm, args.run, collect_dir, validator_dir, out_path,
                                 manufacturer=args.manufacturer)
    print(f"wrote {n} constraint(s) -> {out_path}")


if __name__ == "__main__":
    main()
