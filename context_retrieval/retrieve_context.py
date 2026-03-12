import os
import json
import sys

# HACK, remove this once we have a proper package structure
# Add the parent directory to sys.path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)

from defs import ContextRetrievalParameters, ContextRetrievalMethod, Manufacturer, BatchedRetrievalStrategy
from context_retrieval.keyword_search import create_keyword_info_json, get_keyword_entry, get_page_list_for_keyword_entry
from context_retrieval.search import search_context, search_context_raw
from context_retrieval.post_processing import post_process
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

def retrieve_context_for_peripheral(
    context_retrieval_parameters: ContextRetrievalParameters,
    device_name: str,
    device_dir: str,
    peripheral_name: str,
    register_names: list[str],
    manufacturer: Manufacturer,
    output_dir: str,
) -> tuple:
    """Retrieve datasheet context for an entire peripheral (multiple registers).

    For keyword search: unions page sets for all ``{peripheral}_{register}``
    entries in keyword_infos.json, deduplicates, sorts, and extracts once.

    For semantic search (OpenAI / local): builds a multi-register query and
    passes a list of register names as the metadata filter.

    Args:
        register_names: list of register names (without peripheral prefix).
            An empty list triggers "discovery mode" — the query searches for
            the peripheral name only.

    Returns:
        (datasheet_pages, embedding_ids) — same shape as ``retrieve_context()``.
    """
    if context_retrieval_parameters.context_retrieval_method == ContextRetrievalMethod.KEYWORD_SEARCH:
        keyword_info_path = create_keyword_info_json(device_name, device_dir, manufacturer)
        pdf_path = os.path.join(device_dir, f"{device_name}.pdf")

        all_pages: set[int] = set()
        if register_names:
            for reg in register_names:
                search_key = f"{peripheral_name}_{reg}"
                if manufacturer == Manufacturer.TI:
                    search_key = reg
                entry = get_keyword_entry(keyword_info_path, search_key)
                if entry:
                    pages = get_page_list_for_keyword_entry(
                        pdf_path, entry, context_retrieval_parameters.pages_after_keyword,
                    )
                    all_pages.update(pages)
        else:
            # Discovery mode — search by peripheral name only
            entry = get_keyword_entry(keyword_info_path, peripheral_name)
            if entry:
                pages = get_page_list_for_keyword_entry(
                    pdf_path, entry, context_retrieval_parameters.pages_after_keyword,
                )
                all_pages.update(pages)

        if not all_pages:
            return None, []

        sorted_pages = sorted(all_pages)
        datasheet_pages = extract_pages_from_pdf(pdf_path, sorted_pages)
        if context_retrieval_parameters.remove_tables:
            datasheet_pages = remove_markdown_tables(datasheet_pages)
        return datasheet_pages, []

    elif context_retrieval_parameters.context_retrieval_method in (
        ContextRetrievalMethod.OPENAI_FILE_SEARCH,
        ContextRetrievalMethod.LOCAL_VECTOR_DB,
    ):
        if register_names:
            strategy = context_retrieval_parameters.batched_retrieval_strategy
            if strategy == BatchedRetrievalStrategy.COMBINED_WITH_FILTER:
                return _batched_combined(
                    context_retrieval_parameters, peripheral_name, register_names,
                    use_metadata_filter=True,
                )
            elif strategy == BatchedRetrievalStrategy.COMBINED_NO_FILTER:
                return _batched_combined(
                    context_retrieval_parameters, peripheral_name, register_names,
                    use_metadata_filter=False,
                )
            elif strategy == BatchedRetrievalStrategy.PER_REGISTER_TRIMMED:
                return _batched_per_register_trimmed(
                    context_retrieval_parameters, peripheral_name, register_names,
                )
            else:
                # PER_REGISTER (default) — full union, no trim
                return _batched_per_register(
                    context_retrieval_parameters, peripheral_name, register_names,
                )
        else:
            # Discovery mode — single peripheral-level query
            query = (
                f"For the {peripheral_name} peripheral, retrieve all register "
                f"definitions, offsets, reset values, sizes, and subfield information."
            )
            return search_context(query, context_retrieval_parameters, register_filter=[])

    elif context_retrieval_parameters.context_retrieval_method == ContextRetrievalMethod.REGEX:
        print(f"Retrieving context from regex for {device_name} {peripheral_name}")
        return None, []

    else:
        raise ValueError(
            f"Context retrieval method {context_retrieval_parameters.context_retrieval_method} not supported"
        )


def _batched_per_register(
    params: ContextRetrievalParameters,
    peripheral_name: str,
    register_names: list[str],
) -> tuple:
    """Option C: per-register raw searches → union → single post_process pass.

    Each register gets its own query with number_embeddings results, same as
    unbatched. Results are deduplicated and passed through without trimming.
    """
    seen_chunks: set[str] = set()
    all_raw: list = []

    for reg in register_names:
        query = (
            f"For the {peripheral_name}_{reg} register, retrieve all "
            f"information about its offset, reset value, size, readonly "
            f"bits, writeonly bits, readwrite bits, and subfields."
        )
        reg_filter = f"{peripheral_name}_{reg}"
        raw_results = search_context_raw(
            query, params, register_filter=reg_filter,
        )
        for r in raw_results:
            chunk_key = r.text.strip()
            if chunk_key not in seen_chunks:
                seen_chunks.add(chunk_key)
                all_raw.append(r)

    if not all_raw:
        return None, []

    all_raw.sort(key=lambda r: r.score, reverse=True)
    # Don't trim — pass all deduplicated results through so each register
    # keeps its full number_embeddings worth of context (same as unbatched).
    scaled_params = params.model_copy()
    scaled_params.number_embeddings = len(all_raw)
    return post_process(all_raw, scaled_params, peripheral_name)


def _batched_per_register_trimmed(
    params: ContextRetrievalParameters,
    peripheral_name: str,
    register_names: list[str],
) -> tuple:
    """Option D: per-register queries, each trimmed to number_embeddings
    (identical retrieval to the unbatched path), then unioned, deduplicated,
    sorted by page/chunk order, and post-processed once for expansion +
    formatting.  The batched LLM call sees the same chunks each register
    would get individually, presented in document reading order.
    """
    seen_chunks: set[str] = set()
    all_trimmed: list = []

    for reg in register_names:
        query = (
            f"For the {peripheral_name}_{reg} register, retrieve all "
            f"information about its offset, reset value, size, readonly "
            f"bits, writeonly bits, readwrite bits, and subfields."
        )
        reg_filter = f"{peripheral_name}_{reg}"
        raw_results = search_context_raw(
            query, params, register_filter=reg_filter,
        )
        # Apply score threshold + trim to number_embeddings (same as post_process)
        raw_results = [r for r in raw_results if r.score >= params.score_threshold]
        raw_results.sort(key=lambda r: r.score, reverse=True)
        trimmed = raw_results[:max(1, params.number_embeddings)]

        for r in trimmed:
            chunk_key = r.text.strip()
            if chunk_key not in seen_chunks:
                seen_chunks.add(chunk_key)
                all_trimmed.append(r)

    if not all_trimmed:
        return None, []

    # Sort by page number then chunk index for coherent reading order
    all_trimmed.sort(
        key=lambda r: (r.page_number, r.metadata.get("chunk_index", 0)),
    )

    # Post-process once (expansion + formatting). Keyword boost and threshold
    # are already applied; set number_embeddings = len so trim is a no-op.
    scaled_params = params.model_copy()
    scaled_params.number_embeddings = len(all_trimmed)
    scaled_params.keyword_boost = False  # already handled above
    return post_process(all_trimmed, scaled_params, peripheral_name)


def _batched_combined(
    params: ContextRetrievalParameters,
    peripheral_name: str,
    register_names: list[str],
    use_metadata_filter: bool,
) -> tuple:
    """Options A/B: single combined query for all registers in a peripheral.

    Args:
        use_metadata_filter: If True (Option A), passes register names as metadata
            filter. _build_register_filter() in local_vector_search gracefully
            returns None for >10 registers. If False (Option B), passes empty filter.
    """
    reg_list_str = ", ".join(f"{peripheral_name}_{r}" for r in register_names)
    query = (
        f"For the {peripheral_name} peripheral registers ({reg_list_str}), "
        f"retrieve all information about offsets, reset values, sizes, and subfields."
    )

    n_embeddings = max(2 * len(register_names), 4)
    scaled_params = params.model_copy()
    scaled_params.number_embeddings = min(n_embeddings, 50)

    if use_metadata_filter:
        register_filter = [f"{peripheral_name}_{reg}" for reg in register_names]
    else:
        register_filter = []

    raw_results = search_context_raw(query, scaled_params, register_filter=register_filter)
    if not raw_results:
        return None, []

    return post_process(raw_results, scaled_params, peripheral_name)


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
