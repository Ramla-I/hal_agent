"""
LEGACY raw-PDF vector-store creator.

Kept only because `optimization_coverage_improver/coverage_improver_optimization.py`
still imports `create_vector_store` from this module. The current preprocessing
pipeline (../pipeline.py + ../vector_store_uploader.py) replaces this entirely
with chunk-level upload + metadata enrichment.

TODO: once optimization_coverage_improver/ is migrated to the new pipeline
(or deprecated), delete this file along with the `old/` directory.
"""

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
   

if __name__ == "__main__":
    main()

    

