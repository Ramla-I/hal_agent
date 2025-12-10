import os
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.request import urlretrieve
from typing import Optional
import requests
import time # Import the time library for potential debugging

def download_pdf(url, filename):
    # Define custom headers to mimic a web browser
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
    }
    
    # Define a timeout value (in seconds)
    TIMEOUT = 10 

    try:
        print(f"Attempting to download from {url} with a {TIMEOUT} second timeout...")
        start_time = time.time() # For debugging the duration

        # Send a GET request with headers, stream=True, and a timeout
        response = requests.get(url, headers=headers, stream=True, timeout=TIMEOUT)
        response.raise_for_status()  # Raise an exception for bad status codes

        end_time = time.time()
        print(f"Connection successful in {end_time - start_time:.2f} seconds. Status code: {response.status_code}")

        # Open the file in binary write mode and write the content in chunks
        with open(filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"Successfully downloaded '{filename}'")

    except requests.exceptions.Timeout as e:
        print(f"Error downloading PDF: The request timed out after {TIMEOUT} seconds. The server might be throttling the connection or silently dropping requests.")
        print(f"Exception details: {e}")
    except requests.exceptions.RequestException as e:
        print(f"Error downloading PDF: A connection error occurred.")
        print(f"Exception details: {e}")


def process_reference_manuals(xml_path: str, svd_source_folder: str, output_base_dir: Optional[str] = None) -> None:
    """
    Process reference manuals from an XML file.
    
    For each reference manual:
    - Creates a folder with the RM name (lowercase)
    - Downloads the PDF from the URL and saves it as rm_name.pdf
    - Creates a subfolder named 'svd' and copies SVD files from the source folder
    - Prefers .patched versions of SVD files if they exist
    
    Args:
        xml_path: Path to the XML file containing reference manual entries
        svd_source_folder: Path to the folder containing SVD files to copy
        output_base_dir: Base directory where RM folders will be created. 
                        If None, uses the directory containing the XML file.
    """
    # Parse XML file
    tree = ET.parse(xml_path)
    root = tree.getroot()
    
    # Determine output base directory
    if output_base_dir is None:
        output_base_dir = os.path.dirname(os.path.abspath(xml_path))
    else:
        output_base_dir = os.path.abspath(output_base_dir)
    
    # Ensure SVD source folder exists
    svd_source_folder = os.path.abspath(svd_source_folder)
    if not os.path.isdir(svd_source_folder):
        raise ValueError(f"SVD source folder does not exist: {svd_source_folder}")
    
    # Process each reference manual
    for rm_elem in root.findall('reference_manual'):
        rm_name = rm_elem.get('rm')
        if not rm_name or rm_name == 'UNKNOWN':
            print(f"Skipping reference manual with invalid or UNKNOWN RM name")
            continue
        
        # Create folder name (lowercase)
        rm_folder_name = rm_name.lower()
        rm_folder_path = os.path.join(output_base_dir, rm_folder_name)
        
        # Skip if folder already exists
        if os.path.exists(rm_folder_path):
            print(f"Folder {rm_folder_name} already exists, skipping...")
            continue
        
        # Create the folder
        os.makedirs(rm_folder_path, exist_ok=True)
        print(f"Created folder: {rm_folder_name}")
        
        # Download PDF if URL exists
        url_elem = rm_elem.find('url')
        if url_elem is not None and url_elem.text:
            pdf_url = url_elem.text.strip()
            pdf_filename = f"{rm_folder_name}.pdf"
            pdf_path = os.path.join(rm_folder_path, pdf_filename)
            
            try:
                print(f"Downloading PDF from {pdf_url}...")
                download_pdf(pdf_url, pdf_path)
                print(f"Downloaded PDF: {pdf_filename}")
            except Exception as e:
                print(f"Error downloading PDF for {rm_name}: {e}")
        
        # Create svd subfolder
        svd_folder_path = os.path.join(rm_folder_path, 'svd')
        os.makedirs(svd_folder_path, exist_ok=True)
        
        # Copy SVD files
        svd_elem = rm_elem.find('svd')
        if svd_elem is not None:
            for svd_file_elem in svd_elem.findall('svd_file'):
                svd_filename = svd_file_elem.text
                if not svd_filename or not svd_filename.strip():
                    continue
                
                svd_filename = svd_filename.strip()
                
                # Check for patched version first
                patched_filename = f"{svd_filename}.patched"
                patched_source_path = os.path.join(svd_source_folder, patched_filename)
                original_source_path = os.path.join(svd_source_folder, svd_filename)
                
                destination_path = os.path.join(svd_folder_path, svd_filename)
                
                if os.path.exists(patched_source_path):
                    # Copy patched version
                    shutil.copy2(patched_source_path, destination_path)
                    print(f"Copied patched SVD: {patched_filename}")
                elif os.path.exists(original_source_path):
                    # Copy original version
                    shutil.copy2(original_source_path, destination_path)
                    print(f"Copied SVD: {svd_filename}")
                else:
                    print(f"Warning: SVD file not found: {svd_filename} (checked both original and .patched)")
        
        print(f"Completed processing {rm_name}\n")


if __name__ == "__main__":
    # Example usage
    xml_path = "/Users/ramla/Projects/hal_agent/devices/stm/rm_device_mapping.xml"
    svd_source_folder = "/Users/ramla/Projects/stm32-rs/svd"  # Update this path
    process_reference_manuals(xml_path, svd_source_folder)

