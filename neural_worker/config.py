MODEL_NAME = "gpt-4o"

DEFAULT_MAP_PROMPT = \
"""
The given data is the {}st page of the document. 
Decode it into {} markup preserving every text block, table etc. 
Wrap inline equations with '$ EQUATION $' and separate with '$$\\n EQUATION \\n$$'. DONT PLACE ANY MUMBERS AFTER IT!
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
Dont place any numbers after the equations.
If you work with LaTeX, add all the necessary packages in the beginning.
Always put '```{}' before and '```' after doc respectively.

Pages:
{}
"""
REDUCE_SPLITTER = "---!!!---"

SAVE_DIR = "processed_docs"
