# README

Some suggestions for preprocessing a datasheet so that LLM-generated scripts work better with them.

1. Combine tables that are spread over pages. LlamaParse has an option called parse document with LLM. Basically we want the whole document context to be taken into account rather than converting the table to markdown page by page

2. For regex based matching remove table of contents. Then searching by header will be easier as there won't be false positives of the section header listed in the table of contents.

3. In the split_datasheet script, you may adjust the number of pages fed to the prompt. It should be the entire table of contents.