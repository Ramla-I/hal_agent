from pinecone import Pinecone
import os   
from PyPDF2 import PdfWriter,PdfReader

client = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))


def create_index(name):
    if not client.has_index(name):
        client.create_index_for_model(
            name=name,
            cloud="aws",
            region="us-east-1",
            embed={
                "model":"llama-text-embed-v2",
                "field_map":{"text": "chunk_text"}
            }
        )
        print(f"Created index: {name}")
    
    else:
        print(f"Index {name} already exists")
    
def chunk_file_and_upsert(index_name,file_path):
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"The file at {pdf_path} does not exist.")
    
    records = []
    total_records = 0
    with open(file_path, 'rb') as file:
        reader = PdfReader(file)

        total_pages = len(reader.pages)

        for page_num in range(total_pages):
            page_text = reader.pages[page_num].extract_text()
            records.append({
                "_id": f"{page_num}",
                "chunk_text": page_text
            })

            if len(records) == 96:
                upsert_records(index_name, records)
                total_records += len(records)
                records = []
     
    print(f"Chunked {len(records)} records from {file_path}")
    return records

def upsert_records(index_name, records):
    client.Index(index_name).upsert_records("__default__", records)
    print(f"Upserted {len(records)} records to index {index_name}")


# def update_config(device_name, vs_id, file_id, config_path):
#     # Read the config.py file
#     with open(config_path, "r") as f:
#         config_lines = f.readlines()

#     # We'll look for the UserContext block with device_name="device_name"
#     in_user_context = False
#     device_name_found = False
#     start_idx = None
#     end_idx = None

#     for idx, line in enumerate(config_lines):
#         if "UserContext(" in line:
#             in_user_context = True
#             start_idx = idx
#             device_name_found = False
#         if in_user_context and f'device_name="{device_name}"' in line.replace(" ", ""):
#             device_name_found = True
#         if in_user_context and ")" in line:
#             end_idx = idx
#             if device_name_found:
#                 # Now, update file_id and vs_id in this block
#                 for j in range(start_idx, end_idx+1):
#                     if "file_id=" in config_lines[j]:
#                         config_lines[j] = f'        file_id="{file_id}",\n'
#                     if "vs_id=" in config_lines[j]:
#                         config_lines[j] = f'        vs_id="{vs_id}"\n'
#                 break
#             in_user_context = False

#     # Write back the updated config.py
#     with open(config_path, "w") as f:
#         f.writelines(config_lines)


def main():
    import sys
    if len(sys.argv) != 3:
        print("Usage: python create_vector_store_pinecone.py <file_path> <index_name>")
        return
    file_path = sys.argv[1]
    index_name = sys.argv[2]

    create_index(index_name)
    records = chunk_file_and_upsert(index_name, file_path)
    
if __name__ == "__main__":
    main()

    

