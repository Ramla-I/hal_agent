import os
import re
import json
from typing import Optional, Dict, List
from defs import ContextRetrievalParameters, Manufacturer, ContextRetrievalMethod
from agent_tools.tools import all_svd_file_paths, calculate_address_offset
from agent_tools.svd_parsing import get_peripheral_names, get_register_names_for_peripheral, get_field_counts_for_peripheral
from prompts.register_info_stm import (
    create_register_info_stm_system_prompt,
    create_register_info_stm_user_prompt,
    create_register_info_stm_system_prompt_batched,
    create_register_info_stm_user_prompt_batched,
)
from utils.parse_output import (
    get_json_block_from_response,
    get_json_array_from_response,
    get_reasoning_from_response,
    get_function_calls_from_response,
)
from utils.function_call_handler import create_default_handler
from utils.utils import setup_logger, count_tokens
from utils.llm import call_llm
from utils.models import model_costs
from utils.result_saver import ResultSaver, UsageStats
from utils.timing import timed_operation
from context_retrieval.retrieve_context import retrieve_context, retrieve_context_for_peripheral
from scripts.limit_context import truncate_message_by_tokens
from groq import Groq
from openai import OpenAI

logger = setup_logger(__name__)
def run_generator(
    client: OpenAI|Groq,
    model_name: str,
    device_name: str, 
    run_number: int, 
    device_dir: str, 
    agent_output_dir: str,
    context_retrieval_parameters: ContextRetrievalParameters,
    manufacturer: Manufacturer,
    peripherals_registers_dict: Optional[Dict[str, List[str]]] = None,
    models: Optional[List[str]] = None,
) -> bool:
    """
    Runs the generator agent for a given device and run number.
    Args:
        device_name: The name of the device to run the generator for.
        run_number: The run number to run the generator for.
        device_dir: The path to the datasheet file for the device.
        agent_output_dir: The directory to output the agent's output to.
        model_name: The name of the model to use for the generator.
        context_retrieval_parameters: The context retrieval parameters to use for the generator.
        manufacturer: The manufacturer of the device.
        peripherals_registers_dict: Optional dict mapping peripheral names to lists of register names.
            Format: {peripheral_name: [register_name1, register_name2, ...]}
            If None, all peripherals and registers will be extracted from SVD files.
    """
    logger.info(f"Running generator for device {device_name} with run number {run_number}")

    # Model list for the call layer: explicit `models` (with overflow) or just the
    # single requested model (back-compat for callers that pin one model).
    gen_models = models or [model_name]
    truncated_at_any_register = False
    failed_registers = 0

    saver_info = ResultSaver(os.path.join(agent_output_dir, "info"))
    saver_output = ResultSaver(agent_output_dir)

    summary_content = (
        f"MODEL: {model_name}\n"
    )
    saver_info.save_text(summary_content, "summary.txt")

    # Initialize function call handler
    function_handler = create_default_handler()
    
    # Get the name of each register to find in the datasheet, that is our prompt granularity
    if peripherals_registers_dict is None:
        # Extract all peripherals and registers from SVD files
        svd_file_paths = all_svd_file_paths(device_dir)
        peripheral_names = get_peripheral_names(svd_file_paths)

        register_names_to_process = {peripheral_name: [] for peripheral_name in peripheral_names}
        for peripheral_name in peripheral_names:
            register_names = get_register_names_for_peripheral(svd_file_paths, peripheral_name)
            register_names_to_process[peripheral_name].extend(register_names)
        
        logger.info(f"Found registers for {len(register_names_to_process)} peripherals")
    else:
        # Use provided dict of peripherals and registers
        register_names_to_process = peripherals_registers_dict
        logger.info(f"Using provided dict with {len(register_names_to_process)} peripherals")
    
    # Now the Context Retrieval Part
    for peripheral_name in register_names_to_process.keys():
        for register_name in register_names_to_process[peripheral_name]:
            logger.debug(f"Processing {peripheral_name}_{register_name}")
            usage = []
            # check if output file exists, if so assume the agent already processed it, skip to the next register
            output_filename = f"{peripheral_name}_{register_name}"
            output_path = os.path.join(agent_output_dir, output_filename)
            if os.path.exists(output_path):
                continue
            
            datasheet_pages, embedding_ids = retrieve_context(context_retrieval_parameters, device_name, device_dir, peripheral_name, register_name, manufacturer, agent_output_dir)
            if datasheet_pages is None:
                continue

            # Save embedding IDs for overlap analysis
            if embedding_ids:
                embedding_info = {
                    "peripheral": peripheral_name,
                    "register": register_name,
                    "num_embeddings": context_retrieval_parameters.number_embeddings,
                    "embedding_ids": embedding_ids
                }
                saver_info.append_text(
                    json.dumps(embedding_info) + "\n",
                    "embedding_ids.jsonl"
                )

            # Count tokens in file search results
            file_search_tokens = count_tokens(datasheet_pages)

            input_list = [
                {
                    "role": "developer",
                    "content": create_register_info_stm_system_prompt()
                },
                {
                    "role": "user",
                    "content": create_register_info_stm_user_prompt(register_name, peripheral_name, datasheet_pages)
                }
            ]
            truncated, input_list = truncate_message_by_tokens(input_list, model_name)
            truncated_at_any_register = truncated_at_any_register or truncated

            if truncated:
                logger.info(f"Truncated input list for {peripheral_name}_{register_name}")

            try:
                with timed_operation("generator_llm_call"):
                    response, used_model = call_llm(
                        "generator", models=gen_models,
                        input=input_list,
                        tool_choice="none",
                        truncation="auto",
                    )
            except Exception as e:
                # Isolate per register: a terminal failure (e.g. all models
                # rate-limited) skips this register instead of aborting the device.
                logger.error("Generator failed for %s_%s: %s", peripheral_name, register_name, e)
                failed_registers += 1
                continue

            if response.output_text:
                input_list.append({
                    "role": "assistant",
                    "content": response.output_text
                })

            reasoning, rest_of_response = get_reasoning_from_response(response.output_text)
            json_block = get_json_block_from_response(rest_of_response)
            usage.append(response.usage)

            # Process function calls using the abstraction
            function_results = function_handler.process_function_calls(rest_of_response)
            if function_results:
                for result in function_results:
                    logger.debug(f"FUNCTION CALL: {result.function_name} - Success: {result.success}")
                    if not result.success:
                        logger.error(
                            "Error in function call for %s: %s",
                            register_name,
                            result.error_message,
                        )
                    else:
                        logger.debug(
                            "Success in function call for %s: %s",
                            register_name,
                            result.result,
                        )
                                        
                    # Add the result message to the input list for the next response
                    input_list.append({
                        "role": "user",
                        "content": result.message
                    })

                truncated, input_list = truncate_message_by_tokens(input_list, model_name)
                truncated_at_any_register = truncated_at_any_register or truncated

                if truncated:
                    logger.info(f"Truncated input list for {peripheral_name}_{register_name} after function calls")

                # Get response after function calls
                try:
                    with timed_operation("generator_llm_call"):
                        response, used_model = call_llm(
                            "generator", models=gen_models,
                            input=input_list,
                            tool_choice="none",
                            truncation="auto",
                        )
                except Exception as e:
                    logger.error("Generator follow-up failed for %s_%s: %s", peripheral_name, register_name, e)
                    failed_registers += 1
                    continue
                reasoning, rest_of_response = get_reasoning_from_response(response.output_text)
                json_block = get_json_block_from_response(rest_of_response)
                usage.append(response.usage)

            usage_stats = UsageStats.aggregate(used_model, usage, file_search_tokens)
            saver_info.save_usage_stats(
                usage_stats,
                "usage.csv",
                additional_fields={
                    "peripheral_name": peripheral_name,
                    "register_name": register_name,
                },
            )
            saver_info.save_reasoning(
                reasoning,
                "reasoning.txt",
                prefix=f"---{peripheral_name}_{register_name}---",
            )
            # Structured, per-register reasoning for clean downstream lookup
            # (bug-finding uses this as datasheet evidence).
            saver_info.append_text(
                json.dumps({
                    "peripheral": peripheral_name,
                    "register": register_name,
                    "reasoning": reasoning,
                }) + "\n",
                "reasoning.jsonl",
            )

            if json_block:
                try:
                    json_data = json.loads(json_block)
                except Exception as e:
                    logger.error(
                        "Error loading JSON for %s: %s. JSON block: %s",
                        register_name,
                        e,
                        json_block,
                    )
                    json_data = None
            else:
                json_data = None

            if json_data:
                saver_output.save_json(json_data, output_filename)

    if failed_registers:
        logger.error(
            "Generator for %s: %d register(s) failed and were skipped (resume to retry)",
            device_name, failed_registers,
        )
    return truncated_at_any_register


def chunk_registers(registers: list[str], max_size: int = 15) -> list[list[str]]:
    """Split a list of register names into batches of at most *max_size*."""
    if not registers:
        return [[]]  # one empty batch → triggers discovery mode
    return [registers[i : i + max_size] for i in range(0, len(registers), max_size)]


def chunk_registers_adaptive(
    registers: list[str],
    field_counts: dict[str, int],
    max_fields_per_batch: int,
    max_registers_per_batch: int = 15,
    default_field_count: int = 5,
) -> list[list[str]]:
    """Split registers into batches that keep total estimated fields under a cap.

    Each register's field count is looked up in *field_counts* (from SVD).
    Registers not found there get *default_field_count* as a conservative estimate.

    A register is added to the current batch if doing so keeps the batch's
    total fields <= *max_fields_per_batch* **and** the batch size <=
    *max_registers_per_batch*.  Otherwise a new batch is started.  A single
    register always gets its own batch even if it exceeds the field cap.
    """
    if not registers:
        return [[]]  # one empty batch → discovery mode

    batches: list[list[str]] = []
    current_batch: list[str] = []
    current_fields = 0

    for reg in registers:
        reg_fields = field_counts.get(reg, default_field_count)
        would_exceed_fields = current_batch and (current_fields + reg_fields > max_fields_per_batch)
        would_exceed_regs = current_batch and (len(current_batch) >= max_registers_per_batch)

        if would_exceed_fields or would_exceed_regs:
            batches.append(current_batch)
            current_batch = []
            current_fields = 0

        current_batch.append(reg)
        current_fields += reg_fields

    if current_batch:
        batches.append(current_batch)

    return batches


def run_generator_batched(
    client: OpenAI | Groq,
    model_name: str,
    device_name: str,
    run_number: int,
    device_dir: str,
    agent_output_dir: str,
    context_retrieval_parameters: ContextRetrievalParameters,
    manufacturer: Manufacturer,
    peripherals_registers_dict: Optional[Dict[str, List[str]]] = None,
    max_registers_per_batch: int = 15,
    max_fields_per_batch: int = 50,
    include_reasoning: bool = True,
    skip_function_followup: bool = False,
    system_prompt_override: Optional[str] = None,
    retrieval_only: bool = False,
    models: Optional[List[str]] = None,
) -> bool:
    """Per-peripheral batched generator — one LLM call per batch of registers.

    Output files are identical to ``run_generator()`` (one JSON per register),
    so downstream pipeline steps are fully compatible.

    When ``retrieval_only=True``, runs only the retrieval step per batch (writing
    ``embedding_ids.jsonl``) and skips the LLM call + output parsing. Useful for
    cheap retrieval-only sweeps that pair with retrieval IR metrics.
    """
    logger.info(
        "Running batched generator for device %s with run number %s",
        device_name, run_number,
    )

    gen_models = models or [model_name]
    truncated_at_any_register = False
    failed_batches = 0

    saver_info = ResultSaver(os.path.join(agent_output_dir, "info"))
    saver_output = ResultSaver(agent_output_dir)

    saver_info.save_text(f"MODEL: {model_name}\nMODE: batched\n", "summary.txt")

    function_handler = create_default_handler()
    if system_prompt_override is not None:
        system_prompt = system_prompt_override
    else:
        system_prompt = create_register_info_stm_system_prompt_batched(include_reasoning=include_reasoning)

    # ---- Build peripheral→registers mapping ----
    svd_file_paths = all_svd_file_paths(device_dir)
    if peripherals_registers_dict is None:
        peripheral_names = get_peripheral_names(svd_file_paths)
        register_names_to_process: Dict[str, List[str]] = {}
        for pname in peripheral_names:
            register_names_to_process[pname] = get_register_names_for_peripheral(
                svd_file_paths, pname,
            )
        logger.info("Found registers for %d peripherals", len(register_names_to_process))
    else:
        register_names_to_process = peripherals_registers_dict
        logger.info("Using provided dict with %d peripherals", len(register_names_to_process))

    # ---- Main loop ----
    for peripheral_name, all_registers in register_names_to_process.items():
        # Determine which registers still need processing
        remaining = [
            r for r in all_registers
            if not os.path.exists(os.path.join(agent_output_dir, f"{peripheral_name}_{r}"))
        ]

        # Derived peripherals (0 SVD registers) → discovery mode
        if not all_registers:
            batches = [[]]  # single empty batch
        elif not remaining:
            continue  # all registers already done
        else:
            # Adaptive batching: use SVD field counts to limit output complexity
            try:
                field_counts = get_field_counts_for_peripheral(svd_file_paths, peripheral_name)
            except ValueError:
                field_counts = {}
            batches = chunk_registers_adaptive(
                remaining, field_counts, max_fields_per_batch, max_registers_per_batch,
            )
            total_fields = sum(field_counts.get(r, 5) for r in remaining)
            batch_fields = [
                sum(field_counts.get(r, 5) for r in b) for b in batches
            ]
            logger.info(
                "Batch plan for %s: %d regs (%d fields) → %d batches, fields per batch: %s",
                peripheral_name, len(remaining), total_fields, len(batches), batch_fields,
            )

        for batch in batches:
            batch_label = (
                f"{peripheral_name} ({len(batch)} regs)" if batch
                else f"{peripheral_name} (discovery)"
            )
            logger.info("Processing batch: %s", batch_label)

            usage = []

            # 1. Retrieve context for the batch
            datasheet_pages, embedding_ids = retrieve_context_for_peripheral(
                context_retrieval_parameters,
                device_name,
                device_dir,
                peripheral_name,
                batch,
                manufacturer,
                agent_output_dir,
            )
            if datasheet_pages is None:
                logger.warning("No context found for %s — skipping batch", batch_label)
                continue

            # Save embedding IDs
            if embedding_ids:
                embedding_info = {
                    "peripheral": peripheral_name,
                    "registers": batch,
                    "num_embeddings": context_retrieval_parameters.number_embeddings,
                    "embedding_ids": embedding_ids,
                }
                saver_info.append_text(
                    json.dumps(embedding_info) + "\n",
                    "embedding_ids.jsonl",
                )

            if retrieval_only:
                # Retrieval-only mode: skip LLM + output parsing for this batch.
                continue

            # Count tokens in context
            file_search_tokens = count_tokens(datasheet_pages)

            # 2. Build batched prompt
            input_list = [
                {
                    "role": "developer",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": create_register_info_stm_user_prompt_batched(
                        peripheral_name, batch, datasheet_pages,
                    ),
                },
            ]
            truncated, input_list = truncate_message_by_tokens(input_list, model_name)
            truncated_at_any_register = truncated_at_any_register or truncated
            if truncated:
                logger.info("Truncated input for batch %s", batch_label)

            # Estimate output budget: tokens/register + reasoning overhead
            per_register_tokens = 2000 if include_reasoning else 1500
            batch_output_estimate = max(len(batch), 1) * per_register_tokens + 2000
            model_max = model_costs.get(model_name, {}).get("max_output_tokens", 65536)
            max_output_tokens = min(batch_output_estimate, model_max)

            # 3. LLM call
            try:
                with timed_operation("generator_llm_call"):
                    response, used_model = call_llm(
                        "generator", models=gen_models,
                        input=input_list,
                        tool_choice="none",
                        truncation="auto",
                        max_output_tokens=max_output_tokens,
                    )
            except Exception as e:
                logger.error("Generator failed for batch %s: %s", batch_label, e)
                failed_batches += 1
                continue

            if response.output_text:
                input_list.append({
                    "role": "assistant",
                    "content": response.output_text,
                })

            reasoning, rest_of_response = get_reasoning_from_response(response.output_text)
            usage.append(response.usage)

            # 4. Process function calls
            function_results = function_handler.process_function_calls(rest_of_response)
            if function_results:
                for result in function_results:
                    logger.debug("FUNCTION CALL: %s - Success: %s", result.function_name, result.success)
                    if not result.success:
                        logger.error("Error in function call for batch %s: %s", batch_label, result.error_message)

                if not skip_function_followup:
                    # Original behavior: send results back to LLM for a second call
                    for result in function_results:
                        input_list.append({
                            "role": "user",
                            "content": result.message,
                        })

                    truncated, input_list = truncate_message_by_tokens(input_list, model_name)
                    truncated_at_any_register = truncated_at_any_register or truncated

                    try:
                        with timed_operation("generator_llm_call"):
                            response, used_model = call_llm(
                                "generator", models=gen_models,
                                input=input_list,
                                tool_choice="none",
                                truncation="auto",
                                max_output_tokens=max_output_tokens,
                            )
                    except Exception as e:
                        logger.error("Generator follow-up failed for batch %s: %s", batch_label, e)
                        failed_batches += 1
                        continue
                    reasoning, rest_of_response = get_reasoning_from_response(response.output_text)
                    usage.append(response.usage)
                else:
                    # Skip follow-up: execute function calls locally and patch
                    # the JSON with correct computed offsets instead of making
                    # a second LLM call.
                    logger.info(
                        "Skipping function follow-up for %s (%d calls executed locally)",
                        batch_label, len(function_results),
                    )

            # 5. Parse JSON array
            json_array = get_json_array_from_response(rest_of_response)

            # 5b. Patch address_offset values from function call results
            if skip_function_followup and function_results and json_array:
                fn_text = get_function_calls_from_response(rest_of_response)
                if fn_text:
                    try:
                        fn_data = json.loads(fn_text)
                        fn_calls_raw = fn_data.get("function_calls", fn_data if isinstance(fn_data, list) else [])
                    except (json.JSONDecodeError, AttributeError):
                        fn_calls_raw = []

                    # Build mapping: register_number → computed offset
                    offset_by_regnum: dict[int, str] = {}
                    for fc_raw, fc_result in zip(fn_calls_raw, function_results):
                        if fc_result.success and isinstance(fc_raw, dict):
                            params = fc_raw.get("parameters", {})
                            reg_num = params.get("register_number")
                            if reg_num is not None:
                                offset_by_regnum[int(reg_num)] = fc_result.result

                    # Patch JSON entries whose trailing number matches
                    if offset_by_regnum:
                        for item in json_array:
                            rn = item.get("register_name", "")
                            m = re.search(r"(\d+)$", rn)
                            if m:
                                reg_num = int(m.group(1))
                                if reg_num in offset_by_regnum:
                                    computed = offset_by_regnum[reg_num]
                                    current = item.get("address_offset")
                                    if current != computed:
                                        logger.info(
                                            "Patching %s address_offset: %s → %s",
                                            rn, current, computed,
                                        )
                                        item["address_offset"] = computed

            # 6. Save individual register files
            if json_array:
                for item in json_array:
                    reg_name = item.pop("register_name", None)
                    if not reg_name:
                        continue
                    # Strip peripheral prefix if present (e.g. "BKP_DR1" → "DR1")
                    if reg_name.upper().startswith(f"{peripheral_name.upper()}_"):
                        short_name = reg_name[len(peripheral_name) + 1 :]
                    else:
                        short_name = reg_name
                    # Check that at least one meaningful field is present
                    has_data = any(
                        item.get(k) is not None
                        for k in ("address_offset", "reset_value", "size", "subfields")
                    )
                    if has_data:
                        output_filename = f"{peripheral_name}_{short_name}"
                        saver_output.save_json(item, output_filename)
            else:
                logger.warning("No JSON array parsed for batch %s", batch_label)

            # 7. Save usage & reasoning
            usage_stats = UsageStats.aggregate(used_model, usage, file_search_tokens)
            batch_register_names = ", ".join(batch) if batch else "(discovery)"
            saver_info.save_usage_stats(
                usage_stats,
                "usage.csv",
                additional_fields={
                    "peripheral_name": peripheral_name,
                    "register_name": batch_register_names,
                },
            )
            saver_info.save_reasoning(
                reasoning,
                "reasoning.txt",
                prefix=f"---{peripheral_name}---",
            )
            # Structured reasoning (per batch / peripheral) for downstream lookup.
            saver_info.append_text(
                json.dumps({
                    "peripheral": peripheral_name,
                    "registers": batch,
                    "reasoning": reasoning,
                }) + "\n",
                "reasoning.jsonl",
            )

    if failed_batches:
        logger.error(
            "Generator for %s: %d batch(es) failed and were skipped (resume to retry)",
            device_name, failed_batches,
        )
    return truncated_at_any_register


if __name__ == "__main__":
    raise SystemExit(
        "This module no longer provides a CLI/test harness. "
        "Use optimization/retrieval/evaluate_retrieval.py instead."
    )