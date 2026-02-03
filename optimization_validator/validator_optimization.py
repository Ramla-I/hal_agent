import os
import sys
from pathlib import Path

# Add parent directory to path to import from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import csv

from config import client_groq, client_openai, TIKTOKEN_ENCODING
from utils.parse_output import get_json_block_from_response
from utils.utils import get_model_string
from groq import Groq
from openai import OpenAI
from prompts.validator import (
    create_validator_system_prompt,
    create_validator_file_search_query,
    create_validator_user_prompt,
    create_batched_validator_system_prompt,
    create_batched_validator_file_search_query,
    create_batched_validator_user_prompt
)
from context_retrieval.semantic_search import search_vector_store, format_results
from utils.result_saver import ResultSaver, UsageStats
from utils.timing import timed_operation, get_timing_stats
import tiktoken


def _load_test_set_rows(test_set_path: str) -> list[dict]:
    test_set_rows = []
    with open(test_set_path, "r", encoding="utf-8") as test_set_file:
        reader = csv.DictReader(test_set_file)
        for row in reader:
            test_set_rows.append(dict(row))
    return test_set_rows


def _count_tokens(text: str) -> int:
    try:
        encoding = tiktoken.get_encoding(TIKTOKEN_ENCODING)
        return len(encoding.encode(text))
    except Exception:
        return 0


def _create_response(client: OpenAI | Groq, model_name: str, input_list: list, reasoning_effort: str | None):
    if reasoning_effort is not None:
        return client.responses.create(
            model=get_model_string(model_name),
            reasoning={"effort": reasoning_effort},
            input=input_list,
        )
    return client.responses.create(
        model=get_model_string(model_name),
        input=input_list,
    )


def _compute_accuracy_metrics(tp: int, fn: int, fp: int, tn: int) -> dict:
    total = tp + fn + fp + tn
    accuracy = (tp + tn) / total if total > 0 else 0.0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1_score": f1_score,
    }


def _save_accuracy_metrics(saver: ResultSaver, accuracy_csv_name: str, model_name: str, tp: int, fn: int, fp: int, tn: int):
    metrics = _compute_accuracy_metrics(tp, fn, fp, tn)
    saver.save_csv_row(
        {
            'model_name': model_name,
            'true_positives': tp,
            'false_negatives': fn,
            'false_positives': fp,
            'true_negatives': tn,
            'accuracy': metrics["accuracy"],
            'precision': metrics["precision"],
            'recall': metrics["recall"],
            'f1_score': metrics["f1_score"],
        },
        accuracy_csv_name
    )

def run_validator(client: OpenAI|Groq, model_name: str, test_set_path: str, output_dir: str, vs_id: str, reasoning_effort: str | None = None, num_embeddings: int = 4):
    """
    Run the validator sequentially over a test set and write outputs.

    Assumptions:
    - test_set_path CSV has columns: peripheral, register, field_name, key, correct_value, is_correct.
    - vs_id points to a valid vector store; embeddings count is supported by search.
    - output_dir exists or is creatable by ResultSaver.

    Inputs:
    - client: OpenAI or Groq client to issue responses.
    - model_name: Model identifier used in filenames and API calls.
    - test_set_path: Path to test or hold set CSV.
    - output_dir: Directory to write output artifacts.
    - vs_id: Vector store ID for retrieval.
    - reasoning_effort: Optional reasoning effort parameter for supported models.
    - num_embeddings: Number of embeddings to retrieve per search.

    Output:
    - Writes CSV/TXT outputs (accuracy, usage, output, reasoning) into output_dir.
    - Returns None; side effects are persisted files and console logs.
    """
    total_true_positives = 0
    total_false_negatives = 0
    total_false_positives = 0
    total_true_negatives = 0
    output_errors = 0

    # Initialize ResultSaver for all file operations
    saver = ResultSaver(output_dir)
    
    # Define file names
    output_csv_name = f"validator_output_{model_name}.csv"
    reasoning_txt_name = f"validator_reasoning_{model_name}.txt"
    usage_csv_name = f"validator_usage_{model_name}.csv"
    accuracy_csv_name = f"validator_accuracy_{model_name}.csv"
    
    print(f"Running validator for {model_name} with test set {test_set_path}")

    test_set_rows = []
    with open(test_set_path, "r", encoding="utf-8") as test_set_file:
        reader = csv.DictReader(test_set_file)
        for row in reader:
            test_set_rows.append(dict(row))
    
    for row in test_set_rows:
        peripheral_name = row['peripheral']
        register_name = row['register']
        field_name = row['field_name']
        key = row['key']
        value = row['correct_value']
        true_value = row['is_correct']
        
        # print(f"Data: {data}")
        input_list = [
            {
                "role": "developer",
                "content": [
                    {
                        "type": "input_text",
                        "text": create_validator_system_prompt()
                    },
                ]
            }
        ]
        
        query = create_validator_file_search_query(peripheral_name, register_name, field_name, key, value)
        file_search_results = search_vector_store(query, vs_id, num_embeddings, True, 0.25)
        embeddings_returned = len(file_search_results.data)
        file_search = format_results(file_search_results)

        # Count tokens in file search results
        file_search_tokens = _count_tokens(file_search)
        input_list.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": create_validator_user_prompt(peripheral_name, register_name, field_name, key, value, file_search)
                    }
                ]
            }
        )

        with timed_operation("validator_llm_call"):
            response = _create_response(client, model_name, input_list, reasoning_effort)

        # Save reasoning text
        saver.append_text(f"{response.output_text}\n\n", reasoning_txt_name)

        json_block = get_json_block_from_response(response.output_text)
        if json_block is not None:
            try:
                json_data = json.loads(json_block)
                
                # Save validator output row
                saver.save_csv_row(
                    {
                        'peripheral_name': peripheral_name,
                        'register_name': register_name,
                        'field_name': field_name,
                        'key': key,
                        'value': value,
                        'true_value': true_value,
                        'agent_judgement': json_data['is_true'],
                        'confidence_score': json_data['confidence_score']
                    },
                    output_csv_name
                )
                
                agent_judgement = True if json_data['is_true'] == True else False
                correct_judgement = True if true_value == "True" else False
                # print(f"json_data: {json_data['is_true']}, true_value: {true_value}")
                # print(f"Agent judgement: {agent_judgement}, Correct judgement: {correct_judgement}, Confidence score: {json_data['confidence_score']}   Peripheral: {peripheral_name}, Register: {register_name}, Field: {field_name}, Key: {key}, Value: {value}, True value: {true_value}")
                if agent_judgement == True and correct_judgement == True:
                    total_true_positives += 1
                elif agent_judgement == False and correct_judgement == True:
                    total_false_negatives += 1
                elif agent_judgement == True and correct_judgement == False:
                    total_false_positives += 1
                elif agent_judgement == False and correct_judgement == False:
                    total_true_negatives += 1
            
            except Exception as e:
                print(f"Error parsing JSON block for peripheral {peripheral_name}, register {register_name}, field {field_name}, key {key}, value {value}: {e}")
                output_errors += 1

        # Save usage statistics
        usage_stats = UsageStats.from_response_usage(model_name, response.usage, file_search_tokens)
        saver.save_usage_stats(
            usage_stats,
            usage_csv_name,
            additional_fields={
                'peripheral_name': peripheral_name,
                'register_name': register_name,
                'field_name': field_name,
                'key': key,
                'embeddings_returned': embeddings_returned,
            }
        )

    # Save accuracy metrics
    _save_accuracy_metrics(
        saver,
        accuracy_csv_name,
        model_name,
        total_true_positives,
        total_false_negatives,
        total_false_positives,
        total_true_negatives,
    )

    print(f"Total output errors: {output_errors}")


def create_batches_by_size(test_set_rows, batch_size=None):
    """
    Create batches of invariants, keeping all invariants for a register together.

    Args:
        test_set_rows: List of test set rows
        batch_size: Target batch size (number of registers per batch). If None, one register per batch.

    Returns:
        List of batches, where each batch is a list of rows

    Assumptions:
    - test_set_rows are dicts with 'peripheral' and 'register' keys.
    - Batching groups by (peripheral, register) to avoid splitting registers.

    Output:
    - List of dicts with keys: 'registers' and 'rows'.
    """
    from collections import defaultdict

    # First group by (peripheral, register)
    register_groups = defaultdict(list)
    for row in test_set_rows:
        key = (row['peripheral'], row['register'])
        register_groups[key].append(row)

    # If no batch_size specified, return one batch per register (original behavior)
    if batch_size is None:
        return [{'registers': [(key,)], 'rows': rows} for key, rows in register_groups.items()]

    # Create batches of batch_size registers
    # Keep all invariants for a register together
    batches = []
    current_batch_registers = []
    current_batch_rows = []
    current_batch_size = 0

    for register_key, register_rows in register_groups.items():
        # If adding this register would exceed batch_size, start a new batch
        if current_batch_size > 0 and current_batch_size + 1 > batch_size:
            batches.append({
                'registers': current_batch_registers,
                'rows': current_batch_rows
            })
            current_batch_registers = [register_key]
            current_batch_rows = register_rows.copy()
            current_batch_size = 1
        else:
            current_batch_registers.append(register_key)
            current_batch_rows.extend(register_rows)
            current_batch_size += 1

    # Don't forget the last batch
    if current_batch_registers:
        batches.append({
            'registers': current_batch_registers,
            'rows': current_batch_rows
        })

    return batches


def process_single_batch(
    client: OpenAI|Groq,
    model_name: str,
    batch_registers: list,
    batch_rows: list,
    batch_id: str,
    vs_id: str,
    num_embeddings: int,
    reasoning_effort: str | None,
    saver: 'ResultSaver',
    output_csv_name: str,
    reasoning_txt_name: str,
    usage_csv_name: str
):
    """
    Process a single batch of invariants. Returns (tp, fp, tn, fn, errors).
    Automatically splits the batch if context length is exceeded.

    Assumptions:
    - batch_rows follow the test set schema.
    - batch_registers contains tuples of (peripheral, register) referenced by batch_rows.
    - The model returns JSON compatible with get_json_block_from_response().

    Inputs:
    - client/model_name/vs_id/num_embeddings/reasoning_effort: model + retrieval config.
    - batch_registers/batch_rows/batch_id: data to validate and identifier for outputs.
    - saver/output_csv_name/reasoning_txt_name/usage_csv_name: output controls.

    Output:
    - Returns tuple (tp, fp, tn, fn, errors, context_too_large).
    - Writes usage, output, and reasoning files via ResultSaver.
    """
    # Check if batch can be split further (need at least 2 registers or a register with multiple invariants)
    can_split = len(batch_registers) > 1 or (len(batch_registers) == 1 and len(batch_rows) > 1)

    context_too_large = False
    try:
        # Perform a single file search for all registers in batch
        combined_query_parts = [
            create_batched_validator_file_search_query(peripheral_name, register_name)
            for peripheral_name, register_name in batch_registers
        ]
        combined_query = "\n".join(combined_query_parts)
        file_search = search_vector_store(combined_query, vs_id, num_embeddings, True, 0.25)
        embeddings_returned = len(file_search.data)
        combined_file_search = format_results(file_search)

        # Count tokens
        file_search_tokens = _count_tokens(combined_file_search)

        # Prepare invariants for batch
        invariants = []
        for row in batch_rows:
            invariants.append({
                'field_name': row['field_name'],
                'key': row['key'],
                'value': row['correct_value'],
                'peripheral': row['peripheral'],
                'register': row['register']
            })

        # Build user prompt for single or multi-register batch
        user_prompt = create_batched_validator_user_prompt(
            batch_registers,
            invariants,
            combined_file_search
        )

        # Build input
        input_list = [
            {
                "role": "developer",
                "content": [{
                    "type": "input_text",
                    "text": create_batched_validator_system_prompt()
                }]
            },
            {
                "role": "user",
                "content": [{
                    "type": "input_text",
                    "text": user_prompt
                }]
            }
        ]

        # Single LLM call for all invariants in this batch
        with timed_operation("validator_llm_call"):
            response = _create_response(client, model_name, input_list, reasoning_effort)

    except Exception as e:
        error_str = str(e).lower()
        # Check if this is a context length error
        if any(phrase in error_str for phrase in ['context_length_exceeded', 'context length', 'maximum context', 'too long', 'token limit']):
            context_too_large = True
            if not can_split:
                # Can't split further - this single register's invariants are too large
                print(f"⚠️  Context limit exceeded for {batch_id} and cannot split further ({len(batch_rows)} invariants from 1 register)")
                print(f"   Skipping this batch. Consider reducing num_embeddings or processing manually.")
                return (0, 0, 0, 0, len(batch_rows), context_too_large)

            # Split the batch and retry
            print(f"⚠️  Context limit exceeded for {batch_id} ({len(batch_rows)} invariants)")

            if len(batch_registers) > 1:
                # Split by registers
                mid_point = len(batch_registers) // 2
                batch1_registers = batch_registers[:mid_point]
                batch2_registers = batch_registers[mid_point:]

                # Split rows accordingly
                batch1_rows = [r for r in batch_rows if (r['peripheral'], r['register']) in batch1_registers]
                batch2_rows = [r for r in batch_rows if (r['peripheral'], r['register']) in batch2_registers]

                print(f"   Splitting into 2 sub-batches by registers: {len(batch1_registers)} and {len(batch2_registers)} registers")
            else:
                # Split single register's invariants in half
                mid_point = len(batch_rows) // 2
                batch1_registers = batch_registers
                batch2_registers = batch_registers
                batch1_rows = batch_rows[:mid_point]
                batch2_rows = batch_rows[mid_point:]

                print(f"   Splitting {batch_registers[0]} into 2 sub-batches: {len(batch1_rows)} and {len(batch2_rows)} invariants")

            # Process sub-batches recursively
            tp1, fp1, tn1, fn1, err1, ctx1 = process_single_batch(
                client, model_name, batch1_registers, batch1_rows, f"{batch_id}_part1",
                vs_id, num_embeddings, reasoning_effort, saver,
                output_csv_name, reasoning_txt_name, usage_csv_name
            )
            tp2, fp2, tn2, fn2, err2, ctx2 = process_single_batch(
                client, model_name, batch2_registers, batch2_rows, f"{batch_id}_part2",
                vs_id, num_embeddings, reasoning_effort, saver,
                output_csv_name, reasoning_txt_name, usage_csv_name
            )

            return (tp1 + tp2, fp1 + fp2, tn1 + tn2, fn1 + fn2, err1 + err2, context_too_large or ctx1 or ctx2)
        else:
            # Some other error - re-raise
            raise

    # If we get here, the LLM call succeeded
    total_true_positives = 0
    total_false_negatives = 0
    total_false_positives = 0
    total_true_negatives = 0
    output_errors = 0

    # Save reasoning
    saver.append_text(f"---{batch_id}---\n{response.output_text}\n\n", reasoning_txt_name)

    # Parse results
    json_block = get_json_block_from_response(response.output_text)
    if json_block is not None:
        try:
            results = json.loads(json_block)

            if not isinstance(results, list):
                print(f"Error: Expected list, got {type(results)} for {batch_id}")
                output_errors += 1
            else:
                # Process each result
                for result in results:
                    idx = result.get('invariant_index', -1)
                    if idx < 0 or idx >= len(batch_rows):
                        print(f"Error: Invalid invariant_index {idx} for {batch_id}")
                        continue

                    row = batch_rows[idx]
                    is_true = result.get('is_true', False)
                    confidence = result.get('confidence_score', 0.0)

                    # Save output
                    saver.save_csv_row(
                        {
                            'peripheral_name': row['peripheral'],
                            'register_name': row['register'],
                            'field_name': row['field_name'],
                            'key': row['key'],
                            'value': row['correct_value'],
                            'true_value': row['is_correct'],
                            'agent_judgement': is_true,
                            'confidence_score': confidence
                        },
                        output_csv_name
                    )

                    # Calculate confusion matrix
                    agent_judgement = bool(is_true)
                    correct_judgement = (row['is_correct'] == "True")

                    if agent_judgement == True and correct_judgement == True:
                        total_true_positives += 1
                    elif agent_judgement == False and correct_judgement == True:
                        total_false_negatives += 1
                    elif agent_judgement == True and correct_judgement == False:
                        total_false_positives += 1
                    elif agent_judgement == False and correct_judgement == False:
                        total_true_negatives += 1

        except Exception as e:
            print(f"Error parsing batch results for {batch_id}: {e}")
            output_errors += 1

    # Save usage statistics
    usage_stats = UsageStats.from_response_usage(model_name, response.usage, file_search_tokens)
    saver.save_usage_stats(
        usage_stats,
        usage_csv_name,
        additional_fields={
            'batch_id': batch_id,
            'batch_size(reg)': len(batch_registers),
            'num_invariants': len(batch_rows),
            'batch_size': len(batch_registers),
            'embeddings_returned': embeddings_returned,
        }
    )

    return (total_true_positives, total_false_positives, total_true_negatives, total_false_negatives, output_errors, context_too_large)


def run_validator_batched(client: OpenAI|Groq, model_name: str, test_set_path: str, output_dir: str, vs_id: str, reasoning_effort: str | None = None, num_embeddings: int = 4, batch_size: int | None = None):
    """
    Run validator with batching for verified datasets.

    Args:
        client: LLM client (OpenAI or Groq)
        model_name: Model name to use
        test_set_path: Path to test set CSV
        output_dir: Output directory for results
        vs_id: Vector store ID
        reasoning_effort: Reasoning effort parameter (optional)
        num_embeddings: Number of embeddings to retrieve
        batch_size: Target batch size (number of registers per batch).
                   If None, batches by register (one register per batch).

    Assumptions:
    - test_set_path CSV has columns: peripheral, register, field_name, key, correct_value, is_correct.
    - batch_size is a positive int when provided.

    Output:
    - Writes CSV/TXT outputs (accuracy, usage, output, reasoning, batch info) into output_dir.
    - Returns None; side effects are persisted files and console logs.
    """
    total_true_positives = 0
    total_false_negatives = 0
    total_false_positives = 0
    total_true_negatives = 0
    output_errors = 0

    # Initialize ResultSaver
    saver = ResultSaver(output_dir)

    # Define file names
    output_csv_name = f"validator_output_{model_name}.csv"
    reasoning_txt_name = f"validator_reasoning_{model_name}.txt"
    usage_csv_name = f"validator_usage_{model_name}.csv"
    accuracy_csv_name = f"validator_accuracy_{model_name}.csv"
    batch_info_csv_name = f"validator_batch_info_{model_name}.csv"

    batch_mode = "by register" if batch_size is None else f"batch_size={batch_size}"
    print(f"Running BATCHED validator for {model_name} with test set {test_set_path} (mode: {batch_mode})")

    # Load test set
    test_set_rows = _load_test_set_rows(test_set_path)

    # Create batches while keeping register invariants together
    batches = create_batches_by_size(test_set_rows, batch_size)

    total_invariants = len(test_set_rows)
    total_registers = sum(len(batch['registers']) for batch in batches)
    num_batches = len(batches)
    avg_registers_per_batch = total_registers / num_batches if num_batches > 0 else 0
    print(f"Batched {total_invariants} invariants into {num_batches} batches (avg registers: {avg_registers_per_batch:.1f})")

    # Process each batch
    for batch_idx, batch in enumerate(batches):
        batch_registers = batch['registers']
        batch_rows = batch['rows']

        # Create batch identifier
        if len(batch_registers) == 1:
            peripheral_name, register_name = batch_registers[0]
            batch_id = f"{peripheral_name}_{register_name}"
        else:
            batch_id = f"batch_{batch_idx}_({len(batch_registers)}_registers)"

        # Process the batch (with automatic splitting if context limit is hit)
        tp, fp, tn, fn, errors, context_too_large = process_single_batch(
            client, model_name, batch_registers, batch_rows, batch_id,
            vs_id, num_embeddings, reasoning_effort, saver,
            output_csv_name, reasoning_txt_name, usage_csv_name
        )

        # Accumulate results
        total_true_positives += tp
        total_false_positives += fp
        total_true_negatives += tn
        total_false_negatives += fn
        output_errors += errors

        saver.save_csv_row(
            {
                'batch_id': batch_id,
                'num_invariants': len(batch_rows),
                'num_registers': len(batch_registers),
                'context_too_large': context_too_large
            },
            batch_info_csv_name
        )

    # Save accuracy metrics
    _save_accuracy_metrics(
        saver,
        accuracy_csv_name,
        model_name,
        total_true_positives,
        total_false_negatives,
        total_false_positives,
        total_true_negatives,
    )

    print(f"Total output errors: {output_errors}")
    metrics = _compute_accuracy_metrics(
        total_true_positives,
        total_false_negatives,
        total_false_positives,
        total_true_negatives,
    )
    print(f"\nAccuracy Metrics:")
    print(f"  Accuracy:  {metrics['accuracy']:.2%}")
    print(f"  Precision: {metrics['precision']:.2%}")
    print(f"  Recall:    {metrics['recall']:.2%}")
    print(f"  F1 Score:  {metrics['f1_score']:.2%}")


if __name__ == "__main__":
    model_names = ["gpt-4.1-nano", "gpt-5-nano", "gpt-5.2", "gpt-oss-120b"]
    reasoning_efforts = [None, "low", None, None]
    clients = [client_openai, client_openai, client_openai, client_groq]

    id = 3

    # Configuration
    DATASET = "test"  # "test" or "hold"
    RUN_ALL_CONFIGS = True  # Set to False to run single configuration

    vs_id = "vs_6892501067b08191ac63cc6de06ee629"
    device = "stm-rm0041"
    experiment_name = "batch_sizes_embeddings"

    # Setup paths
    base_dir = os.path.join(Path(__file__).parent, device)
    if DATASET == "test":
        input_test_set_path = os.path.join(base_dir, "test_set_rm0041.csv")
    else:
        input_test_set_path = os.path.join(base_dir, "hold_set_rm0041.csv")

    if RUN_ALL_CONFIGS:
        # Run all configurations for comparison
        experiment_dir = os.path.join(base_dir, "experiments", experiment_name)
        configurations = [
            # {"mode": "sequential", "embeddings": 4, "batch_size": None},
            # {"mode": "batched", "embeddings": 4, "batch_size": 1},  # ~2 registers per batch
            # {"mode": "batched", "embeddings": 8, "batch_size": 1},  # ~2 registers per batch
            {"mode": "batched", "embeddings": 4, "batch_size": 4},  # ~2 registers per batch
            # {"mode": "batched", "embeddings": 16, "batch_size": 3},  # ~2 registers per batch
        ]

        results = []

        for config in configurations:
            mode = config["mode"]
            num_emb = config["embeddings"]
            batch_size = config.get("batch_size")

            # Create output directory name
            if mode == "batched" and batch_size is not None:
                output_dir = os.path.join(experiment_dir, f"{model_names[id]}_{DATASET}_emb{num_emb}_bs{batch_size}")
            else:
                output_dir = os.path.join(experiment_dir, f"{model_names[id]}_{mode}_{DATASET}_emb{num_emb}")
            os.makedirs(output_dir, exist_ok=True)

            batch_info = f" (batch_size={batch_size})" if batch_size is not None else ""
            print(f"\n{'='*80}")
            print(f"RUNNING: {mode.upper()} mode with {num_emb} embeddings{batch_info} - {DATASET.upper()} set")
            print(f"{'='*80}")
            print(f"Model: {model_names[id]}")
            print(f"Output: {output_dir}")
            print(f"{'='*80}\n")

            # Reset timing
            timing = get_timing_stats()
            timing.reset()

            # Run validator
            if mode == "batched":
                run_validator_batched(clients[id], model_names[id], input_test_set_path, output_dir, vs_id, reasoning_efforts[id], num_emb, batch_size)
            else:
                run_validator(clients[id], model_names[id], input_test_set_path, output_dir, vs_id, reasoning_efforts[id], num_emb)

            # Get timing stats
            stats = timing.get_all_stats()
            timing_stats_path = os.path.join(output_dir, "timing_stats.json")
            timing.save_to_file(timing_stats_path)

            # Read accuracy metrics
            accuracy_csv = os.path.join(output_dir, f"validator_accuracy_{model_names[id]}.csv")
            accuracy_metrics = {}
            if os.path.exists(accuracy_csv):
                with open(accuracy_csv, 'r') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        accuracy_metrics = row
                        break

            # Read usage stats for token counts
            usage_csv = os.path.join(output_dir, f"validator_usage_{model_names[id]}.csv")
            total_file_search_tokens = 0
            total_input_tokens = 0
            api_calls = 0
            total_batch_size = 0
            total_invariants = 0
            if os.path.exists(usage_csv):
                with open(usage_csv, 'r') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        api_calls += 1
                        total_file_search_tokens += int(row.get('file_search_tokens', 0))
                        total_input_tokens += int(row.get('input_tokens', 0))
                        if 'batch_size(reg)' in row:
                            total_batch_size += int(row.get('batch_size(reg)', 1))
                        elif 'batch_size' in row:
                            total_batch_size += int(row.get('batch_size', 1))
                        if 'num_invariants' in row:
                            total_invariants += int(row.get('num_invariants', 0))

            avg_file_search_tokens = total_file_search_tokens / api_calls if api_calls > 0 else 0
            avg_input_tokens = total_input_tokens / api_calls if api_calls > 0 else 0
            avg_batch_size = total_batch_size / api_calls if api_calls > 0 and total_batch_size > 0 else 1
            avg_invariants = total_invariants / api_calls if api_calls > 0 and total_invariants > 0 else 0

            # Store results
            results.append({
                "mode": mode,
                "embeddings": num_emb,
                "batch_size": batch_size if batch_size else "by_register",
                "llm_time": stats.get("validator_llm_call", {}).get("total_time", 0),
                "search_time": stats.get("vector_store_search", {}).get("total_time", 0),
                "total_time": stats.get("validator_llm_call", {}).get("total_time", 0) + stats.get("vector_store_search", {}).get("total_time", 0),
                "accuracy": float(accuracy_metrics.get("accuracy", 0)),
                "precision": float(accuracy_metrics.get("precision", 0)),
                "recall": float(accuracy_metrics.get("recall", 0)),
                "f1_score": float(accuracy_metrics.get("f1_score", 0)),
                "tp": int(accuracy_metrics.get("true_positives", 0)),
                "fp": int(accuracy_metrics.get("false_positives", 0)),
                "tn": int(accuracy_metrics.get("true_negatives", 0)),
                "fn": int(accuracy_metrics.get("false_negatives", 0)),
                "api_calls": api_calls,
                "avg_file_search_tokens": avg_file_search_tokens,
                "avg_input_tokens": avg_input_tokens,
                "avg_batch_size": avg_batch_size,
                "avg_invariants": avg_invariants,
            })

        # Print comparison table
        print(f"\n{'='*120}")
        print(f"VALIDATOR OPTIMIZATION COMPARISON - {DATASET.upper()} SET")
        print(f"{'='*120}\n")

        # Main performance table
        print(f"{'Configuration':<25} | {'API Calls':<10} | {'LLM Time':<12} | {'Search Time':<12} | {'Total Time':<12} | {'F1 Score':<10}")
        print(f"{'-'*25}-+-{'-'*10}-+-{'-'*12}-+-{'-'*12}-+-{'-'*12}-+-{'-'*10}")

        for r in results:
            config_name = f"{r['mode']}, {r['embeddings']} emb"
            print(f"{config_name:<25} | {r['api_calls']:>10} | {r['llm_time']:>10.2f}s | {r['search_time']:>10.2f}s | {r['total_time']:>10.2f}s | {r['f1_score']:>9.2%}")

        # Full quality metrics table
        print(f"\n{'Quality Metrics'}")
        print(f"{'-'*120}")
        print(f"{'Configuration':<25} | {'Accuracy':<10} | {'Precision':<10} | {'Recall':<10} | {'F1 Score':<10} | {'TP':<6} | {'FP':<6} | {'TN':<6} | {'FN':<6}")
        print(f"{'-'*25}-+-{'-'*10}-+-{'-'*10}-+-{'-'*10}-+-{'-'*10}-+-{'-'*6}-+-{'-'*6}-+-{'-'*6}-+-{'-'*6}")

        for r in results:
            config_name = f"{r['mode']}, {r['embeddings']} emb"
            print(f"{config_name:<25} | {r['accuracy']:>9.2%} | {r['precision']:>9.2%} | {r['recall']:>9.2%} | {r['f1_score']:>9.2%} | {r['tp']:>6} | {r['fp']:>6} | {r['tn']:>6} | {r['fn']:>6}")

        # Token usage table
        print(f"\n{'Token Usage'}")
        print(f"{'-'*100}")
        print(f"{'Configuration':<25} | {'Avg File Search':<18} | {'Avg Input':<15} | {'Avg Registers':<15} | {'Avg Invariants':<15}")
        print(f"{'-'*25}-+-{'-'*18}-+-{'-'*15}-+-{'-'*15}-+-{'-'*15}")

        for r in results:
            config_name = f"{r['mode']}, {r['embeddings']} emb"
            batch_str = f"{r['avg_batch_size']:.1f}" if r['avg_batch_size'] > 1 else "N/A"
            inv_str = f"{r['avg_invariants']:.1f}" if r['avg_invariants'] > 0 else "N/A"
            print(f"{config_name:<25} | {r['avg_file_search_tokens']:>16.0f} | {r['avg_input_tokens']:>13.0f} | {batch_str:>15} | {inv_str:>15}")

        # Efficiency comparison
        baseline = results[0]  # sequential, 4 embeddings
        print(f"\n{'Efficiency vs Sequential (4 emb)'}")
        print(f"{'-'*100}")
        print(f"{'Configuration':<25} | {'Speedup':<12} | {'Time Saved':<12} | {'API Call Reduction':<20}")
        print(f"{'-'*25}-+-{'-'*12}-+-{'-'*12}-+-{'-'*20}")

        for r in results[1:]:
            speedup = baseline['total_time'] / r['total_time'] if r['total_time'] > 0 else 0
            time_saved = baseline['total_time'] - r['total_time']
            api_reduction = (baseline['api_calls'] - r['api_calls']) / baseline['api_calls'] * 100 if baseline['api_calls'] > 0 else 0
            config_name = f"{r['mode']}, {r['embeddings']} emb"
            print(f"{config_name:<25} | {speedup:>10.2f}x | {time_saved:>10.2f}s | {api_reduction:>18.1f}%")

        print(f"\n{'='*120}\n")

    else:
        # Single configuration run
        MODE = "batched"
        NUM_EMBEDDINGS = 4

        experiment_dir = os.path.join(base_dir, "experiments", "batch_sizes_embeddings")
        output_dir = os.path.join(experiment_dir, f"{model_names[id]}_{DATASET}_bs{BATCH_SIZE}_emb{NUM_EMBEDDINGS}")
        os.makedirs(output_dir, exist_ok=True)

        print(f"\n{'='*80}")
        print(f"VALIDATOR OPTIMIZATION TEST")
        print(f"{'='*80}")
        print(f"Model: {model_names[id]}")
        print(f"Mode: {MODE}")
        print(f"Embeddings: {NUM_EMBEDDINGS}")
        print(f"Dataset: {DATASET}")
        print(f"Input: {input_test_set_path}")
        print(f"Output: {output_dir}")
        print(f"{'='*80}\n")

        # Reset timing
        timing = get_timing_stats()
        timing.reset()

        # Run validator
        if MODE == "batched":
            run_validator_batched(clients[id], model_names[id], input_test_set_path, output_dir, vs_id, reasoning_efforts[id], NUM_EMBEDDINGS)
        else:
            run_validator(clients[id], model_names[id], input_test_set_path, output_dir, vs_id, reasoning_efforts[id], NUM_EMBEDDINGS)

        # Print timing summary
        print(f"\n{'='*80}")
        print(f"TIMING SUMMARY - {MODE.upper()} MODE - {DATASET.upper()} SET - {NUM_EMBEDDINGS} EMBEDDINGS")
        print(f"{'='*80}")
        timing.print_summary()

        # Save timing stats
        timing_stats_path = os.path.join(output_dir, "timing_stats.json")
        timing.save_to_file(timing_stats_path)
        print(f"\nTiming statistics saved to: {timing_stats_path}")
