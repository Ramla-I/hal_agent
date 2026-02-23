#!/usr/bin/env python3
import os
import sys
from pathlib import Path

# Add parent directory to path to import from core/
sys.path.insert(0, str(Path(__file__).parent.parent))

import subprocess
import glob
import config
import asyncio
import json
import csv

from core.s1a_generator import run_generator
from scripts.s2_compare_agent_output_with_svd import compare_agent_output_with_svd
from core.s5_analyzer import run_analyzer
from scripts.s4_generate_diff_table import generate_diff_table
from scripts.s5_compare_diff_with_verified_output import compare_diff_with_verified_datasheet
from scripts.update_config import update_user_context
from context_retrieval.preprocessing.old.create_vector_store_openai import create_vector_store
from scripts.calculate_generator_coverage import calculate_generator_coverage
from core.s2_coverage_improver import run_coverage_improver
from defs import CoverageImproverOutput
from config import client_openai, client_groq
from groq import Groq
from openai import OpenAI
from core.s4_validator import build_invariants_from_agent_output, run_validator
from defs import ContextRetrievalParameters

def resolve_repo_root() -> str:
    """Return absolute path to the repository root."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

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
    # Validator settings
    validator_model_name = config.VALIDATOR_MODEL_NAME
    validator_client = determine_client(validator_model_name)
    validator_reasoning_effort = config.VALIDATOR_REASONING_EFFORT

    # Coverage improver settings
    coverage_improver_model_names = ["gpt-4.1-nano", "gpt-5-nano", "gpt-5.2", "gpt-oss-120b"]
    coverage_improver_clients = [determine_client(model_name) for model_name in coverage_improver_model_names]
    coverage_improver_reasoning_efforts = [None, "low", None, None]
    coverage_improver_iterations = config.COVERAGE_IMPROVER_ITERATIONS

    id = 2

    coverage_improver_model_name = coverage_improver_model_names[id]
    coverage_improver_client = coverage_improver_clients[id]
    coverage_improver_reasoning_effort = coverage_improver_reasoning_efforts[id]

    # Find run number for the current device in config.user_contexts
    run_number = 1
    device_ctx = None
    for ctx in getattr(config, "user_contexts", []):
        if getattr(ctx, "device_name", None) == device_name:
            device_ctx = ctx
            break

    # Build absolute paths
    device_directory = os.path.join(repo_root, config.DEVICE_DIRECTORY, device_ctx.manufacturer.value.lower(), device_ctx.device_name)
    svd_dir = os.path.join(device_directory, "svd")
    agent_output_folder = os.path.join(repo_root, "coverage_improver_optimization", device_name, coverage_improver_model_name, str(run_number))

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
        print(f"Running generator for {coverage_improver_model_name} iteration {i}")
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
        print(f"Running validator for {coverage_improver_model_name} iteration {i}")
        invariants = build_invariants_from_agent_output(agent_output_folder)
        validator_output_dir = os.path.join(agent_output_folder, "validator")
        os.makedirs(validator_output_dir, exist_ok=True)
        true_count, false_count = run_validator(
            client=validator_client,
            model_name=validator_model_name,
            invariants=invariants,
            output_dir=validator_output_dir,
            context_retrieval_parameters=context_retrieval_parameters,
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
        print(f"Running coverage improver for {coverage_improver_model_name} iteration {i}")
        coverage_improver_output_dir = os.path.join(agent_output_folder, "coverage_improver")
        os.makedirs(coverage_improver_output_dir, exist_ok=True)
        run_coverage_improver(
            coverage_improver_client,
            coverage_improver_model_name,
            coverage_info,
            context_retrieval_parameters,
            coverage_improver_output_dir,
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
        agent_output_folder = os.path.join(repo_root, "coverage_improver_optimization", device_name, coverage_improver_model_name, str(run_number))

   
if __name__ == "__main__":
    asyncio.run(main())


