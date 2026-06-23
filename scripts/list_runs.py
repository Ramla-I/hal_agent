"""List pipeline runs from their per-run manifests.

    python scripts/list_runs.py                      # table of all runs
    python scripts/list_runs.py --device rm0091      # filter to one device
    python scripts/list_runs.py --valid              # only valid runs
    python scripts/list_runs.py --json               # raw JSON
    python scripts/list_runs.py --mark-used rm0091 3 # flag run 3 of rm0091 as used
"""
import argparse
import json
import os
import sys

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, repo_root)

from utils.run_manifest import find_run_manifests, runs_table, mark_used


def main() -> None:
    parser = argparse.ArgumentParser(description="List pipeline runs from run manifests")
    parser.add_argument("--device", help="Filter to a device name")
    parser.add_argument("--valid", action="store_true", help="Only valid runs")
    parser.add_argument("--used", action="store_true", help="Only runs marked used")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a table")
    parser.add_argument("--mark-used", nargs=2, metavar=("DEVICE", "RUN"),
                        help="Mark a run used (sets used=true) and exit")
    args = parser.parse_args()

    if args.mark_used:
        device, run = args.mark_used[0], int(args.mark_used[1])
        path = mark_used(repo_root, device, run, True)
        print(f"marked used: {path}" if path else f"no manifest for {device} run {run}")
        return

    manifests = find_run_manifests(repo_root)
    if args.device:
        manifests = [m for m in manifests if m.device_name == args.device]
    if args.valid:
        manifests = [m for m in manifests if m.valid]
    if args.used:
        manifests = [m for m in manifests if m.used]

    if not manifests:
        print("No run manifests found (runs created before manifest tracking won't appear).")
        return

    if args.json:
        print(json.dumps([m.model_dump() for m in manifests], indent=2))
    else:
        print(runs_table(manifests))


if __name__ == "__main__":
    main()
