# hal_agent
hal_agent is an AI-powered tool designed to extract, interpret, and summarize hardware register information from device datasheets, with a focus on embedded systems (e.g., STM32 microcontrollers). It leverages OpenAI's agents SDK to automate the process of parsing datasheets, identifying register details, and mapping them to driver code, streamlining hardware abstraction layer (HAL) development and documentation. 

## Prerequisites
1. Install OpenAI agents-SDK (https://openai.github.io/openai-agents-python/quickstart/)
2. Set an OpenAI API key (https://platform.openai.com/docs/quickstart#create-and-export-an-api-key)

## Parameters
1. Preprocessing - In config.py, you can change the way the agent retrieves context from the datasheet by setting the CURRENT_PREPROCESSING_METHOD parameter.

## Testing with an Existing Device
1. register_info_agent.py contains the most recent version of the agent
2. Set the device name in config.py for the device you want to run the agent for. (Currently only STM devices)
3. Run `python3 register_info_agent.py`


## Adding a New Device
1. Add the reference manual and svd files to the devices folder, right now the copy_files script in stm32-rs project does that
2. Add the device to the config.py file (init/update_config.py)
3. Run the preprocessing steps to generate a vector store (preprocessing/create_vector_store.py) -- TODO: automatically update config.py
4. Split the datasheet if STM ref manual (preprocessing/split_datasheet.py) - TODO: make it so that the split can occur the first time the fn is called
5. Make sure the entry in config has all the up to date information