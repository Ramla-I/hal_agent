import os
import json
import sys

# HACK, remove this once we have a proper package structure
# Add the parent directory to sys.path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)

from defs import ContextRetrievalParameters, ContextRetrievalMethod, Manufacturer
from context_retrieval.keyword_search import create_keyword_info_json, get_keyword_entry, get_page_list_for_keyword_entry
from context_retrieval.semantic_search import search_vector_store, format_results
from agent_tools.pdf_ops import extract_pages_from_pdf
from agent_tools.md_ops import remove_markdown_tables


def retrieve_context(
    context_retrieval_parameters: ContextRetrievalParameters,
    device_name: str, 
    device_dir: str, 
    peripheral_name: str,
    register_name: str,
    manufacturer: Manufacturer
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
            return datasheet_pages
        else:
            return None

    elif context_retrieval_parameters.context_retrieval_method == ContextRetrievalMethod.SEMANTIC_SEARCH:
        query = f"For the {peripheral_name}_{register_name} register, retrieve all information about its offset, reset value, size, readonly bits, writeonly bits, readwrite bits, and subfields."
        if context_retrieval_parameters.number_embeddings < 1: 
            context_retrieval_parameters.number_embeddings = 1
        elif context_retrieval_parameters.number_embeddings > 50:
            context_retrieval_parameters.number_embeddings = 50
        results = search_vector_store(query, context_retrieval_parameters.vs_id, context_retrieval_parameters.number_embeddings, context_retrieval_parameters.re_ranking, context_retrieval_parameters.score_threshold)
        if len(results.data) == 0:
            return None
        else:
            formatted_results = format_results(results)
            return formatted_results

    elif context_retrieval_parameters.context_retrieval_method == ContextRetrievalMethod.REGEX:
        print(f"Retrieving context from regex for {device_name} {peripheral_name} {register_name}")
        return None

    else:
        raise ValueError(f"Context retrieval method {context_retrieval_parameters.context_retrieval_method} not supported") 

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 4:
        print(f"Usage: {sys.argv[0]} <device_name> <device_dir> <output_dir> <peripheral_name> <register_name>")
        sys.exit(1)
    device_name = sys.argv[1]
    device_dir = sys.argv[2]
    output_dir = sys.argv[3]
    peripheral_name = sys.argv[4]
    register_name = sys.argv[5]
    retrieve_context( device_name, device_dir, output_dir, peripheral_name, register_name)

