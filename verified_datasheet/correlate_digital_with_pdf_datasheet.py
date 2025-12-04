import argparse
import csv
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass
class Row:
    peripheral: str
    register: str
    field_name: str
    key: str
    correct_value: str
    svd_value: str
    agent_value: str

    @property
    def identifier(self) -> str:
        """
        Build the string to search for in the PDF.

        The user described the pattern as "peripheralname_egsiter_nae"
        which we interpret as "peripheral_register_fieldname".
        Some rows have empty field_name – in that case, skip it.
        """
        parts = [self.peripheral, self.register]
        if self.field_name:
            parts.append(self.field_name)
        return "_".join(parts)


def iter_rows(path: Path) -> Iterable[Row]:
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            yield Row(
                peripheral=r.get("peripheral", "").strip(),
                register=r.get("register", "").strip(),
                field_name=r.get("field_name", "").strip(),
                key=r.get("key", "").strip(),
                correct_value=r.get("correct_value", "").strip(),
                svd_value=r.get("svd_value", "").strip(),
                agent_value=r.get("agent_value", "").strip(),
            )


def write_rows(path: Path, rows: Iterable[Row]) -> None:
    rows = list(rows)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "peripheral",
                "register",
                "field_name",
                "key",
                "correct_value",
                "svd_value",
                "agent_value",
            ],
        )
        writer.writeheader()
        for r in rows:
            writer.writerow(
                {
                    "peripheral": r.peripheral,
                    "register": r.register,
                    "field_name": r.field_name,
                    "key": r.key,
                    "correct_value": r.correct_value,
                    "svd_value": r.svd_value,
                    "agent_value": r.agent_value,
                }
            )


def choose_correct_value(row: Row) -> Row | bool | bool:
    """
    Present the row values and let the user decide what to put into correct_value.
    """
    ORANGE = "\033[38;5;208m"
    ENDC = "\033[0m"
    print("\n---------------------------")
    print(
        f"Row: peripheral={row.peripheral}, register={row.register}, "
        f"field=\033[92;1m{row.field_name or '<none>'}\033[0m, key=\033[92;1m{row.key}\033[0m"
    )
    print(f"  current correct_value: {row.correct_value or '<empty>'}")
    print(f"  svd_value           (s): {ORANGE}{row.svd_value or '<empty>'}{ENDC}")
    print(f"  agent_value         (a): {ORANGE}{row.agent_value or '<empty>'}{ENDC}")
    print("Choose: [s]vd_value, [a]gent_value, [o]ther (manual), [k]eep current, [x] exit, [d]elete row")
    
    delete = False
    leave = False
    while True:
        choice = input("(s/a/o/k/x/d) > ").strip().lower()
        if choice == "s":
            row.correct_value = row.svd_value
            break
        elif choice == "a":
            row.correct_value = row.agent_value
            break
        elif choice == "o":
            val = input("Enter custom correct_value: ").strip()
            row.correct_value = val
            break
        elif choice == "k":
            # keep whatever is there
            break
        elif choice == "x":
            leave = True            
            break
        elif choice == "d":
            print("deleting this row")
            delete = True
            break
        else:
            print("Please choose one of: s, a, o, k, x, d.")

    return row, leave, delete


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Interactively correlate CSV rows with a PDF datasheet.\n"
            "For each row, the script will show the string "
            '"peripheral_register_fieldname" for you to search in the PDF, '
            "the correct_value (svd_value, agent_value, or a custom value)."
        )
    )
    parser.add_argument(
        "csv_path",
        type=str,
        help="Path to input CSV (e.g. rm0041_stm32f100_full.csv).",
    )
    parser.add_argument(
        "pdf_path",
        type=str,
        help="Path to the PDF datasheet.",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Optional path for output CSV. If omitted, the input CSV is overwritten.",
    )

    args = parser.parse_args()
    csv_path = Path(args.csv_path)
    pdf_path = Path(args.pdf_path)

    if not csv_path.is_file():
        raise SystemExit(f"CSV not found: {csv_path}")
    if not pdf_path.is_file():
        raise SystemExit(f"PDF not found: {pdf_path}")

    # Open the PDF in Preview (macOS) if possible.
    try:
        print(f"Opening PDF in Preview: {pdf_path}")
        subprocess.run(["open", str(pdf_path)], check=False)
    except Exception as exc:
        print(f"Could not auto-open PDF: {exc}")

    all_rows = list(iter_rows(csv_path))
    updated_rows = []

    prev_peripheral = None
    prev_register = None
    deleted_rows = []
    for idx, row in enumerate(all_rows, start=1):
        if row.correct_value:
            updated_rows.append(row)
            continue

        identifier = row.peripheral + "_" + row.register
        print(f"\n=== Row {idx}/{len(all_rows)} ===")
        if identifier and (prev_peripheral != row.peripheral or prev_register != row.register):
            print(f'Search string for this row: "{identifier}"')
            print(
                "Use Preview (or your PDF viewer) search (⌘+F) with this string.\n"
                "Press Enter when you are on the right place in the PDF, or type 's' then Enter to skip."
            )
            # INSERT_YOUR_CODE
            # Try to automatically search for the identifier in the PDF using macOS Preview's search.
            # This only works on macOS as Preview supports AppleScript automation.
            # If not macOS, just continue as before.
            import sys
            import platform

            if platform.system() == "Darwin" and identifier:
                # The following AppleScript will bring Preview to front,
                # open the "Find" bar, and paste/search for the identifier.
                # We attempt to interact with the front Preview window.
                from subprocess import run, DEVNULL

                applescript = f"""
                tell application "Preview"
                    activate
                    delay 0.2
                    tell application "System Events"
                        keystroke "f" using command down
                        delay 0.15
                        keystroke "{identifier}"
                        delay 0.15
                        key code 36 -- enter
                    end tell
                end tell
                """
                try:
                    run(["osascript", "-e", applescript], check=False, stdout=DEVNULL, stderr=DEVNULL)
                    print(f"(Preview: search for '{identifier}' issued automatically)")
                except Exception as exc:
                    print(f"(Could not auto-search in Preview: {exc})")
            ans = input("> ").strip().lower()
            if ans == "s":
                print("Skipping PDF-guided context for this row.")
        else:
            print("Row has no identifier (peripheral/register/field_name missing); skipping PDF search.")

        prev_peripheral = row.peripheral
        prev_register = row.register
        row, leave, delete = choose_correct_value(row)

        if leave:
            print("Exiting...")
            break
        if delete:
            deleted_rows.append(row)
            continue

        updated_rows.append(row)

    # If updated_rows are fewer, append the rest of the rows from all_rows
    if len(updated_rows) + len(deleted_rows) < len(all_rows):
        updated_indices = set()
        for r in updated_rows + deleted_rows:
            try:
                idx = all_rows.index(r)
                updated_indices.add(idx)
            except ValueError:
                continue
        for idx, row in enumerate(all_rows):
            if idx not in updated_indices:
                updated_rows.append(row)
    
    if not args.output:
        # No output path specified, save a backup of the input CSV
        from shutil import copyfile
        bak_path = str(csv_path) + '.bak'
        print(f"No output file specified, saving input CSV as backup to {bak_path}")
        copyfile(csv_path, bak_path)

    output_path = Path(args.output) if args.output else csv_path
    print(f"\nWriting updated CSV to {output_path}")
    write_rows(output_path, updated_rows)



if __name__ == "__main__":
    main()


