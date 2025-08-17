import os
import google.generativeai as genai
from typing import List, Dict, Any
from dotenv import load_dotenv

# ✅ Load environment variables (GOOGLE_API_KEY)
load_dotenv()
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

# ✅ Use Gemini 2.5 Flash with deterministic output
model = genai.GenerativeModel(
    "gemini-2.5-flash",
    generation_config={
        "temperature": 0,         # No randomness
        "top_p": 1,
        "top_k": 1,
    }
)

# ✅ System prompt to normalize column names and ensure robustness
system_prompt = """
You are an AI assistant that converts natural language questions into robust Python code
that can scrape, process, and analyze data from Wikipedia or similar HTML pages.

Rules for generated code:
0. Don't guess or assume anything not explicitly stated, analyze only when you see the html structure.
1. Always enclose your answer in a single ```python ... ``` code block with no extra text.
2. Scraping:
   - Use pandas.read_html with html5lib or lxml to read all tables.
   - Normalize column names: strip spaces, remove footnotes ([1], [2], etc.), convert to lowercase.
   - Match columns using partial/keyword matching instead of exact names.
     Examples:
       - For country-like columns: look for keywords ['country', 'dependency', 'territory', 'nation', 'state'].
       - For population-like columns: look for keywords ['population', 'pop.', 'inhabitants'].
       - For title/film-like columns: look for keywords ['film', 'title', 'movie'].
   - If multiple tables match, choose the one with the most relevant columns.
   - If still no match, gracefully handle and return an empty DataFrame with a warning.
3. Data Cleaning:
   - Remove currency symbols, commas, spaces, footnotes, and non-numeric characters from numeric columns.
   - Convert numeric columns to int or float where possible, coercing errors to NaN and dropping NaN rows when appropriate.
   - Trim and clean text columns, removing footnotes and extra whitespace.
4. Validation:
   - Always check that a required column exists before using it.
   - If missing, try alternative matches using regex or partial matches.
5. Robustness:
   - Wrap scraping and processing in try/except with clear error messages.
   - Code must run even if Wikipedia table structures change.
6. **Output contract — very important**
   - **Print exactly one JSON value** to stdout. No extra logs, no explanations.
   - If the task asks for an array of 4 answers, print a JSON array of 4 raw values (numbers, strings, floats, URIs).
   - Example: `[1, "Titanic", 0.485782, "data:image/png;base64,iVBORw0K..."]`
   - Do not wrap values with extra wording like "The earliest film is...".
   - No explanations or markdown outside the ```python block.
"""


def query_gemini(prompt: str, tools: List[Dict[str, Any]] = None, files: List[Any] = None):
    """
    Calls Gemini with a prompt and optional tool-calling configuration.

    Args:
        prompt (str): User question or command.
        tools (list): List of tool definitions for function calling.
        files (list): Optional files (not currently used).

    Returns:
        Gemini response object (supports .text, .function_calls, etc.)
    """
    chat = model.start_chat(enable_automatic_function_calling=True)

    # Send system instruction first
    chat.send_message(system_prompt.strip())

    # Then send the actual user prompt
    response = chat.send_message(
        prompt,
        tools=tools
    )

    return response
