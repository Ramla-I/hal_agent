import os
import re
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

def generic_peripheral_stem(name: str) -> str | None:
    """Strip a trailing instance number to the generic stem (i2c2 -> i2c,
    usart8 -> usart, tim16 -> tim). Returns None when there's no trailing digit
    or stripping leaves nothing. Lettered instances (GPIOA) are out of scope."""
    m = re.match(r"^(.*?)(\d+)$", name)
    if not m:
        return None
    stem = m.group(1)
    return stem or None


def _resolve_oe_chunks(device_dir: str, device_name: str) -> tuple[str, str]:
    """Resolve chunks directory and index CSV for OpenEvolve retrieval."""
    # Extract manufacturer from device_dir (e.g. "devices/stm/rm0041" → "stm")
    parts = device_dir.rstrip("/").split("/")
    mfr = parts[-2] if len(parts) >= 2 else "stm"
    chunks_dir = os.path.join("chunked_datasheets", mfr, device_name, "chunks", "md")
    chunks_index_csv = os.path.join(chunks_dir, "chunks_index.csv")
    return chunks_dir, chunks_index_csv


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

        # Fall back to the generic peripheral stem (i2c2_cr1 -> i2c_cr1) when the
        # instance-specific key isn't documented (multi-instance peripherals).
        if not keyword_entry and manufacturer != Manufacturer.TI:
            stem = generic_peripheral_stem(peripheral_name)
            if stem:
                keyword_entry = get_keyword_entry(keyword_info_path, f"{stem}_{register_name}")

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
        # Hint the generic form so embeddings also match a generically-documented
        # section (e.g. I2Cx_CR1 / I2C_CR1) for a numbered instance.
        stem = generic_peripheral_stem(peripheral_name)
        if stem and stem != peripheral_name:
            query += f" This register may be documented generically as {stem}x_{register_name} or {stem}_{register_name}."
        return search_context(
            query,
            context_retrieval_parameters,
            register_filter=f"{peripheral_name}_{register_name}",
        )

    elif context_retrieval_parameters.context_retrieval_method == ContextRetrievalMethod.OPENEVOLVE:
        from context_retrieval.openevolve_search import search_openevolve
        chunks_dir, chunks_index_csv = _resolve_oe_chunks(device_dir, device_name)
        # search_openevolve returns the canonical <sources>...</sources> XML
        # with one <result page='N'> per OE page block — same shape as the
        # batched OE path and post_processing.format_results.
        formatted, embedding_ids = search_openevolve(
            peripheral_name, register_name, chunks_dir, chunks_index_csv,
            program_path=context_retrieval_parameters.oe_program_path,
        )
        # Fall back to the generic peripheral stem when the instance yields nothing.
        if not formatted:
            stem = generic_peripheral_stem(peripheral_name)
            if stem and stem != peripheral_name:
                formatted, embedding_ids = search_openevolve(
                    stem, register_name, chunks_dir, chunks_index_csv,
                    program_path=context_retrieval_parameters.oe_program_path,
                )
        if not formatted:
            return None, []
        return formatted, embedding_ids

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
            return _batched_retrieve(
                context_retrieval_parameters, peripheral_name, register_names,
            )
        else:
            # Discovery mode — single peripheral-level query
            query = (
                f"For the {peripheral_name} peripheral, retrieve all register "
                f"definitions, offsets, reset values, sizes, and subfield information."
            )
            return search_context(query, context_retrieval_parameters, register_filter=[])

    elif context_retrieval_parameters.context_retrieval_method == ContextRetrievalMethod.OPENEVOLVE:
        from context_retrieval.openevolve_search import search_openevolve_for_peripheral
        chunks_dir, chunks_index_csv = _resolve_oe_chunks(device_dir, device_name)
        return search_openevolve_for_peripheral(
            peripheral_name, register_names, chunks_dir, chunks_index_csv,
            program_path=context_retrieval_parameters.oe_program_path,
        )

    elif context_retrieval_parameters.context_retrieval_method == ContextRetrievalMethod.REGEX:
        print(f"Retrieving context from regex for {device_name} {peripheral_name}")
        return None, []

    else:
        raise ValueError(
            f"Context retrieval method {context_retrieval_parameters.context_retrieval_method} not supported"
        )


_PER_REGISTER_QUERY_TEMPLATE = (
    "For the {peripheral}_{register} register, retrieve all "
    "information about its offset, reset value, size, readonly "
    "bits, writeonly bits, readwrite bits, and subfields."
)
_COMBINED_QUERY_TEMPLATE = (
    "For the {peripheral} peripheral registers ({reg_list}), "
    "retrieve all information about offsets, reset values, sizes, and subfields."
)


def _batched_retrieve(
    params: ContextRetrievalParameters,
    peripheral_name: str,
    register_names: list[str],
) -> tuple:
    """Batched semantic retrieval across multiple registers in one peripheral.

    Dispatches on ``params.batched_retrieval_strategy``:

      ``COMBINED_WITH_FILTER`` (sA): one query covering all registers, with the
          register-name list passed as a metadata filter
          (``_build_register_filter()`` in local_vector_search gracefully
          returns None for >10 registers, falling back to unfiltered).
      ``COMBINED_NO_FILTER`` (sB): one combined query, no metadata filter.
      ``PER_REGISTER`` (sC, default): one query per register, all raw results
          unioned and deduped, sorted by score before post_process.
      ``PER_REGISTER_TRIMMED`` (sD): one query per register, each result list
          score-thresholded and trimmed to ``number_embeddings`` (matching the
          unbatched code path), then unioned, deduped, and sorted by document
          order; keyword boost is disabled in post_process so the document
          order survives.
    """
    strategy = params.batched_retrieval_strategy

    if strategy in (
        BatchedRetrievalStrategy.COMBINED_WITH_FILTER,
        BatchedRetrievalStrategy.COMBINED_NO_FILTER,
    ):
        reg_list_str = ", ".join(f"{peripheral_name}_{r}" for r in register_names)
        query = _COMBINED_QUERY_TEMPLATE.format(
            peripheral=peripheral_name, reg_list=reg_list_str,
        )
        scaled_params = params.model_copy()
        scaled_params.number_embeddings = min(max(2 * len(register_names), 4), 50)

        register_filter = (
            [f"{peripheral_name}_{reg}" for reg in register_names]
            if strategy == BatchedRetrievalStrategy.COMBINED_WITH_FILTER
            else []
        )
        raw_results = search_context_raw(
            query, scaled_params, register_filter=register_filter,
        )
        if not raw_results:
            return None, []
        return post_process(raw_results, scaled_params, peripheral_name)

    # Per-register modes
    trim_per_register = (strategy == BatchedRetrievalStrategy.PER_REGISTER_TRIMMED)

    seen_chunks: set[str] = set()
    collected: list = []

    for reg in register_names:
        query = _PER_REGISTER_QUERY_TEMPLATE.format(
            peripheral=peripheral_name, register=reg,
        )
        reg_filter = f"{peripheral_name}_{reg}"
        raw_results = search_context_raw(
            query, params, register_filter=reg_filter,
        )

        if trim_per_register:
            # Apply score threshold + trim per register (matches the unbatched path).
            raw_results = [r for r in raw_results if r.score >= params.score_threshold]
            raw_results.sort(key=lambda r: r.score, reverse=True)
            raw_results = raw_results[:max(1, params.number_embeddings)]

        for r in raw_results:
            chunk_key = r.text.strip()
            if chunk_key not in seen_chunks:
                seen_chunks.add(chunk_key)
                collected.append(r)

    if not collected:
        return None, []

    scaled_params = params.model_copy()
    scaled_params.number_embeddings = len(collected)

    if trim_per_register:
        # Sort by document order so the LLM sees chunks in reading order;
        # disable keyword boost so post_process doesn't re-sort by score.
        collected.sort(key=lambda r: (r.page_number, r.metadata.get("chunk_index", 0)))
        scaled_params.keyword_boost = False
    else:
        # PER_REGISTER (default): pre-sort by score; post_process may re-sort
        # again via keyword boost if enabled.
        collected.sort(key=lambda r: r.score, reverse=True)

    return post_process(collected, scaled_params, peripheral_name)


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
