import os
import xml.etree.ElementTree as ET

def get_register_field_from_svd(svd_file_path, peripheral_abbr, register_abbr, field_name=None):
    """
    Given an SVD file path, a peripheral abbreviation, a register abbreviation, and an optional field name,
    return the value(s) of the field for the given register of the peripheral. If no field name is given,
    return all information about the register as a dictionary.

    Args:
        svd_file_path (str): Path to the SVD file.
        peripheral_abbr (str): Abbreviation/name of the peripheral (e.g., "ADC1").
        register_abbr (str): Abbreviation/name of the register (e.g., "SR").
        field_name (str, optional): The field to extract (e.g., "BREGEN"). If None, return all info.

    Returns:
        dict: All information about the register if field_name is None, or a dictionary of the field values if field_name is provided.
    """

    if not os.path.exists(svd_file_path):
        raise FileNotFoundError(f"SVD file not found: {svd_file_path}")

    tree = ET.parse(svd_file_path)
    root = tree.getroot()
    peripherals = root.find("peripherals")
    if peripherals is None:
        raise ValueError(f"No <peripherals> section found in SVD file: {svd_file_path}")

    # --- Find the peripheral --- #
    for periph in peripherals.findall("peripheral"):
        name_elem = periph.find("name")
        if name_elem is not None and name_elem.text and name_elem.text.lower() == peripheral_abbr.lower():
            # print(f"Found peripheral '{peripheral_abbr}' in SVD file: {svd_file_path}")
            registers_elem = periph.find("registers")
            if registers_elem is not None:

                # --- Find the register --- #
                for reg in registers_elem.findall("register"):
                    reg_name_elem = reg.find("name")

                    if reg_name_elem is not None and reg_name_elem.text and (reg_name_elem.text.lower() == register_abbr.lower() or reg_name_elem.text.lower() == peripheral_abbr.lower() + '_' + register_abbr.lower()):
                        # print(f"Found register '{register_abbr}' in SVD file: {svd_file_path}")
                        if field_name is None:
                            # Return all information about the register as a dictionary
                            reg_info = {}
                            for child in reg:
                                # If the child has sub-elements, represent as dict/list
                                if len(child):
                                    # If all children have the same tag, treat as list
                                    tags = [c.tag for c in child]
                                    if len(set(tags)) == 1:
                                        reg_info[child.tag] = []
                                        for c in child:
                                            if len(c):
                                                reg_info[child.tag].append({g.tag: g.text for g in c})
                                            else:
                                                reg_info[child.tag].append(c.text)
                                    else:
                                        reg_info[child.tag] = {c.tag: c.text for c in child}
                                else:
                                    reg_info[child.tag] = child.text
                            return reg_info
                       
                        # --- Find the field --- #
                        else:
                            fields_elem = reg.find("fields")
                            if fields_elem is None:
                                raise ValueError(f"Register '{register_abbr}' has no fields.")

                            for field in fields_elem.findall("field"):
                                fname_elem = field.find("name")
                                if fname_elem is None or not fname_elem.text:
                                    continue

                                # match the field name
                                if fname_elem.text.lower() != field_name.lower():
                                    continue

                                # Build dictionary of all field properties
                                field_info = {}
                                for fchild in field:
                                    field_info[fchild.tag] = fchild.text

                                return field_info
                            
                            raise ValueError(f"Field '{field_name}' not found in register '{register_abbr}' in SVD file: {svd_file_path}")
            # If peripheral found but register not found
            raise ValueError(f"Register '{register_abbr}' not found in peripheral '{peripheral_abbr}' in SVD file: {svd_file_path}")
    # If peripheral not found
    raise ValueError(f"Peripheral '{peripheral_abbr}' not found in SVD file: {svd_file_path}")


 
def main():
    import argparse
    import pprint

    parser = argparse.ArgumentParser(description="Extract register or field info from one or more SVD files and display as a table.")
    parser.add_argument("svd_files_folder", help="Path(s) to the folder containing the SVD file(s) (e.g., devices/rm0090/)")
    parser.add_argument("peripheral", help="Peripheral abbreviation (e.g., 'FSMC')")
    parser.add_argument("register", help="Register abbreviation (e.g., 'BCR1')")
    parser.add_argument("key", help="Key to extract (e.g., 'resetValue')")
    parser.add_argument("--field", help="Field name to extract (optional)", default=None)
    parser.add_argument("--svd_file", help="SVD file to search if only one (optional)", default=None)


    args = parser.parse_args()

    import os

    # Get all SVD file names (with full path) in the folder, sorted alphabetically
    if args.svd_file:
        svd_files = [args.svd_file]
    else:
        svd_files = [
            os.path.join(args.svd_files_folder, f)
            for f in os.listdir(args.svd_files_folder)
            if f.lower().endswith(".svd")
        ]
        svd_files.sort()

    results = []
    for svd_file_path in svd_files:
        result = get_register_field_from_svd(
            svd_file_path,
            args.peripheral,
            args.register,
            args.field
        )
        results.append(result)
    
    # Pretty print the table of results
    if results:
        # Determine if we're looking for one field or full register content
        headers = ["svd_file", args.key]
        rows = []
        for svd_file, dict in zip(svd_files, results):
            row = [svd_file]
            row.append(dict.get(args.key, ""))
            rows.append(row)
        
        # Compute column widths
        col_widths = [max(len(str(x)) for x in ([h] + [row[i] for row in rows])) for i, h in enumerate(headers)]
        fmt = " | ".join("{{:<{}}}".format(w) for w in col_widths)
        # Print header
        print(fmt.format(*headers))
        print('-+-'.join('-' * w for w in col_widths))
        # Print all rows
        for row in rows:
            print(fmt.format(*row))
    else:
        print("No results to display.")

if __name__ == "__main__":
    main()