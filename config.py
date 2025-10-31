from defs import UserContext, Manufacturer, PreprocessingMethod

DEVICE_NAME = "rm0041"
SVD_FILE = "stm32f100"
CURRENT_VS_ID = "vs_6892501067b08191ac63cc6de06ee629"
CURRENT_PREPROCESSING_METHOD = PreprocessingMethod.KEYWORD_SEARCH
# MODEL_NAME = "gpt-4o"
MODEL_NAME = "gpt-oss-20b"
OUTPUT_DIR = "agent_output"
RESULTS_DIR = "evaluation/results"
GENERATOR_ITER = 1 # Number of iterations for the generator agent


user_contexts = [
    UserContext(device_name='82579', peripheral_name='', manufacturer=Manufacturer.INTEL, driver_path='devices/82579/e1000_ebb2314.rs', run=0, file_id='file-Y42TiuVyte2z2TcbsXt9sv', vs_id='vs_68924fa6726481918501140c8ac86afe'),
    UserContext(device_name='82599', peripheral_name='', manufacturer=Manufacturer.INTEL, driver_path='devices/82599/ixgbe_4a124f4.rs', run=0, file_id='file-RdWHHvaJvfkRZ59zXGjVVS', vs_id='vs_68924fdcb9cc8191809cacd7be13a9ea'),
    UserContext(device_name='rm0041', peripheral_name='', manufacturer=Manufacturer.STM, driver_path='', run=14, file_id='file-MHtC1XNEQDa2X8jNEjfk1b', vs_id='vs_6892501067b08191ac63cc6de06ee629'),
    UserContext(device_name='rm0090', peripheral_name='', manufacturer=Manufacturer.STM, driver_path='', run=2, file_id='file-CjEojSnvTNU3hpXQFG6DK5', vs_id='vs_689f5188906c81919cebc07c132a8f46'),
    UserContext(device_name='rm0091', peripheral_name='', manufacturer=Manufacturer.STM, driver_path='', run=1, file_id='file-T2XMpz886q7hQNqaDhN7Fn', vs_id='vs_689f52468484819182c9c3085572ce19'),
    UserContext(device_name='rm0360', peripheral_name='', manufacturer=Manufacturer.STM, driver_path='', run=0, file_id='file-JT7wee34qTEUtugwxW2VAP', vs_id='vs_689f52862f5881918366547ab0417608'),
    UserContext(device_name='rm0490', peripheral_name='', manufacturer=Manufacturer.STM, driver_path='', run=0, file_id='file-RygxVqtujcgLnFBQGrQ1in', vs_id='vs_689f52efc4bc8191afb9b4fb05c78f6c'),
]
