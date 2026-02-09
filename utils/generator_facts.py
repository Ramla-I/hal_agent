"""Shared utilities for extracting facts from generator output."""

REGISTER_LEVEL_FACTS = [
    'address_offset',
    'reset_value',
    'size',
    'subfields',
]

SUBFIELD_LEVEL_FACTS = [
    'access',
    'bit_offset', # legacy format
    'bit_width', # legacy format
    'bit_number', # new format
    'enumerated_values',
]


def get_bit_offset_width(field, default_zero=False):
    """
    Compute a subfield's bit offset/width.

    Assumptions about input:
    - **field** is a dict-like object (typically one entry from generator output `subfields`).
    - New-format bit location is stored in `field["bit_number"]` as a dict with:
      - `start_bit` (int) and `end_bit` (int), or possibly `None`.
    - Legacy format may store `field["bit_offset"]` and `field["bit_width"]` directly.

    Args:
        field: Subfield dict from generator output.
        default_zero: If True, missing `start_bit`/`end_bit` default to 0 (useful for older
            scripts that historically treated missing bits as 0). If False, missing bits
            yield `(None, None)` unless legacy values exist.

    Returns:
        Tuple `(bit_offset, bit_width)` where each element is:
        - an `int` when derivable, or
        - `None` when not present/derivable.
    """
    bit_number = field.get('bit_number')
    if isinstance(bit_number, dict):
        if default_zero:
            start = bit_number.get('start_bit', 0)
            end = bit_number.get('end_bit', 0)
        else:
            start = bit_number.get('start_bit')
            end = bit_number.get('end_bit')

        if start is not None and end is not None:
            bit_offset = min(start, end)
            bit_width = abs(end - start) + 1
            return bit_offset, bit_width

    bit_offset = field.get('bit_offset')
    bit_width = field.get('bit_width')
    return bit_offset, bit_width


def convert_generator_register_to_svd_like(register_data, include_enums=True, default_zero=False):
    """
    Convert a generator register JSON dict into an SVD-like structure.

    Assumptions about input:
    - **register_data** is a dict-like object representing a single register (generator output).
    - It may contain register-level keys like `address_offset`, `reset_value`, `size`.
    - It may contain a list of subfields at `register_data["subfields"]` (preferred).

    Notes:
    - This function does **not** normalize numeric formats (e.g., it does not convert hex strings
      to ints). Callers that need numeric normalization should do so after this conversion.

    Args:
        register_data: Register dict from generator output.
        include_enums: If True, include `enumerated_values` entries (name/value pairs) when present.
        default_zero: Passed to `get_bit_offset_width()`; see that docstring.

    Returns:
        - A dict with shape:
          - `address_offset`: original value (often str like `"0x..."` or int), default `""`
          - `reset_value`: original value, default `""`
          - `size`: original value, default `None`
          - `fields`: list of dicts, each with:
            - `name` (lowercased str)
            - `description` (str)
            - `access` (str)
            - `bit_offset` (int|None)
            - `bit_width` (int|None)
            - `enumerated_values` (list of `{name, value}`) if `include_enums` else `[]`
        - `None` if `register_data` is falsy (missing/unreadable).
    """
    if not register_data:
        return None

    def bitfield_to_svd_field(field):
        bit_offset, bit_width = get_bit_offset_width(
            field,
            default_zero=default_zero,
        )

        enumerated_values = []
        if include_enums:
            enum_list = field.get('enumerated_values', [])
            for enum in enum_list:
                enumerated_values.append({
                    'name': enum.get('name', '').lower(),
                    'value': enum.get('value', '')
                })

        return {
            'name': field.get('name', '').lower(),
            'description': field.get('description', ''),
            'access': field.get('access', ''),
            'bit_offset': bit_offset,
            'bit_width': bit_width,
            'enumerated_values': enumerated_values if include_enums else [],
        }

    fields = []
    for field in register_data.get('subfields', []):
        fields.append(bitfield_to_svd_field(field))

    return {
        'address_offset': register_data.get('address_offset', ''),
        'reset_value': register_data.get('reset_value', ''),
        'size': register_data.get('size', None),
        'fields': fields,
    }


def extract_facts_from_generator_output(output_json, peripheral, register, include_access=True):
    """
    Extract "facts" from a generator register output for comparison with verified CSV facts.

    Assumptions about input:
    - **output_json** is a dict-like object representing a single register's generator output.
    - **peripheral** and **register** are the names used to key facts (usually from filenames
      like `<PERIPHERAL>_<REGISTER>`).
    - Subfields may be under `output_json["subfields"]` or `output_json["fields"]`.

    Output format:
    - Returns a dict mapping:
      - key: `(peripheral, register, field_name, fact_key)` tuples
      - value: stringified value (via `str(...)`)
    - Register-level facts use `field_name == ""`.

    Notes / caveats:
    - `field_name` is lowercased for matching consistency.
    """
    facts = {}

    if not output_json:
        return facts

    # Register-level facts
    for key in REGISTER_LEVEL_FACTS:
        if key in output_json:
            fact_key = (peripheral, register, '', key)
            facts[fact_key] = str(output_json[key])

    # Field-level facts (handle both 'subfields' and 'fields' key)
    fields_list = output_json.get('subfields', output_json.get('fields', []))

    for field in fields_list:
        # Get field name (handle both 'name' and 'field_name')
        field_name = field.get('name', field.get('field_name', '')).lower()

        # Access
        if include_access and 'access' in SUBFIELD_LEVEL_FACTS and 'access' in field:
            fact_key = (peripheral, register, field_name, 'access')
            facts[fact_key] = str(field['access'])

        bit_offset, bit_width = get_bit_offset_width(field)
        if 'bit_offset' in SUBFIELD_LEVEL_FACTS and bit_offset is not None:
            fact_key = (peripheral, register, field_name, 'bit_offset')
            facts[fact_key] = str(bit_offset)
        if 'bit_width' in SUBFIELD_LEVEL_FACTS and bit_width is not None:
            fact_key = (peripheral, register, field_name, 'bit_width')
            facts[fact_key] = str(bit_width)

    return facts
