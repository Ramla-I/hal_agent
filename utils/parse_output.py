
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


def get_json_array_from_response(response: str) -> list | None:
    """Parse a JSON array from the response text.

    Returns a list of dicts. If the JSON block contains a single object
    instead of an array, wraps it in a list for backward compatibility.

    If the JSON is truncated (e.g. model hit output token limit mid-array),
    attempts to salvage fully-formed objects by progressively trimming from
    the end and re-parsing.

    Returns None if no valid JSON is found.
    """
    import json

    json_block = get_json_block_from_response(response)
    if json_block is None:
        return None
    try:
        parsed = json.loads(json_block)
    except json.JSONDecodeError:
        # Attempt to salvage truncated JSON arrays.
        # Walk backwards to find the last complete object boundary "},".
        salvaged = _salvage_truncated_json_array(json_block)
        if salvaged is not None:
            return salvaged
        return None
    if isinstance(parsed, list):
        return parsed
    if isinstance(parsed, dict):
        return [parsed]
    return None


def _salvage_truncated_json_array(json_block: str) -> list | None:
    """Try to recover complete objects from a truncated JSON array.

    Looks for the last ``}`` that, when followed by ``]``, produces a valid
    JSON array. This handles the common case where the model ran out of
    output tokens mid-object.
    """
    import json

    stripped = json_block.rstrip()
    if not stripped.startswith("["):
        return None

    # Find the last '},' or '}' and try closing the array there
    pos = len(stripped)
    while pos > 1:
        pos = stripped.rfind("}", 0, pos)
        if pos == -1:
            break
        candidate = stripped[: pos + 1].rstrip().rstrip(",") + "\n]"
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, list) and parsed:
                return parsed
        except json.JSONDecodeError:
            pass
    return None