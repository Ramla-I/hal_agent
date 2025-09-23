def get_register_field_from_svd(svd_file_path, peripheral_abbr, register_abbr, field_name=None):
    """
    Given an SVD file path, a peripheral abbreviation, a register abbreviation, and an optional field name,
    return the value(s) of the field for the given register of the peripheral. If no field name is given,
    return all information about the register as a dictionary.

    Args:
        svd_file_path (str): Path to the SVD file.
        peripheral_abbr (str): Abbreviation/name of the peripheral (e.g., "ADC1").
        register_abbr (str): Abbreviation/name of the register (e.g., "SR").
        field_name (str, optional): The field to extract (e.g., "resetValue"). If None, return all info.

    Returns:
        list: List of field values found for the register (could be empty if not found), or
        dict: All information about the register if field_name is None.
    """
    if not os.path.exists(svd_file_path):
        raise FileNotFoundError(f"SVD file not found: {svd_file_path}")

    tree = ET.parse(svd_file_path)
    root = tree.getroot()
    peripherals = root.find("peripherals")
    if peripherals is None:
        raise ValueError(f"No <peripherals> section found in SVD file: {svd_file_path}")

    for periph in peripherals.findall("peripheral"):
        name_elem = periph.find("name")
        if name_elem is not None and name_elem.text == peripheral_abbr:
            registers_elem = periph.find("registers")
            if registers_elem is not None:
                for reg in registers_elem.findall("register"):
                    reg_name_elem = reg.find("name")
                    if reg_name_elem is not None and reg_name_elem.text == register_abbr:
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
                        else:
                            # Return the value(s) of the specified field
                            field_elems = reg.findall(field_name)
                            values = []
                            for elem in field_elems:
                                if elem.text is not None:
                                    values.append(elem.text)
                            return values
            # If peripheral found but register not found
            raise ValueError(f"Register '{register_abbr}' not found in peripheral '{peripheral_abbr}' in SVD file: {svd_file_path}")
    # If peripheral not found
    raise ValueError(f"Peripheral '{peripheral_abbr}' not found in SVD file: {svd_file_path}")


 
def main():
    import argparse
    import pprint

    parser = argparse.ArgumentParser(description="Extract register or field info from an SVD file.")
    parser.add_argument("svd_file", help="Path to the SVD file (e.g., devices/rm0090/stm32f405.svd)")
    parser.add_argument("peripheral", help="Peripheral abbreviation (e.g., 'FSMC')")
    parser.add_argument("register", help="Register abbreviation (e.g., 'BCR1')")
    parser.add_argument("--field", help="Field name to extract (optional)", default=None)

    args = parser.parse_args()

    try:
        result = get_register_field_from_svd(
            args.svd_file,
            args.peripheral,
            args.register,
            args.field
        )
        pprint.pprint(result)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()