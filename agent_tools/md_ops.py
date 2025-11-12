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



def remove_markdown_tables(markdown_text: str) -> str:
    """
    Removes Markdown tables from the given text.
    Handles both pipe-style and no-leading-pipe tables.
    Skips tables inside fenced code blocks (```).
    """

    # Split into lines for easier processing
    lines = markdown_text.splitlines()

    # Regex patterns
    code_fence_pattern = re.compile(r'^\s*```')  # detect start/end of code block
    table_line_pattern = re.compile(
        r'^\s*\|.*\|.*$'  # lines with pipes (common table pattern)
    )
    separator_line_pattern = re.compile(
        r'^\s*\|?[\s:\-|\+]+\|?\s*$'  # header separator line like ---|---
    )
    loose_table_pattern = re.compile(
        r'^[^`]*\|[^`]*$'  # lines with at least one pipe but not inside code
    )

    cleaned_lines = []
    inside_code_block = False
    inside_table = False

    for line in lines:
        if code_fence_pattern.match(line):
            inside_code_block = not inside_code_block
            cleaned_lines.append(line)
            continue

        if inside_code_block:
            # keep everything inside code fences untouched
            cleaned_lines.append(line)
            continue

        # Detect table-like lines
        is_table_line = (
            table_line_pattern.match(line)
            or separator_line_pattern.match(line)
            or loose_table_pattern.match(line)
        )

        if is_table_line:
            inside_table = True
            continue  # skip table line

        # If we just exited a table block and hit a non-table line, reset
        if inside_table and not is_table_line:
            inside_table = False

        # Keep normal lines
        cleaned_lines.append(line)

    return "\n".join(cleaned_lines)
