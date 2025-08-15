import xml.etree.ElementTree as ET
import re
from pydantic import BaseModel, Field
import os
import openai

class RegisterSection(BaseModel):
    name: str = Field(description="The name of the register")
    header_line: str = Field(description="The line contents where the register section starts")
    end_line: str = Field(description="The line contents where the register section ends")

class RegisterSections(BaseModel):
    register_sections: list[RegisterSection] = Field(description="The list of register sections")

def find_register_sections(svd_path, peripheral_name, sections_directory):
    """
    Finds the given peripheral in an SVD file, gets all its registers, and then in the markdown file
    finds the line numbers where the subsection for each register starts.

    Args:
        svd_path (str): Path to the SVD XML file.
        peripheral_name (str): Name of the peripheral to search for.
        markdown_path (str): Path to the markdown file.

    Returns:
        dict: A dictionary mapping register names to the line number (0-based) where their section starts in the markdown file.
    """
    # Parse the SVD file
    tree = ET.parse(svd_path)
    root = tree.getroot()

    # SVD files use the namespace, so we need to handle that
    ns = ""
    if root.tag.startswith("{"):
        ns = root.tag.split("}")[0] + "}"

    # Find the peripheral
    peripheral = None
    for p in root.findall(f".//{ns}peripheral"):
        name_elem = p.find(f"{ns}name")
        if name_elem is not None and name_elem.text and name_elem.text.strip().lower() == peripheral_name.lower():
            peripheral = p
            break

    if peripheral is None:
        raise ValueError(f"Peripheral '{peripheral_name}' not found in SVD file.")

    # Get all register names for the peripheral
    registers = []
    registers_elem = peripheral.find(f"{ns}registers")
    if registers_elem is not None:
        for reg in registers_elem.findall(f"{ns}register"):
            reg_name_elem = reg.find(f"{ns}name")
            if reg_name_elem is not None and reg_name_elem.text:
                registers.append(reg_name_elem.text.strip())

    if not registers:
        raise ValueError(f"No registers found for peripheral '{peripheral_name}' in SVD file.")
    print(registers)
    # Find the markdown file in sections_directory that contains the peripheral name in its filename
    markdown_file = None
    for fname in os.listdir(sections_directory):
        if fname.lower().endswith(".md") and peripheral_name.lower() in fname.lower():
            markdown_file = os.path.join(sections_directory, fname)
            break

    if markdown_file is None:
        raise FileNotFoundError(f"No markdown file found in '{sections_directory}' containing '{peripheral_name}' in its name.")
    
    # Read the markdown file
    print(f"Using markdown file: {markdown_file}")
    with open(markdown_file, "r", encoding="utf-8") as f:
        markdown_text = f.read()

    # Prepare the prompt for OpenAI
    prompt = f"""
        You are given a markdown file containing documentation for the peripheral '{peripheral_name}'. 
        Here is the content of the markdown file:

        ---
        {markdown_text}
        ---

        The following is a list of register names for this peripheral:
        {registers}

        For each register, find the section in the markdown file that documents it. 
        For each such section, return an object in the following format:

        RegisterSection:
        register_name: <register name>
        header_line: <line contents where the section for this register starts>
        end_line: <line contents where the section for this register ends>

        Return a list of RegisterSection objects, one for each register that is documented in the markdown file. 
        If a register is not found, omit it from the list. 
        Return only valid JSON, as a list of objects with 'register_name' and 'line_number' fields.
    """

    # Call OpenAI API (assumes OPENAI_API_KEY is set)
    client = openai.OpenAI()
    response = client.chat.completions.parse(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an assistant that extracts structured data from technical documentation."},
            {"role": "user", "content": prompt}
        ],
        temperature=0,
        response_format=RegisterSections
    )

    # Parse the response
    import json
    try:
        # The response content should be a JSON list of RegisterSection objects
        result = json.loads(response.choices[0].message.content)
    except Exception as e:
        raise RuntimeError(f"Failed to parse OpenAI response: {e}\nRaw response: {response.choices[0].message.content}")

    # After obtaining the result, ask ChatGPT if there's a regex pattern that can be used to find the start and end of a section for each register.
    # We'll use the same markdown_text and registers as context.
    # This is a best-effort prompt to ChatGPT, not a guarantee of a perfect answer.

    # Prepare a follow-up prompt for ChatGPT
    followup_prompt = f"""
        Given the following JSON entries listing the lines of the section  for the peripheral '{peripheral_name}':
        ---
        {markdown_text}
        ---

        And the following list of register names:
        {registers}

        For each register, is there a regex pattern (or set of patterns) that could be used to reliably find the start and end of the section documenting that register in the markdown file?
        If so, provide the regex pattern(s) for each register, and explain briefly how they work.
        If not, explain why not for any register where it's not possible.
        Return your answer as a JSON object mapping each register name to either a regex pattern (or patterns) and explanation, or to an explanation of why a regex is not possible.
    """

    # Call OpenAI API for the follow-up question
    followup_response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an expert in text processing and regular expressions, especially for technical documentation."},
            {"role": "user", "content": followup_prompt}
        ],
        temperature=0
    )

    # Parse the follow-up response
    try:
        followup_content = followup_response.choices[0].message.content
        # Try to extract JSON from the response
        import json
        import re
        # Extract JSON object from the response (in case there's explanation text)
        match = re.search(r"\{.*\}", followup_content, re.DOTALL)
        if match:
            regex_patterns = json.loads(match.group(0))
        else:
            regex_patterns = {"raw_response": followup_content}
    except Exception as e:
        regex_patterns = {"error": f"Failed to parse regex patterns: {e}", "raw_response": followup_response.choices[0].message.content}

    # Attach the regex_patterns to the result for further inspection
    result_with_regex = {
        "register_sections": result,
        "regex_patterns": regex_patterns
    }
    return result


def main():
    import argparse
    import os

    parser = argparse.ArgumentParser(description="Find register section line numbers in a peripheral markdown file.")
    parser.add_argument("svd_path", help="Path to the SVD file")
    parser.add_argument("peripheral_name", help="Peripheral name")
    parser.add_argument("sections_directory", help="Path to the directory containing the markdown files")
    args = parser.parse_args()

    result = find_register_sections(args.svd_path, args.peripheral_name, args.sections_directory)
    import json
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
