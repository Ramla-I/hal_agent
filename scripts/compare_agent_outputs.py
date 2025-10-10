import json
from typing import Any, List, Dict


def compare_json_fields(file1: str, file2: str) -> List[Dict[str, Any]]:
    """
    Compare the values of fields in two JSON files and return a structured list of differences.
    Each difference is a dict with keys: 'field', 'value1', 'value2', and 'type'.
    Also prints the differences in a readable way.
    """
    def load_json(path):
        with open(path, 'r') as f:
            return json.load(f)

    def compare_dicts(d1, d2, prefix="") -> List[Dict[str, Any]]:
        diffs = []
        all_keys = set(d1.keys()) | set(d2.keys())
        for key in all_keys:
            if key == 'description':
                continue  # Skip description fields
            v1 = d1.get(key, None)
            v2 = d2.get(key, None)
            full_key = f"{prefix}.{key}" if prefix else key
            if isinstance(v1, dict) and isinstance(v2, dict):
                diffs.extend(compare_dicts(v1, v2, prefix=full_key))
            elif isinstance(v1, list) and isinstance(v2, list):
                if len(v1) != len(v2):
                    diffs.append({
                        'field': full_key,
                        'type': 'list_length',
                        'value1': len(v1),
                        'value2': len(v2)
                    })
                min_len = min(len(v1), len(v2))
                for i in range(min_len):
                    item1, item2 = v1[i], v2[i]
                    if isinstance(item1, dict) and isinstance(item2, dict):
                        diffs.extend(compare_dicts(item1, item2, prefix=f"{full_key}[{i}]") )
                    else:
                        if item1 != item2:
                            diffs.append({
                                'field': f"{full_key}[{i}]",
                                'type': 'list_item',
                                'value1': item1,
                                'value2': item2
                            })
                # If one list is longer
                if len(v1) > len(v2):
                    for i in range(len(v2), len(v1)):
                        diffs.append({
                            'field': f"{full_key}[{i}]",
                            'type': 'extra_in_file1',
                            'value1': v1[i],
                            'value2': ''
                        })
                elif len(v2) > len(v1):
                    for i in range(len(v1), len(v2)):
                        diffs.append({
                            'field': f"{full_key}[{i}]",
                            'type': 'extra_in_file2',
                            'value1': '',
                            'value2': v2[i]
                        })
            else:
                # If one value is None (missing), treat as missing field
                if v1 is None and v2 is not None:
                    diffs.append({
                        'field': full_key,
                        'type': 'missing_in_file1',
                        'value1': '',
                        'value2': v2
                    })
                elif v2 is None and v1 is not None:
                    diffs.append({
                        'field': full_key,
                        'type': 'missing_in_file2',
                        'value1': v1,
                        'value2': ''
                    })
                elif v1 != v2:
                    diffs.append({
                        'field': full_key,
                        'type': 'value',
                        'value1': v1,
                        'value2': v2
                    })
        return diffs

    data1 = load_json(file1)
    data2 = load_json(file2)
    differences = compare_dicts(data1, data2)

    # Print differences in table form
    if not differences:
        print("No differences found.")
    else:
        # Table header
        col1 = "Field"
        col2 = file1
        col3 = file2
        # Find max widths
        field_width = max(len(col1), max((len(str(d['field'])) for d in differences), default=0))
        val1_width = max(len(col2), max((len(str(d['value1'])) for d in differences), default=0))
        val2_width = max(len(col3), max((len(str(d['value2'])) for d in differences), default=0))
        # Print header
        print(f"{col1:<{field_width}} | {col2:<{val1_width}} | {col3:<{val2_width}}")
        print(f"{'-'*field_width}-+-{'-'*val1_width}-+-{'-'*val2_width}")
        # Print rows
        for diff in differences:
            print(f"{diff['field']:<{field_width}} | {str(diff['value1']):<{val1_width}} | {str(diff['value2']):<{val2_width}}")
    return differences

# Example usage (uncomment to use):
# compare_json_fields("agent_output/rm0041/4/TIM1_ARR", "agent_output/rm0041/3/TIM1_ARR")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Compare two agent output JSON files and print differences.")
    parser.add_argument("file1", help="Path to first JSON file")
    parser.add_argument("file2", help="Path to second JSON file")
    args = parser.parse_args()

    compare_json_fields(args.file1, args.file2)


