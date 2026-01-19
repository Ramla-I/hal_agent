"""
Example usage of ResultSaver to demonstrate how to refactor existing code.

This file shows before/after examples of how to use ResultSaver in place of
manual file operations.
"""

from result_saver import ResultSaver, UsageStats
from defs import CoverageImproverOutput  # Example Pydantic model


# ============================================================================
# EXAMPLE 1: Coverage Improver (coverage_improver.py)
# ============================================================================

def run_coverage_improver_example_old_way(output_dir: str, model_name: str, usage, output, coverage_info, reasoning):
    """OLD WAY - Manual file operations"""
    import os
    import json
    
    # Write output
    output_path = os.path.join(output_dir, "coverage_improver_output.json")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(output.model_dump_json(indent=2))
    
    output_coverage_info_path = os.path.join(output_dir, "coverage_info.json")
    with open(output_coverage_info_path, "w", encoding="utf-8") as f:
        f.write(coverage_info.model_dump_json(indent=2))
    
    # Write reasoning if available
    if reasoning:
        reasoning_path = os.path.join(output_dir, "coverage_improver_reasoning.txt")
        with open(reasoning_path, "w", encoding="utf-8") as f:
            f.write(reasoning)
    
    # Write usage
    output_usage_path = os.path.join(output_dir, "usage.csv")
    if not os.path.exists(output_usage_path):
        with open(output_usage_path, "w", encoding="utf-8") as f:
            f.write("model_name,input_tokens,cached_tokens,output_tokens,reasoning_tokens,total_tokens\n")
    with open(output_usage_path, "a", encoding="utf-8") as f:
        f.write(f"{model_name},{usage.input_tokens},{usage.input_tokens_details.cached_tokens},{usage.output_tokens},{usage.output_tokens_details.reasoning_tokens},{usage.total_tokens}\n")


def run_coverage_improver_example_new_way(output_dir: str, model_name: str, usage, output, coverage_info, reasoning):
    """NEW WAY - Using ResultSaver"""
    saver = ResultSaver(output_dir)
    
    # Write output
    saver.save_json(output, "coverage_improver_output.json")
    saver.save_json(coverage_info, "coverage_info.json")
    
    # Write reasoning if available
    if reasoning:
        saver.save_text(reasoning, "coverage_improver_reasoning.txt")
    
    # Write usage
    usage_stats = UsageStats.from_response_usage(model_name, usage)
    saver.save_usage_stats(usage_stats, "usage.csv")


# ============================================================================
# EXAMPLE 2: Generator (s1a_generator.py)
# ============================================================================

def run_generator_example_old_way(info_dir: str, peripheral_name: str, register_name: str, model_name: str, usage_list, reasoning, json_data):
    """OLD WAY - Manual file operations"""
    import os
    
    usage_path = os.path.join(info_dir, "usage.csv")
    if not os.path.exists(usage_path):
        with open(usage_path, "w", encoding="utf-8") as usage_file:
            usage_file.write("peripheral_name,register_name,model_name,input_tokens,cached_tokens,output_tokens,reasoning_tokens,total_tokens\n")
    
    total_input_tokens = sum(u.input_tokens for u in usage_list)
    total_cached_tokens = sum(u.input_tokens_details.cached_tokens for u in usage_list)
    total_output_tokens = sum(u.output_tokens for u in usage_list)
    total_reasoning_tokens = sum(u.output_tokens_details.reasoning_tokens for u in usage_list)
    total_total_tokens = sum(u.total_tokens for u in usage_list)
    
    with open(usage_path, "a", encoding="utf-8") as usage_file:
        usage_file.write(f"{peripheral_name},{register_name},{model_name},{total_input_tokens},{total_cached_tokens},{total_output_tokens},{total_reasoning_tokens},{total_total_tokens}\n")
    
    reasoning_path = os.path.join(info_dir, "reasoning.txt")
    with open(reasoning_path, "a", encoding="utf-8") as reasoning_file:
        reasoning_file.write(f"---{peripheral_name}_{register_name}---\n{reasoning}\n\n")
    
    if json_data:
        output_path = os.path.join(output_dir, f"{peripheral_name}_{register_name}")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(json_data, indent=2))


def run_generator_example_new_way(info_dir: str, peripheral_name: str, register_name: str, model_name: str, usage_list, reasoning, json_data, output_dir: str):
    """NEW WAY - Using ResultSaver"""
    import json
    from result_saver import ResultSaver, UsageStats
    
    saver_info = ResultSaver(info_dir)
    saver_output = ResultSaver(output_dir)
    
    # Calculate totals
    total_input_tokens = sum(u.input_tokens for u in usage_list)
    total_cached_tokens = sum(u.input_tokens_details.cached_tokens for u in usage_list)
    total_output_tokens = sum(u.output_tokens for u in usage_list)
    total_reasoning_tokens = sum(u.output_tokens_details.reasoning_tokens for u in usage_list)
    total_total_tokens = sum(u.total_tokens for u in usage_list)
    
    # Save usage with additional fields
    usage_stats = UsageStats(
        model_name=model_name,
        input_tokens=total_input_tokens,
        cached_tokens=total_cached_tokens,
        output_tokens=total_output_tokens,
        reasoning_tokens=total_reasoning_tokens,
        total_tokens=total_total_tokens
    )
    saver_info.save_usage_stats(
        usage_stats,
        "usage.csv",
        additional_fields={
            'peripheral_name': peripheral_name,
            'register_name': register_name
        }
    )
    
    # Save reasoning
    saver_info.save_reasoning(
        reasoning,
        "reasoning.txt",
        prefix=f"---{peripheral_name}_{register_name}---"
    )
    
    # Save JSON output
    if json_data:
        saver_output.save_json(json_data, f"{peripheral_name}_{register_name}")


# ============================================================================
# EXAMPLE 3: Validator (validator_optimization.py)
# ============================================================================

def run_validator_example_old_way(output_dir: str, model_name: str, peripheral_name: str, register_name: str, field_name: str, key: str, usage, json_data, true_value: str):
    """OLD WAY - Manual file operations"""
    import os
    
    output_file_path = os.path.join(output_dir, f"validator_output_{model_name}_rm0041.csv")
    output_file = open(output_file_path, "w", encoding="utf-8")
    output_file.write("peripheral_name, register_name, field_name, key, value, true_value, agent_judgement, confidence_score\n")
    output_file.write(f"{peripheral_name}, {register_name}, {field_name}, {key}, {value}, {true_value}, {json_data['is_true']}, {json_data['confidence_score']}\n")
    
    usage_file_path = os.path.join(output_dir, f"validator_usage_{model_name}_rm0041.csv")
    usage_file = open(usage_file_path, "w", encoding="utf-8")
    usage_file.write("peripheral_name, register_name, field_name, key, input_tokens, cached_tokens, output_tokens, reasoning_tokens, total_tokens\n")
    usage_file.write(f"{peripheral_name}, {register_name}, {field_name}, {key}, {usage.input_tokens}, {usage.input_tokens_details.cached_tokens}, {usage.output_tokens}, {usage.output_tokens_details.reasoning_tokens}, {usage.total_tokens}\n")


def run_validator_example_new_way(output_dir: str, model_name: str, peripheral_name: str, register_name: str, field_name: str, key: str, value: str, usage, json_data, true_value: str):
    """NEW WAY - Using ResultSaver"""
    saver = ResultSaver(output_dir)
    
    # Save validator output
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
        f"validator_output_{model_name}_rm0041.csv"
    )
    
    # Save usage with additional fields
    usage_stats = UsageStats.from_response_usage(model_name, usage)
    saver.save_usage_stats(
        usage_stats,
        f"validator_usage_{model_name}_rm0041.csv",
        additional_fields={
            'peripheral_name': peripheral_name,
            'register_name': register_name,
            'field_name': field_name,
            'key': key
        }
    )


# ============================================================================
# EXAMPLE 4: Summary file (s1a_generator.py)
# ============================================================================

def save_summary_old_way(info_dir: str, context_retrieval_parameters, model_name: str):
    """OLD WAY - Manual file operations"""
    import os
    
    summary_path = os.path.join(info_dir, "summary.txt")
    with open(summary_path, "w", encoding="utf-8") as summary_file:
        summary_file.write(f"CONTEXT_RETRIEVAL_METHOD: {context_retrieval_parameters.context_retrieval_method.value}\n")
        summary_file.write(f"----PAGES_AFTER_KEYWORD: {context_retrieval_parameters.pages_after_keyword}\n")
        summary_file.write(f"----REMOVE_TABLES: {context_retrieval_parameters.remove_tables}\n")
        summary_file.write(f"----NUMBER_EMBEDDINGS: {context_retrieval_parameters.number_embeddings}\n")
        summary_file.write(f"----RE_RANKING: {context_retrieval_parameters.re_ranking}\n")
        summary_file.write(f"----REGEX: {context_retrieval_parameters.regex}\n")
        summary_file.write(f"----OTHER: {context_retrieval_parameters.other}\n\n")
        summary_file.write(f"MODEL: {model_name}\n")


def save_summary_new_way(info_dir: str, context_retrieval_parameters, model_name: str):
    """NEW WAY - Using ResultSaver"""
    saver = ResultSaver(info_dir)
    
    summary_content = f"""CONTEXT_RETRIEVAL_METHOD: {context_retrieval_parameters.context_retrieval_method.value}
----PAGES_AFTER_KEYWORD: {context_retrieval_parameters.pages_after_keyword}
----REMOVE_TABLES: {context_retrieval_parameters.remove_tables}
----NUMBER_EMBEDDINGS: {context_retrieval_parameters.number_embeddings}
----RE_RANKING: {context_retrieval_parameters.re_ranking}
----REGEX: {context_retrieval_parameters.regex}
----OTHER: {context_retrieval_parameters.other}

MODEL: {model_name}
"""
    saver.save_text(summary_content, "summary.txt")

