from defs import CoverageInfo, ContextRetrievalParameters

def create_coverage_improver_file_search_query(coverage_info: CoverageInfo, context_retrieval_parameters: ContextRetrievalParameters) -> str:
    return f"""
    Find information about the peripherals, registers, and fields that are missing from the agent's output.
    The coverage information shows:
    - Peripheral coverage: {coverage_info.peripheral_coverage}%
    - Register coverage: {coverage_info.register_coverage}%
    - Field coverage: {coverage_info.field_coverage}%
    
    Missing peripherals: {coverage_info.peripherals_only_in_svd}
    Missing registers: {coverage_info.registers_only_in_svd}
    Missing fields: {coverage_info.fields_only_in_svd}
    
    Help understand why these are missing and how to improve the context retrieval parameters to find them.
    """

def create_coverage_improver_system_prompt() -> str:
    return f"""
    You are an expert embedded systems engineer, highly familiar with understanding and parsing hardware datasheets. 
    You are trying to improve the coverage of a previous agent which searches for information about a register in a datasheet.
    By coverage, we mean the percentage of registers that are found in the datasheet, and the percentage of fields that are found in the registers.
    
    # INPUT INFORMATION
    You will be given the coverage information about the previous agent's output. It has the following fields:
    - `peripheral_coverage`: The percentage of peripherals that are found in the datasheet compared to the total number of peripherals in the SVD file. A float between 0 and 100.
    - `register_coverage`: The percentage of registers that are found in the datasheet from the peripherals that are present in the agent's output. A float between 0 and 100.
    - `field_coverage`: The percentage of fields that are found in the registers that are present in the agent's output. A float between 0 and 100.
    - `peripherals_only_in_svd`: A list of peripherals that are only in the SVD file.
    - `peripherals_only_in_agent_output`: A list of peripherals that are only in the agent's output.
    - `peripherals_present_in_both`: A list of peripherals that are present in both the SVD file and the agent's output.
    - `registers_only_in_svd`: A list of registers that are only in the SVD file.
    - `registers_only_in_agent_output`: A list of registers that are only in the agent's output.
    - `registers_present_in_both`: A list of registers that are present in both the SVD file and the agent's output.
    - `fields_only_in_svd`: A list of fields that are only in the SVD file.
    - `fields_only_in_agent_output`: A list of fields that are only in the agent's output.
    - `fields_present_in_both`: A list of fields that are present in both the SVD file and the agent's output.

    You will also be given the context retrieval parameters used by the previous agent. It has the following fields:
    - `context_retrieval_method`: The method used to retrieve the context. A string. it can be one of the following values:
        - `keyword_search`: The agent used keyword search to retrieve the context. It will search for the regsiter name and then retrieve all pages with that name.
        - `semantic_search`: The agent used semantic search to retrieve the context.
        - `regex`: The agent used regex to retrieve the context. This is not supported yet.
    - `pages_after_keyword`: If using keyword search, the number of pages after the keyword to retrieve. An integer.
    - `remove_tables`: If using keyword search, a boolean indicating if the tables should be removed from the context.
    - `number_embeddings`: If using semantic search, the number of embeddings to use for the context retrieval. An integer between 1 and 50.
    - `re_ranking`: If using semantic_search, a boolean indicating if the re-ranking should be used for the context retrieval.
    - `score_threshold`: IF using semantic_search, the score threshold for the context retrieval. A float between 0 and 1.
    - `query_rewrite`: A boolean indicating if the query should be rewritten for the context retrieval.
    - `vs_id`: The vector store id to use for the context retrieval. A string.
    - `regex`: If using regex, the regex pattern to use for the context retrieval. A string.    
    - `other`: If using other methods, the other method to use for the context retrieval. A string.

    Lastly, you will be given file search results about the missing peripherals, registers, and fields.
    You should use this information to understand why the previous agent's coverage is not good enough and how to improve it.

    # OUTPUT INFORMATION
    You will need to give the improved context retrieval parameters that will be used by the next agent, as well as your reasoning for the output. It should be a JSON object with the following fields:
    - `reasoning`: Your reasoning for the output. A string.
    - `context_retrieval_parameters`: The improved context retrieval parameters that will be used by the next agent. A JSON object.
    - `stop_improving`: A boolean indicating if you think the coverage is good enough and you should stop improving.

    # OUTPUT FORMAT
    You will start of by returning your reasoning for the output.
    Then, you will return the JSON object with the following fields:
    - `context_retrieval_parameters`: The improved context retrieval parameters that will be used by the next agent. A JSON object same as the input context retrieval parameters, but with the improved values.
    - `stop_improving`: A boolean indicating if you think the coverage is good enough and you should stop improving.

    Always follow this format:
    <reasoning>
    ```json
    <json_block>
    ```

    # EXAMPLE OUTPUT

    The misses strongly suggest a naming-variant problem rather than absence in the PDF. 
    In RM0041, GPIO register headings are written generically as GPIOx_CRL/GPIOx_CRH (x=A..G), 
    so a literal keyword search for GPIOA_CRL / GPIOA_CRH can fail even though the content exists in Section 7.2. 
    Similarly, UART2 is typically referred to as USART2 in STM32 reference manuals, 
    so exact-keyword retrieval can miss the correct USART section. 
    Switching to semantic search with query rewriting improves robustness to these systematic naming differences (GPIOA_* vs GPIOx_*; UART2 vs USART2), and raising the embedding count increases the chance we pull the register-map and bit/field description pages. Lowering the score threshold slightly helps include borderline matches such as per-bit field names (IDR0/IDR1) that may appear in tables/bitfield layouts rather than repeated prose. Keeping tables (remove_tables=false) remains important because field definitions (IDR0, IDR1, etc.) are often primarily presented in tabular/bitfield form.
    ```json
    {{
        "context_retrieval_parameters": {{
            "context_retrieval_method": "semantic_search",
            "pages_after_keyword": 12,
            "remove_tables": false,
            "number_embeddings": 50,
            "re_ranking": true,
            "score_threshold": 0.1,
            "query_rewrite": true,
            "vs_id": "vs_6892501067b08191ac63cc6de06ee629",
            "regex": "",
            "other": ""
        }},
        "stop_improving": false
    }}
    ```
    """

def context_was_truncated_at_any_register_prompt(truncated: bool) -> str:
    if truncated:
        return f"""
        With these context retrieval parameters, the agent had to truncate the results of the context retrieval because the context was too long.
        This means that the agent was not able to use all the context to generate the output for a register.
        The context retrieval parameters should result in good coverage, but try to avoid truncation at any register.
        """
    else:
        return f"""
        With these context retrieval parameters, the agent did not have to truncate the results of the context retrieval.
        This means that the retrieval algorithm was able to retrieve the context and pass all context to the agent, which is good.
        """

def create_coverage_improver_user_prompt(coverage_info: CoverageInfo, context_retrieval_parameters: ContextRetrievalParameters, generator_truncated_at_any_register: bool, file_search: str) -> str:
    truncation_prompt = context_was_truncated_at_any_register_prompt(generator_truncated_at_any_register)
    return f"""
        You need to improve the context retrieval parameters to increase the coverage of the previous agent's output.
        These context retrieval parameters were used by the previous agent to retrieve the context for the registers.
        {truncation_prompt}
        Keep this in mind when improving the context retrieval parameters.
        
        # INPUT
        ## COVERAGE INFORMATION
        {coverage_info}
        
        ## CONTEXT RETRIEVAL PARAMETERS
        {context_retrieval_parameters}
        
        ## FILE SEARCH RESULTS
        {file_search}
        
        # OUTPUT
    """