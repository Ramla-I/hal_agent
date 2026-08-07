"""Update the device registry (config_devices.json) programmatically.

Replaces the old approach of regex-rewriting config.py source. The registry is
plain JSON, so updates are a robust read-modify-write keyed by device_name —
no source surgery, no fragile line matching.

CLI:
    python scripts/update_config.py rm0033 --run 2 --vs-id vs_abc --file-id file-xyz
"""
import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Optional

# HACK, remove this once we have a proper package structure
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, repo_root)

from defs import UserContext, Manufacturer

REGISTRY_PATH = Path(repo_root) / "config_devices.json"

# Fields a device entry may carry (besides device_name, which is the key).
_DEVICE_FIELDS = ("manufacturer", "peripheral_name", "driver_path", "run", "file_id", "vs_id")


def _load_registry() -> dict[str, Any]:
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_registry(registry: dict[str, Any]) -> None:
    with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2)
        f.write("\n")


def update_device(device_name: str, **fields: Any) -> None:
    """Update (or insert) a device entry in config_devices.json.

    Only the keys passed in *fields* are changed; unspecified fields keep their
    existing values. A new device is appended if device_name isn't present.
    Pass `manufacturer` as a defs.Manufacturer enum NAME or member.
    """
    unknown = set(fields) - set(_DEVICE_FIELDS)
    if unknown:
        raise ValueError(f"Unknown device field(s): {sorted(unknown)}; allowed: {_DEVICE_FIELDS}")

    if "manufacturer" in fields and isinstance(fields["manufacturer"], Manufacturer):
        fields["manufacturer"] = fields["manufacturer"].name

    registry = _load_registry()
    devices = registry.setdefault("devices", [])

    for entry in devices:
        if entry.get("device_name") == device_name:
            entry.update(fields)
            _save_registry(registry)
            print(f"Updated device entry: {device_name}")
            return

    # Not found — append a new entry with sensible defaults.
    new_entry = {"device_name": device_name, "peripheral_name": "", "driver_path": "",
                 "run": 0, "file_id": "", "vs_id": ""}
    new_entry.update(fields)
    if "manufacturer" not in new_entry:
        raise ValueError(f"New device {device_name!r} requires a manufacturer")
    devices.append(new_entry)
    _save_registry(registry)
    print(f"Added device entry: {device_name}")


def update_user_context(user_context: UserContext) -> None:
    """Backward-compatible wrapper: persist a UserContext into the registry."""
    update_device(
        user_context.device_name,
        manufacturer=user_context.manufacturer.name,
        peripheral_name=user_context.peripheral_name,
        driver_path=user_context.driver_path,
        run=user_context.run,
        file_id=user_context.file_id,
        vs_id=user_context.vs_id,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Update a device entry in config_devices.json")
    parser.add_argument("device_name", help="Device to update or add")
    parser.add_argument("--manufacturer", choices=[m.name for m in Manufacturer])
    parser.add_argument("--peripheral-name")
    parser.add_argument("--driver-path")
    parser.add_argument("--run", type=int)
    parser.add_argument("--file-id")
    parser.add_argument("--vs-id")
    args = parser.parse_args()

    fields: dict[str, Any] = {}
    if args.manufacturer is not None:
        fields["manufacturer"] = args.manufacturer
    if args.peripheral_name is not None:
        fields["peripheral_name"] = args.peripheral_name
    if args.driver_path is not None:
        fields["driver_path"] = args.driver_path
    if args.run is not None:
        fields["run"] = args.run
    if args.file_id is not None:
        fields["file_id"] = args.file_id
    if args.vs_id is not None:
        fields["vs_id"] = args.vs_id

    update_device(args.device_name, **fields)


if __name__ == "__main__":
    main()
