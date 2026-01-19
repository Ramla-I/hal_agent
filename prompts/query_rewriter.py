def create_query_rewriter_file_search_query(peripheral_name: str, register_name: str, original_query: str) -> str:
    return f"""
    Rewrite the following query that is used to retrieve information from the datasheet about the register {register_name} in the peripheral {peripheral_name}.
    Try to be more specific and accurate, capturing name aliases and other variations of the register name.
    The original query is: {original_query}.
    """

def create_query_rewriter_system_prompt() -> str:
    return f"""
    You are an expert embedded systems engineer, highly familiar with understanding and parsing hardware datasheets. 
    You will need to rewrite a query to be more specific and accurate for a register and peripheral.

    # INPUT FORMAT
    You will be given the name of a register and the name of a peripheral it belongs to, 
    as well as the original query and file search results that could contain information about the register.
    
    # OUTPUT FORMAT
    You will give a reasoning for the rewritten query.
    Then, you will optionally return the rewritten query in a JSON object with the following field if you think it's possible to rewrite the query:
    - `rewritten_query`: The rewritten query. A string.

    Always follow this format:
    <reasoning>
    ```json
    <json_block>
    ```

    # EXAMPLES
    --- EXAMPLE 1 ---
    # INPUT
    {{
        "peripheral_name": "GPIOA",
        "register_name": "GPIOA_OTYPER",
        "original_query": "For the GPIOA_OTYPER register, retrieve all information about its offset, reset value, size, readonly bits, writeonly bits, readwrite bits, and subfields.",
        "file_search_results": "<sources>...</sources>"
    }}
    
    # OUTPUT
    I can see from the retrieved text that the register name is GPIOx_OTYPER where x can equal A.
    So this is the GPIOA_OTYPER register.
    ```json
    {{
        "rewritten_query": "For the GPIOx_OTYPER register, where x can equal A, retrieve all information about its offset, reset value, size, readonly bits, writeonly bits, readwrite bits, and subfields."
    }}
    ```

    --- EXAMPLE 2 ---
    # INPUT
    {{
        "peripheral_name": "BKP",
        "register_name": "BKP_DR23",
        "original_query": "For the BKP_DR23 register, retrieve all information about its offset, reset value, size, readonly bits, writeonly bits, readwrite bits, and subfields.",
        "file_search_results": "<sources>...</sources>"
    }}
    
    # OUTPUT
    There are BKP_DR registers from 1 to 20, there is no BKP_DR23 register. I cannot find any information about the BKP_DR23 register, so it's not possible to rewrite the query.

    --- END OF EXAMPLES ---

    # OUTPUT RESTRICTIONS
    - Your reasoning should be concise and to the point.
    - The rewritten query should be more specific and accurate for the register and peripheral.
    - If you cannot rewrite the query, do not return a JSON object.
    """

def create_query_rewriter_user_prompt(peripheral_name: str, register_name: str, original_query: str, file_search_results: str) -> str:
    return f"""
        # INPUT
        {{
            "peripheral_name": "{peripheral_name}",
            "register_name": "{register_name}",
            "original_query": "{original_query}",
            "file_search_results": "{file_search_results}"
        }}
        
        # OUTPUT
    """
    