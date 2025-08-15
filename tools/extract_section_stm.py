import os
import pymupdf4llm
import tools
import tools.extract_section_intel

def extract_section_file(folder_path, section_name, tables_only=False):
    """
    Extract a section from an STM32 markdown datasheet
    
    Args:
        file_path: Path to the folder with the markdown files
        section_name: Name of the section to extract
        tables_only: If True, only extract tables from the section
        
    Returns:
        String containing the extracted section content
    """
    if not os.path.exists(folder_path):
        raise FileNotFoundError(f"Folder {folder_path} not found")
    
    # Search for file containing section_name in its name
    matching_files = []
    for filename in os.listdir(folder_path):
        if section_name.lower() in filename.lower() and filename.endswith('.md'):
            matching_files.append(filename)
            
    if not matching_files:
        raise FileNotFoundError(f"No files found containing '{section_name}'")
        
    if len(matching_files) > 1:
        # If multiple matches, take first one but warn
        print(f"Warning: Multiple files found matching '{section_name}', using {matching_files[0]}")
        
    file_path = os.path.join(folder_path, matching_files[0])

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        section_content = content
        
    if tables_only:
        section_content = tools.extract_section_intel.extract_tables_from_section(content)
        
        
    return section_content

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Extract section from STM32 markdown datasheet')
    parser.add_argument('folder', help='Path to folder containing markdown files')
    parser.add_argument('section', help='Name of section to extract')
    parser.add_argument('--tables-only', action='store_true', help='Extract only tables from the section')
    args = parser.parse_args()

    try:
        result = extract_section_file(args.folder, args.section, args.tables_only)
        print(result)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    main()
