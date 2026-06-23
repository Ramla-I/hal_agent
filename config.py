from defs import UserContext, Manufacturer, ContextRetrievalParameters, ContextRetrievalMethod
from openai import OpenAI
import json
import os
from pathlib import Path

GROQ_BASE_URL = "https://api.groq.com/openai/v1"


def _load_groq_keys() -> list[str]:
    """Groq API keys as a pool. Reads GROQ_API_KEYS (JSON array, also accepts
    comma-separated); falls back to the single GROQ_API_KEY. Add keys from
    DIFFERENT Groq accounts/orgs to multiply the effective rate limit — just
    extend the array, no code change."""
    raw = os.environ.get("GROQ_API_KEYS", "").strip()
    keys: list[str] = []
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                keys = [str(k).strip() for k in parsed if str(k).strip()]
        except json.JSONDecodeError:
            keys = [k.strip() for k in raw.split(",") if k.strip()]
    if not keys:
        single = os.environ.get("GROQ_API_KEY")
        if single:
            keys = [single.strip()]
    return keys


GROQ_API_KEYS = _load_groq_keys()
# One client per key — the call layer (utils/llm.py) round-robins across these.
GROQ_CLIENTS = [OpenAI(api_key=k, base_url=GROQ_BASE_URL) for k in GROQ_API_KEYS]

client_openai = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
)

# Backward-compat singleton (first key); prefer GROQ_CLIENTS via the call layer.
client_groq = GROQ_CLIENTS[0] if GROQ_CLIENTS else OpenAI(
    api_key=os.environ.get("GROQ_API_KEY"), base_url=GROQ_BASE_URL,
)

DEVICE_NAME = "rm0041"

# Tiktoken encoding for chunking
TIKTOKEN_ENCODING = "o200k_harmony"

CONTEXT_RETRIEVAL_PARAMETERS = ContextRetrievalParameters(
    context_retrieval_method=ContextRetrievalMethod.LOCAL_VECTOR_DB,
    pages_after_keyword=0,
    remove_tables=False,
    number_embeddings=2,
    re_ranking=False,
    score_threshold=0.0,
    vs_id="",
    regex="",
    # Contiguous chunk expansion (for semantic search)
    chunk_expansion_enabled=True,
    pages_after=1,
    chunk_index_path="chunked_datasheets/stm/rm0041/chunks/md/chunks_index.csv",
    expand_table_pages_only=False,
    # Local vector DB parameters (D2 experiment — best found accuracy)
    local_db_name="rm0041_md_chunks",
    keyword_boost=False,
    reranker_type="local",
    metadata_filter_enabled=True,
)

# Keyword search alternative:
# CONTEXT_RETRIEVAL_PARAMETERS = ContextRetrievalParameters(
#     context_retrieval_method=ContextRetrievalMethod.KEYWORD_SEARCH,
#     pages_after_keyword=2,
#     remove_tables=True,
#     number_embeddings=16,
#     re_ranking=True,
#     score_threshold=0.25,
#     vs_id="",
#     regex="",
#     chunk_expansion_enabled=True,
#     pages_after=2,
#     chunk_index_path=""
# )

# --- Model routing & per-stage model lists -------------------------------
# Models that route to the Groq key pool; every other model routes to OpenAI.
# Groq TPM limits are PER-MODEL, so each Groq model here carries its own budget —
# adding a second Groq model is an alternative to adding another API key.
GROQ_MODELS = {"gpt-oss-120b", "llama-3.3-70b-versatile"}

# Ordered list of acceptable models per LLM stage: the call layer tries them in
# order and overflows to the next when one is persistently rate-limited (e.g.
# Groq TPM exhausted → fall back to a second Groq model, then a low-cost OpenAI
# model). EDIT THESE LISTS to change what each stage runs and its fallbacks.
# Generator overflow: gpt-oss-120b (best quality) → llama-3.3-70b-versatile
# (separate Groq TPM budget, slightly weaker on structure) → gpt-5-nano (OpenAI).
STAGE_MODELS = {
    "generator":         ["gpt-oss-120b", "llama-3.3-70b-versatile", "gpt-5-nano"],
    "analyzer":          ["gpt-5-nano"],
    "coverage_improver": ["gpt-5.2"],
    "validator":         ["gpt-oss-120b"],
}

# MODEL_NAME = "gpt-4o"
GENERATOR_MODEL_NAME = "gpt-oss-120b"
GENERATOR_BATCHED = False  # Use per-peripheral batched generator (fewer LLM calls)
GENERATOR_ITER = 1 # Number of iterations for the generator agent

COVERAGE_IMPROVER_MODEL_NAME = "gpt-5.2"
COVERAGE_IMPROVER_REASONING_EFFORT = "medium"
COVERAGE_IMPROVER_ITERATIONS = 5

VALIDATOR_MODEL_NAME = "gpt-oss-120b"
VALIDATOR_REASONING_EFFORT = None

RUN_ANALYZER = True

OUTPUT_DIR = "agent_output"
RESULTS_DIR = "evaluation"
DEVICE_DIRECTORY = "devices"

# Logging configuration
LOG_LEVEL = "ERROR"  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FILE = "hal_agent.log"  # Path to log file (relative to project root or absolute path)
LOG_TO_CONSOLE = True  # Also emit logs to the console (env: HAL_AGENT_LOG_TO_CONSOLE)
# Level can be overridden per-run via env HAL_AGENT_LOG_LEVEL (e.g. INFO for progress).

# Device registry lives in config_devices.json (data, not source) so it can be
# updated programmatically without rewriting this module — see scripts/update_config.py.
DEVICE_REGISTRY_PATH = Path(__file__).resolve().parent / "config_devices.json"


def load_user_contexts(registry_path: Path = DEVICE_REGISTRY_PATH) -> list[UserContext]:
    """Build the list of UserContexts from the JSON device registry."""
    with open(registry_path, "r", encoding="utf-8") as f:
        registry = json.load(f)
    return [
        UserContext(
            device_name=d["device_name"],
            peripheral_name=d.get("peripheral_name", ""),
            manufacturer=Manufacturer[d["manufacturer"]],
            driver_path=d.get("driver_path", ""),
            run=d.get("run", 0),
            file_id=d.get("file_id", ""),
            vs_id=d.get("vs_id", ""),
        )
        for d in registry["devices"]
    ]


user_contexts = load_user_contexts()
