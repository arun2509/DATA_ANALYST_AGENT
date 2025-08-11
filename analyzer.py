import os
import subprocess
import base64
from io import BytesIO
from typing import List, Dict, Any
import json
import re
import matplotlib.pyplot as plt
import pandas as pd
import traceback
import shutil  # ✅ added for cleanup

from gemini_llm import query_gemini  # Your Gemini wrapper
from tools import scrape_website, get_relevant_data
from google.generativeai.types.generation_types import StopCandidateException

tools = [
    {
        "function_declarations": [
            {
                "name": "scrape_website",
                "description": "Scrapes a website and saves the content to a file",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL to scrape"},
                        "output_file": {"type": "string", "description": "Output HTML file"},
                    },
                    "required": ["url", "output_file"]
                }
            },
            {
                "name": "get_relevant_data",
                "description": "Extract data from a local HTML file using a CSS selector",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_name": {"type": "string", "description": "Path to HTML file"},
                        "js_selector": {"type": "string", "description": "CSS selector"},
                    },
                    "required": ["file_name", "js_selector"]
                }
            }
        ]
    }
]

# 🛠 Fix parameter names if Gemini sends wrong keys
def sanitize_tool_params(tool_name: str, params: dict) -> dict:
    fixes = {
        "scrape_website": {"file": "output_file"},
        "get_relevant_data": {"file": "file_name"}
    }
    if tool_name in fixes:
        for wrong, correct in fixes[tool_name].items():
            if wrong in params and correct not in params:
                params[correct] = params.pop(wrong)
    return params

# 🔄 Auto-rename Film/Title column
def rename_film_column(df: pd.DataFrame) -> pd.DataFrame:
    try:
        cols_lower = {c.lower(): c for c in df.columns}
        if "film" in cols_lower:
            df.rename(columns={cols_lower["film"]: "Title"}, inplace=True)
        elif "title" in cols_lower:
            df.rename(columns={cols_lower["title"]: "Film"}, inplace=True)
    except Exception as e:
        print(f"[WARN] Could not rename Film/Title column: {e}")
    return df

# 🖼️ Save plot as base64
def save_plot_as_base64():
    try:
        buf = BytesIO()
        plt.savefig(buf, format="png")
        buf.seek(0)
        image_base64 = base64.b64encode(buf.read()).decode("utf-8")
        buf.close()
        return image_base64
    except Exception as e:
        print(f"[WARN] Failed to save plot as base64: {e}")
        return None

# 🧠 Run Gemini-generated code safely
def run_code_and_capture_output(code: str) -> List[Dict[str, Any]]:
    temp_code_path = "temp_code.py"
    try:
        with open(temp_code_path, "w", encoding="utf-8") as f:
            f.write(code)
    except Exception as e:
        return [{"type": "text", "output": f"❌ Failed to write code file: {e}"}]

    try:
        result = subprocess.run(
            ["python", temp_code_path],
            capture_output=True, text=True, timeout=60
        )
        output = (result.stdout or "") + (result.stderr or "")

        # Attempt to inspect DataFrames & fix Film/Title mismatch
        try:
            local_vars = {}
            exec(code, {"pd": pd, "plt": plt}, local_vars)
            for v in local_vars.values():
                if isinstance(v, pd.DataFrame):
                    rename_film_column(v)
        except Exception as e:
            print(f"[WARN] Failed to inspect DataFrames: {e}")

        # Capture image
        image_base64 = None
        try:
            if os.path.exists("scatterplot.png"):
                with open("scatterplot.png", "rb") as f:
                    image_base64 = base64.b64encode(f.read()).decode("utf-8")
            else:
                image_base64 = save_plot_as_base64()
        except Exception as e:
            print(f"[WARN] Failed to read plot image: {e}")

        response = [{"type": "text", "output": output.strip() or "✅ Code executed, but no textual output."}]
        if image_base64:
            response.append({"type": "image", "output": f"data:image/png;base64,{image_base64}"})
        return response

    except subprocess.TimeoutExpired:
        return [{"type": "text", "output": "⏱️ Code execution timed out!"}]
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"[ERROR] Code execution failed:\n{error_trace}")
        return [{"type": "text", "output": f"❌ Code execution failed: {str(e)}"}]

# 📊 Main analysis entrypoint
def analyze(questions_file: str, all_files: Dict[str, str]) -> List[Dict[str, Any]]:
    # Load questions
    try:
        with open(questions_file, encoding="utf-8") as f:
            prompt = f.read()
    except Exception as e:
        return [{"type": "text", "output": f"❌ Failed to read questions file: {e}"}]

    # Call Gemini safely with retry on MALFORMED_FUNCTION_CALL
    for attempt in range(2):  # First try + one retry
        try:
            response = query_gemini(prompt, tools=tools)
            break  # Success, exit retry loop
        except StopCandidateException as e:
            if attempt == 0:
                print(f"[WARN] Gemini returned malformed function call. Retrying...")
                prompt += "\n\nYour last tool call failed due to malformed parameters. Please retry with correctly formatted parameters."
                continue  # Retry once
            else:
                error_trace = traceback.format_exc()
                print(f"[ERROR] Gemini returned malformed function call after retry:\n{error_trace}")
                return [{"type": "text", "output": "⚠️ Gemini failed twice due to malformed tool parameters. No valid answer could be generated."}]
        except Exception as e:
            error_trace = traceback.format_exc()
            print(f"[ERROR] Gemini query failed:\n{error_trace}")
            return [{"type": "text", "output": f"❌ Gemini query failed: {str(e)}"}]

    # Save Gemini response for debugging
    try:
        response_text = getattr(response, "text", str(response))
        with open("gpt_response.json", "w", encoding="utf-8") as f:
            json.dump({"text": response_text}, f, indent=2)
    except Exception as e:
        print(f"[WARN] Failed to save Gemini response: {e}")

    # Handle tool calls
    if hasattr(response, "function_calls"):
        for tool_call in response.function_calls:
            try:
                function_name = tool_call.name
                parameters = json.loads(tool_call.args)
                parameters = sanitize_tool_params(function_name, parameters)

                if function_name == "scrape_website":
                    scrape_website(**parameters)
                elif function_name == "get_relevant_data":
                    get_relevant_data(**parameters)
            except Exception as e:
                print(f"[WARN] Tool execution failed for {tool_call.name}: {e}")

    # If Gemini returned code, execute it
    if hasattr(response, "text"):
        full_text = response.text or ""
        match = re.search(r"```python(.*?)```", full_text, re.DOTALL)
        if match:
            return run_code_and_capture_output(match.group(1).strip())
        if "import" in full_text or "def " in full_text:
            return run_code_and_capture_output(full_text.strip())

    return [{"type": "text", "output": "🤷 No usable code returned by Gemini."}]
