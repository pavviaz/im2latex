MODEL_NAME = "gpt-4o"
OPENAI_API = "https://api.openai.com/v1/chat/completions"

DEFAULT_MAP_PROMPT = \
"""
The given image is the {}st page of the document. 
Decode it into {} markup preserving every text block, table etc. 
Insert placeholder instead of images with coordinates of corresponding img on original screenshot. 
Write nothing more but {}.
Always put '```{}' before and '```' after doc respectively
"""
MD_REPLACER = ("md", "```md", "```")
LATEX_REPLACER = ("latex" ,"```latex", "```")

DEFAULT_REDUCE_PROMPT = \
"""
This is {}-pages document, decoded in {}.
The pages are splitted with '{}'.
Combine them into one single document, preserving all the contents.
Write nothing more but combined document.
Always put '```{}' before and '```' after doc respectively.

Pages:
{}
"""
REDUCE_SPLITTER = "---!!!---"

SAVE_DIR = "processed_docs"
