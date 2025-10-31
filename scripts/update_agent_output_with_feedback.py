import json
import sys
import os
import argparse

def update_registerinfo_with_feedback(original_dict, feedback_dict):
    """
    Update the original_dict with values from feedback_dict following these rules:
    - For each field in feedback_dict:
        - If the value is empty ("" or []), keep the original value.
        - If the value is different, replace with feedback value.
        - If it's a new field in feedback, add it to original.
    """
    updated = original_dict.copy()
    for key, feedback_value in feedback_dict.items():
        if key not in original_dict:
            # New field, just add
            updated[key] = feedback_value
        else:
            orig_value = original_dict[key]
            # For primitive fields
            if isinstance(feedback_value, (str, int, float, type(None))):
                if feedback_value == "" or feedback_value is None:
                    updated[key] = orig_value
                elif feedback_value != orig_value:
                    updated[key] = feedback_value
                else:
                    updated[key] = orig_value
            # For list fields: (e.g., readonly_bits, write_only_bits, read_write_bits, subfields)
            elif isinstance(feedback_value, list):
                if len(feedback_value) == 0:
                    updated[key] = orig_value
                else:
                    # For subfields we should recursively update each corresponding field if possible
                    if key == "subfields":
                        # Each subfield has "name", do alignment by name
                        orig_subfields = {sf['name']: sf for sf in orig_value} if orig_value else {}
                        updated_subfields = []
                        feedback_subfields = {sf['name']: sf for sf in feedback_value}
                        seen_names = set()

                        # Process all feedback subfields
                        for name, feedback_sf in feedback_subfields.items():
                            seen_names.add(name)
                            orig_sf = orig_subfields.get(name, None)
                            if orig_sf:
                                updated_sf = update_registerinfo_with_feedback(orig_sf, feedback_sf)
                            else:
                                updated_sf = feedback_sf
                            updated_subfields.append(updated_sf)
                        # Add any original subfields that aren't in feedback
                        for name, orig_sf in orig_subfields.items():
                            if name not in seen_names:
                                updated_subfields.append(orig_sf)
                        updated[key] = updated_subfields
                    else:
                        updated[key] = feedback_value
            # For dict fields (e.g., bit_number in subfields)
            elif isinstance(feedback_value, dict):
                orig_val = orig_value if isinstance(orig_value, dict) else {}
                updated[key] = update_registerinfo_with_feedback(orig_val, feedback_value)
            else:
                # Fallback, just use feedback value if not empty, else original
                updated[key] = feedback_value if feedback_value else orig_value
    # Also retain original fields not present in feedback
    for key, value in original_dict.items():
        if key not in updated:
            updated[key] = value
    return updated

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update agent output with feedback")
    parser.add_argument("original_json_folder", help="Path to the original JSON folder")
    parser.add_argument("output_json_folder", help="Path to the output JSON folder")
    args = parser.parse_args()

    original_json_folder = args.original_json_folder
    output_json_folder = args.output_json_folder
    feedback_json_folder = os.path.join(original_json_folder, "judge_iteration")

    if not os.path.exists(output_json_folder):
        os.makedirs(output_json_folder)

    for file in os.listdir(original_json_folder):
        if not "summary" in file and not file.endswith(".csv") and not "judge_iteration" in file and not "analyzer_iteration" in file:
            original_json_path = os.path.join(original_json_folder, file)
            feedback_json_path = os.path.join(feedback_json_folder, file)
            output_json_path = os.path.join(output_json_folder, file)
            
            with open(original_json_path, "r") as f:
                    original_json = json.load(f)

            if not os.path.exists(feedback_json_path):
                # If feedback file doesn't exist, copy original to output
                updated = original_json
            else:
                with open(feedback_json_path, "r") as f:
                    feedback_json = json.load(f)
                updated = update_registerinfo_with_feedback(original_json, feedback_json)
            
            with open(output_json_path, "w") as f:
                json.dump(updated, f, indent=2)
