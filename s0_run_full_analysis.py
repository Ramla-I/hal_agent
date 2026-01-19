#!/usr/bin/env python3
import os
import sys
import subprocess
import glob
import config
import asyncio
import json
import csv

from s1a_generator import run_generator
from scripts.s2_compare_agent_output_with_svd import compare_agent_output_with_svd
from s5_analyzer import run_analyzer
from scripts.s4_generate_diff_table import generate_diff_table
from scripts.s5_compare_diff_with_verified_output import compare_diff_with_verified_datasheet
from scripts.update_config import update_user_context
from preprocessing.create_vector_store_openai import create_vector_store
from scripts.calculate_generator_coverage import calculate_generator_coverage
from s2_coverage_improver import run_coverage_improver
from defs import CoverageImproverOutput
from config import client_openai, client_groq

def resolve_repo_root() -> str:
    """Return absolute path to the repository root."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__)))

def determine_client(model_name: str) -> Groq|OpenAI:
    return client_groq if model_name == "gpt-oss-120b" else client_openai

async def main() -> None:
    repo_root = resolve_repo_root()
    sys.path.insert(0, repo_root)

    device_name = config.DEVICE_NAME
    context_retrieval_parameters = config.CONTEXT_RETRIEVAL_PARAMETERS
    # Generator settings
    generator_model_name = config.GENERATOR_MODEL_NAME
    generator_client = determine_client(generator_model_name)
    # Coverage improver settings
    coverage_improver_model_name = config.COVERAGE_IMPROVER_MODEL_NAME
    coverage_improver_client = determine_client(coverage_improver_model_name)
    coverage_improver_reasoning_effort = config.COVERAGE_IMPROVER_REASONING_EFFORT
    coverage_improver_iterations = config.COVERAGE_IMPROVER_ITERATIONS
    # Validator settings
    validator_model_name = config.VALIDATOR_MODEL_NAME
    validator_client = determine_client(validator_model_name)
    validator_reasoning_effort = config.VALIDATOR_REASONING_EFFORT
    # Analyzer settings
    analyzer = config.RUN_ANALYZER

    # Find run number for the current device in config.user_contexts
    run_number = None
    device_ctx = None
    for ctx in getattr(config, "user_contexts", []):
        if getattr(ctx, "device_name", None) == device_name:
            device_ctx = ctx
            run_number = str(getattr(ctx, "run"))
            break
    if run_number is None:
        raise RuntimeError(f"Run number not found for device '{device_name}' in config.user_contexts")

    # Build absolute paths
    device_directory = os.path.join(repo_root, config.DEVICE_DIRECTORY, device_ctx.manufacturer.value.lower(), device_ctx.device_name)
    svd_dir = os.path.join(device_directory, "svd")
    agent_output_folder = os.path.join(repo_root, config.OUTPUT_DIR, device_ctx.manufacturer.value.lower(), device_name, run_number)
    results_directory = os.path.join(repo_root, config.RESULTS_DIR, device_ctx.manufacturer.value.lower(), device_name, run_number)
    verified_datasheet_directory = os.path.join(repo_root, "verified_datasheet")

    # Update the context_retrieval_parameters with the vs_id from the device_ctx
    if device_ctx.vs_id != "":
        context_retrieval_parameters.vs_id = device_ctx.vs_id
    else:
        pdf_path = os.path.join(device_directory, f"{device_name}.pdf")
        vs_id, file_id = create_vector_store(pdf_path, device_name)
        device_ctx.vs_id = vs_id
        device_ctx.file_id = file_id
        update_user_context(device_ctx)

    for i in range(coverage_improver_iterations):
        # ---- (S1) Run generator agent ----
        generator_truncated_at_any_register = run_generator(
            client=generator_client, 
            model_name=generator_model_name, 
            device_name=device_name, 
            run_number=run_number, 
            device_dir=device_directory, 
            agent_output_dir=agent_output_folder, 
            context_retrieval_parameters=context_retrieval_parameters, 
            manufacturer=device_ctx.manufacturer,
            peripherals_registers_dict=None
        )

        # Run the validator on the agent output
        invariants = build_invariants_from_agent_output(agent_output_folder)
        validator_output_dir = os.path.join(agent_output_folder, "validator")
        os.makedirs(validator_output_dir, exist_ok=True)
        true_count, false_count = run_validator(
            client=validator_client,
            model_name=validator_model_name,
            invariants=invariants,
            output_dir=validator_output_dir,
            vs_id=device_ctx.vs_id,
            reasoning_effort=validator_reasoning_effort
        )
        print("Coverage improver iteration: ", i)
        print("Coverage improver model: ", coverage_improver_model_name)
        print(f"True count: {true_count}, False count: {false_count}")
        
        # ---- (S2) Feeedback Loop with Coverage Improver ----
        # Get the coverage of the agent output
        svd_files = sorted([f for f in glob.glob(os.path.join(svd_dir, "*.svd"))])
        if not svd_files:
            raise RuntimeError(f"No svd files found in {svd_dir}")
        svd_path = svd_files[0]
        coverage_info = calculate_generator_coverage(svd_path, agent_output_folder)
       
        # Call coverage improver with information about the coverage, context retrieval parameters, 
        coverage_improver_output_dir = os.path.join(agent_output_folder, "coverage_improver")
        os.makedirs(coverage_improver_output_dir, exist_ok=True)
        run_coverage_improver(
            coverage_improver_client, 
            coverage_improver_model_name, 
            coverage_info, 
            context_retrieval_parameters, 
            coverage_improver_output_dir, 
            device_ctx.vs_id, 
            coverage_improver_reasoning_effort, 
            generator_truncated_at_any_register
        )
       
        # Output should be an updated context retrieval parameters and reasoning.
        coverage_improver_output = CoverageImproverOutput.model_validate_json(open(os.path.join(coverage_improver_output_dir, "coverage_improver_output.json")).read())
        stop_improving = coverage_improver_output.stop_improving
        if stop_improving:
            break
        context_retrieval_parameters = coverage_improver_output.context_retrieval_parameters
        context_retrieval_parameters.vs_id = device_ctx.vs_id # just to make sure model didn't change it
       
        # update the run number and corresponding directories
        run_number = str(int(run_number) + 1)
        device_ctx.run = run_number
        update_user_context(device_ctx)
        agent_output_folder = os.path.join(repo_root, config.OUTPUT_DIR, device_ctx.manufacturer.value.lower(), device_name, run_number)
        results_directory = os.path.join(repo_root, config.RESULTS_DIR, device_ctx.manufacturer.value.lower(), device_name, run_number)

    exit()
    # ---- (S2) Compare agent output with SVD for each SVD file ----
    svd_files = sorted([f for f in glob.glob(os.path.join(svd_dir, "*.svd"))])
    if not svd_files:
        raise RuntimeError(f"No svd files found in {svd_dir}")

    for svd_path in svd_files:
        svd_file_base = os.path.splitext(os.path.basename(svd_path))[0]
        custom_results_dir = os.path.join(results_directory, svd_file_base)
        os.makedirs(custom_results_dir, exist_ok=True)
        print(f"Comparing agent output with SVD for: {svd_file_base}")
        compare_agent_output_with_svd(svd_path, agent_output_folder, custom_results_dir)

    # ---- (S3) Run the analyzer agent on the results ----
    if analyzer:
        for svd_path in svd_files:
            svd_file_base = os.path.splitext(os.path.basename(svd_path))[0]
            register_diff_csv_path = os.path.join(results_directory, svd_file_base, "register_diff.csv")
            analyzer_output_dir = os.path.join(agent_output_folder, "analyzer_iteration")
            os.makedirs(analyzer_output_dir, exist_ok=True)
            print(f"Running analyzer for: {svd_file_base}")
            await run_analyzer(model_name, svd_file_base, register_diff_csv_path, analyzer_output_dir)
            
            # Filter the register_diff.csv file to only include the rows that are in the analyzer output
            analyzer_output_path = os.path.join(analyzer_output_dir, f"{svd_file_base}")
            analyzer_register_diff_csv_path = register_diff_csv_path.replace('.csv', '_analyzer.csv')
            with open(analyzer_output_path, 'r') as f:
                ids = json.load(f)['bugs']
                # Now filter rows from register_diff.csv to register_diff_analyzer.csv
                with open(register_diff_csv_path, 'r') as inf, open(analyzer_register_diff_csv_path, 'w') as outf:
                    reader = csv.reader(inf)
                    writer = csv.writer(outf)
                    input_header = next(reader)
                    writer.writerow(input_header)
                    for row in reader:
                        if row and (int(row[0]) in ids or row[3] == 'fields'):
                            writer.writerow(row)

    # ---- (S4) Generate the diff table ----
    for svd_path in svd_files:
        svd_file_base = os.path.splitext(os.path.basename(svd_path))[0]
        custom_results_dir = os.path.join(results_directory, svd_file_base)
        generate_diff_table(custom_results_dir, analyzer)

    # ---- (S5) Compare the diff table with the verified output ----
    for svd_path in svd_files:
        svd_file_base = os.path.splitext(os.path.basename(svd_path))[0]
        custom_results_dir = os.path.join(results_directory, svd_file_base)

        verified_csv_path = os.path.join(verified_datasheet_directory, f"{device_name}_{svd_file_base}.csv")
        if not os.path.exists(verified_csv_path):
            print(f"Verified CSV not found for {svd_file_base}")
            continue
        # Compare the register diff with the verified output
        register_diff_csv_path = os.path.join(custom_results_dir, "register_diff.csv")
        register_diff_verified_csv_path = os.path.join(custom_results_dir, "register_diff_verified.csv")
        compare_diff_with_verified_datasheet(register_diff_csv_path, verified_csv_path, register_diff_verified_csv_path)
        # Additionally, run compare_diff_with_verified_output.py with 'field_diff.csv' instead of 'register_diff.csv'
        field_diff_csv_path = os.path.join(custom_results_dir, "field_diff.csv")
        field_diff_verified_csv_path = os.path.join(custom_results_dir, "field_diff_verified.csv")
        compare_diff_with_verified_datasheet(field_diff_csv_path, verified_csv_path, field_diff_verified_csv_path)


if __name__ == "__main__":
    asyncio.run(main())


