import os
import xml.etree.ElementTree as ET


def resolve_peripheral_registers(root, ns: str = ""):
    """Map peripheral name (lowercase) -> its ``<registers>`` element, resolving
    ``derivedFrom`` so derived instances inherit the base peripheral's registers.

    STM SVDs define instance 1 with full registers and the rest as
    ``<peripheral derivedFrom="I2C1">`` (registers inherited, not repeated).
    Without this resolution derived instances (i2c2, usart2..8, ...) parse to zero
    registers and are silently skipped by both the generator and the diff.

    Args:
        root: parsed SVD root element.
        ns: XML namespace prefix (e.g. ``"{...}"``); ``""`` for namespace-free SVDs.

    Returns:
        dict[str, Element | None]: peripheral name -> registers element (None if the
        peripheral and its derivedFrom chain have no registers).
    """
    by_name = {}
    for p in root.iter(f"{ns}peripheral"):
        name_elem = p.find(f"{ns}name")
        if name_elem is not None and name_elem.text:
            by_name[name_elem.text.strip().lower()] = p

    resolved = {}
    for name, p in by_name.items():
        registers = p.find(f"{ns}registers")
        # Follow the derivedFrom chain until we find an element with registers.
        seen = set()
        current = p
        while registers is None:
            base = current.get("derivedFrom")
            if not base:
                break
            base = base.strip().lower()
            if base in seen or base not in by_name:
                break
            seen.add(base)
            current = by_name[base]
            registers = current.find(f"{ns}registers")
        resolved[name] = registers
    return resolved


def _strip_peripheral_prefix(register_name: str, peripheral_name: str) -> str:
    """Lowercase a register name and drop a leading ``{peripheral}_`` if present."""
    name = register_name.strip().lower()
    prefix = f"{peripheral_name.lower()}_"
    if name.startswith(prefix):
        name = name[len(prefix):]
    return name


def expand_dim_indices(elem, ns: str = "") -> list:
    """Index tokens for an SVD ``<dim>`` register/cluster array: from ``dimIndex``
    (e.g. ``"2-4"`` -> ``["2","3","4"]``, ``"1,3,5"`` -> ``["1","3","5"]``) or, if
    absent, ``0..dim-1``. ``[]`` if the element is not a dim array."""
    dim_index = elem.findtext(f"{ns}dimIndex")
    if dim_index:
        s = dim_index.strip()
        if "-" in s and "," not in s:
            lo, hi = s.split("-", 1)
            try:
                return [str(i) for i in range(int(lo), int(hi) + 1)]
            except ValueError:
                return []
        return [p.strip() for p in s.split(",") if p.strip()]
    dim = elem.findtext(f"{ns}dim")
    if dim:
        try:
            return [str(i) for i in range(int(dim))]
        except ValueError:
            return []
    return []


def expand_dim_register_name(name: str, elem, ns: str = "") -> list:
    """A register name with a ``%s``/``[%s]`` placeholder -> its concrete instances
    (``BCR%s`` dim 2-4 -> ``["BCR2","BCR3","BCR4"]``). Names without a placeholder
    pass through unchanged."""
    if "%s" not in name:
        return [name]
    base = name.replace("[%s]", "%s")
    return [base.replace("%s", i) for i in expand_dim_indices(elem, ns)] or [name]


def _iter_svd_roots(svd_file_paths):
    if not svd_file_paths or not isinstance(svd_file_paths, list):
        raise ValueError("svd_file_paths must be a non-empty list of file paths")
    for svd_file_path in svd_file_paths:
        if not os.path.exists(svd_file_path):
            raise FileNotFoundError(f"SVD file not found: {svd_file_path}")
        yield ET.parse(svd_file_path).getroot()


def get_peripheral_names(svd_file_paths):
    """Unique peripheral names (lowercase) across all SVD files."""
    names = set()
    for root in _iter_svd_roots(svd_file_paths):
        names.update(resolve_peripheral_registers(root).keys())
    return list(names)


def get_register_names_for_peripheral(svd_file_paths, peripheral_name):
    """Unique register names for a peripheral across all SVD files (derivedFrom- and
    <dim>-aware). ``<dim>`` arrays are expanded to concrete names (``BCR%s`` ->
    ``bcr2/bcr3/bcr4``), so the caller never sees a ``%s`` placeholder."""
    register_names = set()
    found = False
    target = peripheral_name.lower()

    for root in _iter_svd_roots(svd_file_paths):
        resolved = resolve_peripheral_registers(root)
        if target not in resolved:
            continue
        found = True
        registers_elem = resolved[target]
        if registers_elem is not None:
            for reg in registers_elem.findall("register"):
                name_elem = reg.find("name")
                if name_elem is not None and name_elem.text:
                    stripped = _strip_peripheral_prefix(name_elem.text, peripheral_name)
                    # Expand <dim> arrays (BCR%s -> bcr2/bcr3/bcr4) so the generator
                    # receives concrete register names, not the %s placeholder.
                    for concrete in expand_dim_register_name(stripped, reg):
                        register_names.add(concrete)

    if not found:
        raise ValueError(f"Peripheral '{peripheral_name}' not found in any SVD file: {svd_file_paths}")
    return list(register_names)


def get_field_counts_for_peripheral(svd_file_paths, peripheral_name):
    """Return {register_name: field_count} for a peripheral (derivedFrom- and
    <dim>-aware). ``<dim>`` arrays are expanded to concrete names, each instance
    sharing the base register's field count (``BCR%s`` -> ``bcr2/bcr3/bcr4``)."""
    field_counts = {}
    found = False
    target = peripheral_name.lower()

    for root in _iter_svd_roots(svd_file_paths):
        resolved = resolve_peripheral_registers(root)
        if target not in resolved:
            continue
        found = True
        registers_elem = resolved[target]
        if registers_elem is not None:
            for reg in registers_elem.findall("register"):
                name_elem = reg.find("name")
                if name_elem is not None and name_elem.text:
                    reg_name = _strip_peripheral_prefix(name_elem.text, peripheral_name)
                    fields_elem = reg.find("fields")
                    count = len(fields_elem.findall("field")) if fields_elem is not None else 0
                    # Expand <dim> arrays (EP%sR -> ep0r..ep7r) so the count is keyed
                    # by concrete names, matching get_register_names_for_peripheral;
                    # all instances of an array share the base register's fields.
                    for concrete in expand_dim_register_name(reg_name, reg):
                        field_counts[concrete] = count

    if not found:
        raise ValueError(f"Peripheral '{peripheral_name}' not found in any SVD file: {svd_file_paths}")
    return field_counts
