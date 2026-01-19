
def get_reasoning_from_response(response: str) -> tuple[str, str]:
    """
    Returns a tuple (reasoning, rest_of_response) where reasoning is everything up to the first line starting with ```
    """
    lines = response.splitlines(keepends=True)
    reasoning_lines = []
    rest_lines = []
    found_codeblock = False
    for idx, line in enumerate(lines):
        if line.lstrip().startswith("```"):
            found_codeblock = True
            rest_lines = lines[idx:]
            break
        reasoning_lines.append(line)
    reasoning = "".join(reasoning_lines).rstrip("\n")
    rest = "".join(rest_lines)
    return reasoning, rest

def get_function_calls_from_response(response: str) -> str | None:
    """
    Returns a list of function calls from the response.
    """
    if "```function_call" in response:
        # Split and extract all text blocks between ```function_call and ```
        split_blocks = response.split("```function_call")
        # Find the next ```
        block = split_blocks[1]
        end_idx = block.find("```")
        if end_idx != -1:
            return block[:end_idx].strip()
        else:
            return block.strip()
    return None

def get_json_block_from_response(response: str) -> str | None:
    if "```json" in response:
        # Split and extract all text blocks between ```json and ```
        split_blocks = response.split("```json")
        # Find the next ```
        block = split_blocks[1]
        end_idx = block.find("```")
        if end_idx != -1:
            return block[:end_idx].strip()
        else:
            return block.strip()
    return None