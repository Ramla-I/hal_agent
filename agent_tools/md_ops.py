import re

def extract_tables_from_section(section_content):
    """
    Extract all tables from a given section.
    
    Args:
        section_content (str): The full markdown content
    
    Returns:
        list: List of table strings
    """
    
    # Find all tables in the section
    # Tables start with a line containing | and end with a blank line or another header
    tables = []
    
    # Split by lines that start with # (headers) to separate content blocks
    blocks = re.split(r'^# ', section_content, flags=re.MULTILINE)
    
    for block in blocks:
        if not block.strip():
            continue
            
        # Look for table patterns in each block
        lines_in_block = block.split('\n')
        current_table = []
        in_table = False
        
        for line in lines_in_block:
            if '|' in line and line.strip():
                # This looks like a table line
                if not in_table:
                    in_table = True
                current_table.append(line)
            elif in_table:
                # End of table
                if current_table:
                    table_text = '\n'.join(current_table)
                    if table_text.strip():
                        tables.append(table_text)
                current_table = []
                in_table = False
        
        # Don't forget the last table if we're still in one
        if in_table and current_table:
            table_text = '\n'.join(current_table)
            if table_text.strip():
                tables.append(table_text)
    
    return tables


def find_pages_with_tables(pdf_path, pages):
    """
    Given a PDF path and a list of page numbers, convert each page to markdown,
    check if it contains a markdown table, and return a list of pages that contain tables.

    Args:
        pdf_path (str): Path to the PDF file.
        pages (list of int): List of page numbers (1-based).

    Returns:
        list of int: List of page numbers that contain tables.
    """
    from agent_tools.pdf_ops import pdf_page_to_markdown  # Assume this exists
    pages_with_tables = []
    for page_num in pages:
        try:
            md_content = pdf_page_to_markdown(pdf_path, page_num)
            tables = extract_tables_from_section(md_content)
            if tables and len(tables) > 0:
                pages_with_tables.append(page_num)
        except Exception as e:
            # Optionally log or print error
            continue
    return pages_with_tables
