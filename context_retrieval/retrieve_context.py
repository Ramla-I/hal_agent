import os
import json
import sys

# HACK, remove this once we have a proper package structure
# Add the parent directory to sys.path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)

from defs import ContextRetrievalParameters, ContextRetrievalMethod, Manufacturer
import config
from context_retrieval.keyword_search import create_keyword_info_json, get_keyword_entry, get_page_list_for_keyword_entry
from context_retrieval.semantic_search import (
    search_vector_store, format_results, extract_embedding_ids,
    format_results_with_expansion
)
from context_retrieval.chunk_index import get_chunk_index
from context_retrieval.local_vector_search import search_local_vector_db
from agent_tools.pdf_ops import extract_pages_from_pdf
from agent_tools.md_ops import remove_markdown_tables
from core.s3_query_rewriter import run_query_rewriter

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

    elif context_retrieval_parameters.context_retrieval_method == ContextRetrievalMethod.SEMANTIC_SEARCH:
        query = f"For the {peripheral_name}_{register_name} register, retrieve all information about its offset, reset value, size, readonly bits, writeonly bits, readwrite bits, and subfields."
        if context_retrieval_parameters.number_embeddings < 1:
            context_retrieval_parameters.number_embeddings = 1
        elif context_retrieval_parameters.number_embeddings > 50:
            context_retrieval_parameters.number_embeddings = 50

        # Check both config.QUERY_REWRITE flag and context_retrieval_parameters.query_rewrite
        if config.QUERY_REWRITE and context_retrieval_parameters.query_rewrite:
            query = run_query_rewriter(query, peripheral_name, register_name, context_retrieval_parameters.vs_id, output_dir)

        results = search_vector_store(query, context_retrieval_parameters.vs_id, context_retrieval_parameters.number_embeddings, context_retrieval_parameters.re_ranking, context_retrieval_parameters.score_threshold)
        if len(results.data) == 0:
            return None, []
        else:
            # Check if chunk expansion is enabled and chunk_index_path is configured
            chunk_index = None
            expansion_enabled = context_retrieval_parameters.chunk_expansion_enabled
            if expansion_enabled and context_retrieval_parameters.chunk_index_path:
                try:
                    chunk_index = get_chunk_index(context_retrieval_parameters.chunk_index_path)
                except FileNotFoundError:
                    # Fall back to no expansion if chunk index not found
                    expansion_enabled = False

            # Format results with optional chunk expansion
            if chunk_index is not None and expansion_enabled:
                formatted_results = format_results_with_expansion(
                    results,
                    chunk_index=chunk_index,
                    pages_after=context_retrieval_parameters.pages_after,
                    expansion_enabled=True,
                    table_pages_only=context_retrieval_parameters.expand_table_pages_only
                )
            else:
                formatted_results = format_results(results)

            embedding_ids = extract_embedding_ids(results)
            return formatted_results, embedding_ids

    elif context_retrieval_parameters.context_retrieval_method == ContextRetrievalMethod.LOCAL_VECTOR_DB:
        query = f"For the {peripheral_name}_{register_name} register, retrieve all information about its offset, reset value, size, readonly bits, writeonly bits, readwrite bits, and subfields."
        if context_retrieval_parameters.number_embeddings < 1:
            context_retrieval_parameters.number_embeddings = 1

        if config.QUERY_REWRITE and context_retrieval_parameters.query_rewrite:
            query = run_query_rewriter(query, peripheral_name, register_name,
                                       context_retrieval_parameters.local_db_name, output_dir)

        return search_local_vector_db(
            query=query,
            db_name=context_retrieval_parameters.local_db_name,
            n_results=context_retrieval_parameters.number_embeddings,
            keyword_boost=context_retrieval_parameters.keyword_boost and context_retrieval_parameters.number_embeddings > 1,
            reranker_type=context_retrieval_parameters.reranker_type,
            score_threshold=context_retrieval_parameters.score_threshold,
            db_path=context_retrieval_parameters.local_db_path,
            embedding_provider=context_retrieval_parameters.local_embedding_provider,
            register_filter=f"{peripheral_name}_{register_name}" if context_retrieval_parameters.metadata_filter_enabled else "",
            chunk_index_path=context_retrieval_parameters.chunk_index_path if context_retrieval_parameters.chunk_expansion_enabled else "",
            pages_after=context_retrieval_parameters.pages_after,
            table_pages_only=context_retrieval_parameters.expand_table_pages_only,
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
            context_retrieval_method=ContextRetrievalMethod.SEMANTIC_SEARCH,
            number_embeddings=16,
            query_rewrite=True,
            vs_id="vs_6892501067b08191ac63cc6de06ee629",
        ),
        device_name="rm0041",
        device_dir="devices/rm0041",
        peripheral_name="TIM2",
        register_name="CR2",
        manufacturer=Manufacturer.STM,
        output_dir="context_retrieval_test"
    )
