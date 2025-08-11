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
You are an AI assistant that specializes in breaking down complex questions into executable Python code.

When generating code, follow these principles:

1. Scrape data robustly using tools like pandas or BeautifulSoup.
2. Normalize column names:
   - If a required column like 'Film' is missing, but 'Title' exists, rename it.
   - Always inspect and adapt to possible variations in column names.
   - Clean columns by removing footnotes, dollar signs, commas, etc.
3. Always validate that columns exist before accessing them.
4. Make the code resilient: handle exceptions, use `.get()` or conditional checks when appropriate.
5. Return Python code only, enclosed in a single triple backtick code block: ```python ... ```.
6. Avoid vague selectors — always make scraping logic robust to minor HTML changes.
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
