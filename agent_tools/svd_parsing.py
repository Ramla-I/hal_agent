import os
import xml.etree.ElementTree as ET

def get_peripheral_names(svd_file_paths):
    """
    Given a list of SVD file paths, extract all unique peripheral names across all files.

    Args:
        svd_file_paths (list[str]): List of SVD file paths.

    Returns:
        list[str]: List of unique peripheral names.
    """
    if not svd_file_paths or not isinstance(svd_file_paths, list):
        raise ValueError("svd_file_paths must be a non-empty list of file paths")

    peripheral_names_set = set()
    for svd_file_path in svd_file_paths:
        if not os.path.exists(svd_file_path):
            raise FileNotFoundError(f"SVD file not found: {svd_file_path}")

        tree = ET.parse(svd_file_path)
        root = tree.getroot()
        peripherals = root.find("peripherals")
        if peripherals is None:
            raise ValueError(f"No <peripherals> section found in SVD file: {svd_file_path}")

        for periph in peripherals.findall("peripheral"):
            name_elem = periph.find("name")
            if name_elem is not None and name_elem.text:
                peripheral_names_set.add(name_elem.text)

    return list(peripheral_names_set)


def get_register_names_for_peripheral(svd_file_paths, peripheral_name):
    """
    Given a list of SVD file paths and a peripheral name, return a list of unique register names
    for that peripheral across all files.

    Args:
        svd_file_paths (list[str]): List of SVD file paths.
        peripheral_name (str): Name of the peripheral.

    Returns:
        list[str]: List of unique register names for the specified peripheral across all files.
    """
    if not svd_file_paths or not isinstance(svd_file_paths, list):
        raise ValueError("svd_file_paths must be a non-empty list of file paths")

    register_names_set = set()
    found_peripheral = False

    for svd_file_path in svd_file_paths:
        if not os.path.exists(svd_file_path):
            raise FileNotFoundError(f"SVD file not found: {svd_file_path}")

        tree = ET.parse(svd_file_path)
        root = tree.getroot()
        peripherals = root.find("peripherals")
        if peripherals is None:
            raise ValueError(f"No <peripherals> section found in SVD file: {svd_file_path}")

        for periph in peripherals.findall("peripheral"):
            name_elem = periph.find("name")
            if name_elem is not None and name_elem.text == peripheral_name:
                found_peripheral = True
                registers_elem = periph.find("registers")
                if registers_elem is not None:
                    for reg in registers_elem.findall("register"):
                        reg_name_elem = reg.find("name")
                        if reg_name_elem is not None and reg_name_elem.text:
                            register_names_set.add(reg_name_elem.text)

    if not found_peripheral:
        raise ValueError(f"Peripheral '{peripheral_name}' not found in any SVD file: {svd_file_paths}")

    return list(register_names_set)


