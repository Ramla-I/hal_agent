# hal_agent

1. add the reference manual and svd files to the devices folder, right now the copy_files script in stm32-rs project does that
2. Add the device to the config.py file (init/update_config.py)
3. run the preprocessing steps to generate a vector store (preprocessing/create_vector_store.py) -- need to automatically upated config.py
4. split the datasheet if STM ref manual (preprocessing/split_datasheet.py) -- need to automatically update config.py
5. make sure the entry in config has all the up to date information