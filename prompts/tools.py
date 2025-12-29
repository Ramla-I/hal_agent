calculate_address_offset_tool_description = f"""
- calculate_address_offset: 
    - Description: Calculate the address offset of a register when it is given as a formula or as a range.
    - Parameters:
        - base_address_in_hex: The base address of the register in hexadecimal.
        - start_register_number: The starting register number.
        - register_number: The register number.
        - register_size_in_bytes: The size of the register in bytes.
    - Returns:
        - address_offset_in_hex: The address offset of the register in hexadecimal.
    - Example:
        The address offset for BKP_DRx(x=1..20)is given in the datasheet as:
            Address offset: 0x04 to 0x28, 0x40 to 0x64
        You can use the `calculate_address_offset` tool to calculate the address offset for each register in the range 1 to 20.
        - For BKP_DR1 :
            base_address_in_hex = 0x04
            start_register_number = 1
            register_number = 1
            register_size_in_bytes = 4
            - you would call calculate_address_offset(0x04, 1, 1, 4). The result would be 0x04.
        - For BKP_DR12 :
            base_address_in_hex = 0x40 because it seems registers 1 to 10 start at 0x04 and the next 10 registers (11 to 20) start at 0x40.
            start_register_number = 11
            register_number = 12
            register_size_in_bytes = 4
            - you would call calculate_address_offset(0x40, 11, 12, 4). The result would be 0x08.
        - For BKP_DR35, you would detect that there is no 35th register as the range is only from 1 to 20, 
        so you would make no function call and return no output for BKP_DR35 beyond a reasoning line stating that there is no 35th register.
"""

get_keyword_seach_code_tool_description = f"""
- get_keyword_seach_code: 
    - Description: Get the code for the keyword search.
    - Parameters:
        - None
    - Returns:
        - keyword_search_code: The code for the keyword search.
    - Example:
        - You would call get_keyword_seach_code(). The result would be the code for the keyword search.
"""

get_semantic_search_code_tool_description = f"""
- get_semantic_search_code: 
    - Description: Get the code for the semantic search.
    - Parameters:
        - None
    - Returns:
        - semantic_search_code: The code for the semantic search.
    - Example:
        - You would call get_semantic_search_code(). The result would be the code for the semantic search.
""" 