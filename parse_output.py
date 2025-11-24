def get_json_block_from_response(response: str) -> tuple[str, str]:
    extracted_json_blocks = []
    reasoning = ""
    if "```json" in response:
        # Split and extract all text blocks between ```json and ```

        idx = response.find("```json")
        reasoning = response[:idx].strip()

        split_blocks = response.split("```json")
        for block in split_blocks[1:]:
            # Only find up to the next ```
            end_idx = block.find("```")
            if end_idx != -1:
                extracted = block[:end_idx].strip()
            else:
                extracted = block.strip()
            if extracted:
                extracted_json_blocks.append(extracted)
    if extracted_json_blocks:   
        return extracted_json_blocks[0], reasoning
    return None