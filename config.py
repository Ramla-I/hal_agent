from defs import UserContext, Manufacturer, ContextRetrievalParameters, ContextRetrievalMethod
from openai import OpenAI
import os

client_groq = OpenAI(
    api_key=os.environ.get("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

client_openai = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
)

DEVICE_NAME = "rm0041"

# Tiktoken encoding for chunking
TIKTOKEN_ENCODING = "o200k_harmony"

CONTEXT_RETRIEVAL_PARAMETERS = ContextRetrievalParameters(
    context_retrieval_method=ContextRetrievalMethod.KEYWORD_SEARCH,
    pages_after_keyword=2,
    remove_tables=True,
    number_embeddings=16,
    re_ranking=True,
    score_threshold=0.25,
    vs_id="",
    regex="",
    # Contiguous chunk expansion (for semantic search)
    chunk_expansion_enabled=True,
    pages_after=2,
    chunk_index_path=""
)

# Local Vector DB example (ChromaDB + FastEmbed, free and offline):
# CONTEXT_RETRIEVAL_PARAMETERS = ContextRetrievalParameters(
#     context_retrieval_method=ContextRetrievalMethod.LOCAL_VECTOR_DB,
#     pages_after_keyword=0,
#     remove_tables=False,
#     number_embeddings=5,
#     re_ranking=False,
#     score_threshold=0.0,
#     vs_id="",
#     regex="",
#     local_db_name="rm0041_md",     # ChromaDB database name
#     keyword_boost=True,             # Hybrid semantic + keyword matching
#     reranker_type="local",          # FlashRank local reranker ("", "local", "cohere", "bge")
# )

# MODEL_NAME = "gpt-4o"
GENERATOR_MODEL_NAME = "gpt-oss-120b"
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

user_contexts = [
    UserContext(device_name='82579', peripheral_name='', manufacturer=Manufacturer.INTEL, driver_path='devices/82579/e1000_ebb2314.rs', run=0, file_id='file-Y42TiuVyte2z2TcbsXt9sv', vs_id='vs_68924fa6726481918501140c8ac86afe', vs_id_text='', vs_id_md=''),
    UserContext(device_name='82599', peripheral_name='', manufacturer=Manufacturer.INTEL, driver_path='devices/82599/ixgbe_4a124f4.rs', run=0, file_id='file-RdWHHvaJvfkRZ59zXGjVVS', vs_id='vs_68924fdcb9cc8191809cacd7be13a9ea', vs_id_text='', vs_id_md=''),
    UserContext(device_name='rm0008', peripheral_name='', manufacturer=Manufacturer.STM, driver_path='', run=2, file_id='file-D98Cj39QhHMHNdXLNxewq7', vs_id='vs_693a0971872881918852f40b15c29fa1', vs_id_text='', vs_id_md=''),
    UserContext(device_name='rm0033', peripheral_name='', manufacturer=Manufacturer.STM, driver_path='', run=1, file_id='file-CmfGB6SWzkxDpHdXSGRWY7', vs_id='vs_693a093c1ce48191a0bb9e6630f090b5', vs_id_text='', vs_id_md=''),
    UserContext(device_name='rm0041', peripheral_name='', manufacturer=Manufacturer.STM, driver_path='', run=21, file_id='file-MHtC1XNEQDa2X8jNEjfk1b', vs_id='vs_6892501067b08191ac63cc6de06ee629', vs_id_text='vs_69739f0610d8819183584c2d343e88a6', vs_id_md='vs_6973a4df01bc81919940212995712255'),
    UserContext(device_name='rm0090', peripheral_name='', manufacturer=Manufacturer.STM, driver_path='', run=3, file_id='file-CjEojSnvTNU3hpXQFG6DK5', vs_id='vs_689f5188906c81919cebc07c132a8f46', vs_id_text='', vs_id_md=''),
    UserContext(device_name='rm0091', peripheral_name='', manufacturer=Manufacturer.STM, driver_path='', run=2, file_id='file-T2XMpz886q7hQNqaDhN7Fn', vs_id='vs_689f52468484819182c9c3085572ce19', vs_id_text='', vs_id_md=''),
    UserContext(device_name='rm0360', peripheral_name='', manufacturer=Manufacturer.STM, driver_path='', run=1, file_id='file-JT7wee34qTEUtugwxW2VAP', vs_id='vs_689f52862f5881918366547ab0417608', vs_id_text='', vs_id_md=''),
    UserContext(device_name='rm0490', peripheral_name='', manufacturer=Manufacturer.STM, driver_path='', run=1, file_id='file-RygxVqtujcgLnFBQGrQ1in', vs_id='vs_689f52efc4bc8191afb9b4fb05c78f6c', vs_id_text='', vs_id_md=''),
    UserContext(device_name='ke04', peripheral_name='', manufacturer=Manufacturer.NXP, driver_path='', run=3, file_id='file-HXurUicV6dJUZqMjbKWRWk', vs_id='vs_693b01dc21608191914afb688556c220', vs_id_text='', vs_id_md=''),
    UserContext(device_name='s32k1xx', peripheral_name='', manufacturer=Manufacturer.NXP, driver_path='', run=1, file_id='', vs_id='', vs_id_text='', vs_id_md=''),
    UserContext(device_name='msp430g2', peripheral_name='', manufacturer=Manufacturer.TI, driver_path='', run=2, file_id='file-XbEecafgtidnALoE4qarHz', vs_id='vs_693b0615f51481919e951ae03d5b471e', vs_id_text='', vs_id_md=''),
]
