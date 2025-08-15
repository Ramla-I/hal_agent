import requests
from io import BytesIO
from openai import OpenAI
import sys
import os

client = OpenAI()

def create_file(client, file_path):
    if file_path.startswith("http://") or file_path.startswith("https://"):
        # Download the file content from the URL
        response = requests.get(file_path)
        file_content = BytesIO(response.content)
        file_name = file_path.split("/")[-1]
        file_tuple = (file_name, file_content)
        result = client.files.create(
            file=file_tuple,
            purpose="assistants"
        )
    else:
        # Handle local file path
        with open(file_path, "rb") as file_content:
            result = client.files.create(
                file=file_content,
                purpose="assistants"
            )
    print(result.id)
    return result.id

def create_vector_store(path, name):
    file_id = create_file(client, path)
    vector_store = client.vector_stores.create(
        name = name
    )
    print(vector_store.id)

    result = client.vector_stores.files.create(
        vector_store_id = vector_store.id,
        file_id = file_id
    )
    print(result)

    result = client.vector_stores.files.list(
        vector_store_id=vector_store.id
    )
    print(result)
    return vector_store.id, file_id

def update_config(device_name, vs_id, file_id, config_path):
    # Read the config.py file
    with open(config_path, "r") as f:
        config_lines = f.readlines()

    # We'll look for the UserContext block with device_name="device_name"
    in_user_context = False
    device_name_found = False
    start_idx = None
    end_idx = None

    for idx, line in enumerate(config_lines):
        if "UserContext(" in line:
            in_user_context = True
            start_idx = idx
            device_name_found = False
        if in_user_context and f'device_name="{device_name}"' in line.replace(" ", ""):
            device_name_found = True
        if in_user_context and ")" in line:
            end_idx = idx
            if device_name_found:
                # Now, update file_id and vs_id in this block
                for j in range(start_idx, end_idx+1):
                    if "file_id=" in config_lines[j]:
                        config_lines[j] = f'        file_id="{file_id}",\n'
                    if "vs_id=" in config_lines[j]:
                        config_lines[j] = f'        vs_id="{vs_id}"\n'
                break
            in_user_context = False

    # Write back the updated config.py
    with open(config_path, "w") as f:
        f.writelines(config_lines)


def main():
    import sys
    if len(sys.argv) != 4:
        print("Usage: python create_vector_store.py <file_path_or_url> <vector_store_name> <config_path>")
        return
    path = sys.argv[1]
    name = sys.argv[2]
    config_path = sys.argv[3]
    
    vs_id, file_id = create_vector_store(path, name)
    print(f"Vector store ID: {vs_id}")
    print(f"File ID: {file_id}")

    # update_config(name, vs_id, file_id, config_path)

# INSERT_YOUR_CODE
    # Update config.py's user_contexts for the matching device_name

   

if __name__ == "__main__":
    main()

    

