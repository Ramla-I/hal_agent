import os
import sys
import re

#HACK, remove this once we have a proper package structure
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, repo_root)

import config
from defs import UserContext, Manufacturer

def update_user_context(user_context: UserContext):
    """
    Update a user context entry in config.py based on device_name.
    
    Args:
        user_context: UserContext object with the updated values.
                     The device_name is used to find the entry to update.
    """
    config_path = os.path.join(repo_root, "config.py")
    
    # Read the config.py file
    with open(config_path, "r") as f:
        config_lines = f.readlines()

    updated_lines = []
    in_user_contexts = False
    entry_updated = False

    for idx, line in enumerate(config_lines):
        stripped = line.strip()

        # Find the start of user_contexts list
        if stripped.startswith("user_contexts = ["):
            in_user_contexts = True
            updated_lines.append(line)
            continue

        # Check for the end of the user_contexts list
        if in_user_contexts and stripped == "]":
            in_user_contexts = False
            updated_lines.append(line)
            continue

        # If inside user_contexts array, look for UserContext entries
        if in_user_contexts:
            # Check if this line contains a UserContext entry
            if "UserContext(" in stripped:
                # Find device_name value in this entry
                m = re.search(r"device_name\s*=\s*['\"]([^'\"]+)['\"]", line)
                if m:
                    curr_device_name = m.group(1)
                    
                    # If this entry matches, update all fields
                    if curr_device_name == user_context.device_name:
                        # Update all fields in the UserContext entry
                        updated_line = line
                        updated_line = re.sub(
                            r"device_name\s*=\s*['\"][^'\"]*['\"]",
                            f"device_name='{user_context.device_name}'",
                            updated_line
                        )
                        updated_line = re.sub(
                            r"peripheral_name\s*=\s*['\"][^'\"]*['\"]",
                            f"peripheral_name='{user_context.peripheral_name}'",
                            updated_line
                        )
                        updated_line = re.sub(
                            r"manufacturer\s*=\s*Manufacturer\.\w+",
                            f"manufacturer=Manufacturer.{user_context.manufacturer.name}",
                            updated_line
                        )
                        updated_line = re.sub(
                            r"driver_path\s*=\s*['\"][^'\"]*['\"]",
                            f"driver_path='{user_context.driver_path}'",
                            updated_line
                        )
                        updated_line = re.sub(
                            r"run\s*=\s*\d+",
                            f"run={user_context.run}",
                            updated_line
                        )
                        updated_line = re.sub(
                            r"file_id\s*=\s*['\"][^'\"]*['\"]",
                            f"file_id='{user_context.file_id}'",
                            updated_line
                        )
                        updated_line = re.sub(
                            r"vs_id\s*=\s*['\"][^'\"]*['\"]",
                            f"vs_id='{user_context.vs_id}'",
                            updated_line
                        )
                        
                        updated_lines.append(updated_line)
                        entry_updated = True
                    else:
                        # Keep the original entry
                        updated_lines.append(line)
                else:
                    # Keep the original entry if device_name not found
                    updated_lines.append(line)
            else:
                # Keep other lines in the user_contexts list (like commas, etc.)
                updated_lines.append(line)
            continue
        
        # For all other lines (outside user_contexts)
        updated_lines.append(line)

    # Write back the modified lines
    with open(config_path, "w") as f:
        f.writelines(updated_lines)
    
    if entry_updated:
        print(f"Successfully updated user context for device: {user_context.device_name}")
    else:
        print(f"Warning: No matching entry found for device: {user_context.device_name}")


def main():
    # Example usage
    updated_context = UserContext(
        device_name='rm0033',
        peripheral_name='',
        manufacturer=Manufacturer.STM,
        driver_path='',
        run=1,
        file_id='file-MHtC1XNEQDa2X8jNEjfk1b',
        vs_id='vs_6892501067b08191ac63cc6de06ee629'
    )
    update_user_context(updated_context)

if __name__ == "__main__":
    main()