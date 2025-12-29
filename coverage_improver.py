from agents import Agent, Runner, GuardrailFunctionOutput, InputGuardrail, FunctionTool, function_tool, RunContextWrapper, handoff, FileSearchTool
from agents.exceptions import InputGuardrailTripwireTriggered
from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
import asyncio  
import os

import config
from defs import CoverageImproverOutput, ContextRetrievalParameters, CoverageInfo
from prompts import coverage_improver as prompts

CURRENT_VS_ID = 'vs_6892501067b08191ac63cc6de06ee629'

@function_tool(name_override="get_keyword_seach_code")  
def get_keyword_seach_code(ctx: RunContextWrapper[ContextRetrievalParameters]) -> str:
    keyword_search_code_path = os.path.join("context_retrieval", "keyword_search.py")
    with open(keyword_search_code_path, "r") as file:
        return file.read()

@function_tool(name_override="get_semantic_search_code")  
def get_semantic_search_code(ctx: RunContextWrapper[ContextRetrievalParameters]) -> str:
    semantic_search_code_path = os.path.join("context_retrieval", "semantic_search.py")
    with open(semantic_search_code_path, "r") as file:
        return file.read()

coverage_improver_agent = Agent(
    name = "Coverage Improver",
    model="gpt-5",
    instructions=prompts.create_coverage_improver_system_prompt(),
    tools=[
        get_keyword_seach_code,
        get_semantic_search_code,
        FileSearchTool(
            max_num_results=2,
            vector_store_ids=[CURRENT_VS_ID],
            include_search_results=True,
        )
    ],
    output_type=CoverageImproverOutput,
)


async def run_coverage_improver(coverage_info: CoverageInfo, context_retrieval_parameters: ContextRetrievalParameters, output_dir: str, vs_id: str):
    global CURRENT_VS_ID
    CURRENT_VS_ID = vs_id
    print(f"Using vector store id: {CURRENT_VS_ID}")
    
    result = await Runner.run(
        coverage_improver_agent,
        prompts.create_coverage_improver_user_prompt(coverage_info, context_retrieval_parameters),
    )

    output_path = os.path.join(output_dir, "coverage_improver_output.json")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(result.final_output.model_dump_json(indent=2))
    
    output_coverage_info_path = os.path.join(output_dir, "coverage_info.json")
    with open(output_coverage_info_path, "w", encoding="utf-8") as f:
        f.write(coverage_info.model_dump_json(indent=2))
    
    usage = result.context_wrapper.usage
    output_usage_path = os.path.join(output_dir, "usage.csv")
    if not os.path.exists(output_usage_path):
        with open(output_usage_path, "w", encoding="utf-8") as f:
            f.write("model_name,input_tokens,cached_tokens,output_tokens,reasoning_tokens,total_tokens\n")
    with open(output_usage_path, "a", encoding="utf-8") as f:
        f.write(f"{config.MODEL_NAME},{usage.input_tokens},{usage.input_tokens_details.cached_tokens},{usage.output_tokens},{usage.output_tokens_details.reasoning_tokens},{usage.total_tokens}\n")
