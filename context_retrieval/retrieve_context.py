import os
import json
import sys

# HACK, remove this once we have a proper package structure
# Add the parent directory to sys.path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)

from defs import ContextRetrievalParameters, ContextRetrievalMethod, Manufacturer
from context_retrieval.keyword_search import create_keyword_info_json, get_keyword_entry, get_page_list_for_keyword_entry
from context_retrieval.search import search_context
from agent_tools.pdf_ops import extract_pages_from_pdf
from agent_tools.md_ops import remove_markdown_tables

def retrieve_context(
    context_retrieval_parameters: ContextRetrievalParameters,
    device_name: str, 
    device_dir: str, 
    peripheral_name: str,
    register_name: str,
    manufacturer: Manufacturer,
    output_dir: str
):
    if context_retrieval_parameters.context_retrieval_method == ContextRetrievalMethod.KEYWORD_SEARCH:
        keyword_info_path = create_keyword_info_json(device_name, device_dir, manufacturer)
        search_key = f"{peripheral_name}_{register_name}"
        if manufacturer == Manufacturer.TI:
            search_key = register_name
        keyword_entry = get_keyword_entry(keyword_info_path, search_key)
    
        if keyword_entry:
            pdf_path = os.path.join(device_dir, f"{device_name}.pdf")
            extended_pages = get_page_list_for_keyword_entry(pdf_path, keyword_entry, context_retrieval_parameters.pages_after_keyword)
            datasheet_pages = extract_pages_from_pdf(pdf_path, extended_pages)
            if context_retrieval_parameters.remove_tables:
                datasheet_pages = remove_markdown_tables(datasheet_pages)
            return datasheet_pages, []
        else:
            return None, []

    elif context_retrieval_parameters.context_retrieval_method in (
        ContextRetrievalMethod.OPENAI_FILE_SEARCH,
        ContextRetrievalMethod.LOCAL_VECTOR_DB,
    ):
        query = f"For the {peripheral_name}_{register_name} register, retrieve all information about its offset, reset value, size, readonly bits, writeonly bits, readwrite bits, and subfields."
        return search_context(
            query,
            context_retrieval_parameters,
            register_filter=f"{peripheral_name}_{register_name}",
        )

    elif context_retrieval_parameters.context_retrieval_method == ContextRetrievalMethod.REGEX:
        print(f"Retrieving context from regex for {device_name} {peripheral_name} {register_name}")
        return None, []

    else:
        raise ValueError(f"Context retrieval method {context_retrieval_parameters.context_retrieval_method} not supported") 

if __name__ == "__main__":
    import sys
    
    retrieve_context(
        context_retrieval_parameters=ContextRetrievalParameters(
            context_retrieval_method=ContextRetrievalMethod.OPENAI_FILE_SEARCH,
            number_embeddings=16,
            vs_id="vs_6892501067b08191ac63cc6de06ee629",
        ),
        device_name="rm0041",
        device_dir="devices/rm0041",
        peripheral_name="TIM2",
        register_name="CR2",
        manufacturer=Manufacturer.STM,
        output_dir="context_retrieval_test"
    )
