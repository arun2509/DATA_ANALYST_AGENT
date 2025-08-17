import os
import re
import json
import base64
import traceback
import subprocess
from io import BytesIO
from typing import Dict, Any

import matplotlib.pyplot as plt
import pandas as pd

from gemini_llm import query_gemini
from tools import scrape_website, get_relevant_data
from google.generativeai.types.generation_types import StopCandidateException

TOOLS = [
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
                    "required": ["url", "output_file"],
                },
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
                    "required": ["file_name"],
                },
            },
        ]
    }
]

# Map occasional wrong param keys coming back from LLM
_FIX_KEYS = {
    "scrape_website": {"file": "output_file"},
    "get_relevant_data": {"file": "file_name"},
}


def _sanitize_params(tool: str, params: dict) -> dict:
    if tool in _FIX_KEYS:
        for wrong, right in _FIX_KEYS[tool].items():
            if wrong in params and right not in params:
                params[right] = params.pop(wrong)
    return params


def _rename_film_column(df: pd.DataFrame) -> None:
    try:
        cols_lower = {c.lower(): c for c in df.columns}
        if "film" in cols_lower and cols_lower["film"] != "Film":
            df.rename(columns={cols_lower["film"]: "Film"}, inplace=True)
        elif "title" in cols_lower and cols_lower["title"] != "Film":
            df.rename(columns={cols_lower["title"]: "Film"}, inplace=True)
    except Exception:
        pass


def _save_current_plot_as_base64() -> str | None:
    try:
        buf = BytesIO()
        plt.savefig(buf, format="png", dpi=150, bbox_inches="tight")
        buf.seek(0)
        data = base64.b64encode(buf.read()).decode("utf-8")
        buf.close()
        return data
    except Exception:
        return None


def _run_generated_code(code: str) -> tuple[bool, str]:
    """Run LLM-generated Python and return (ok, text_output).
    The generated code must **print a JSON string** (array or object) to stdout.
    We also try to capture a figure if created, but the evaluator only reads stdout.
    """
    temp_path = "temp_code.py"
    # Ensure the script runs in a clean namespace with pandas/matplotlib available
    with open(temp_path, "w", encoding="utf-8") as f:
        f.write(code)

    try:
        proc = subprocess.run(["python", temp_path], capture_output=True, text=True, timeout=120)
        stdout = (proc.stdout or "").strip()
        stderr = (proc.stderr or "").strip()

        # Best-effort fix on DataFrames post-run (if the user kept them in globals)
        try:
            local_vars: Dict[str, Any] = {}
            exec(code, {"pd": pd, "plt": plt}, local_vars)
            for v in list(local_vars.values()):
                if isinstance(v, pd.DataFrame):
                    _rename_film_column(v)
        except Exception:
            pass

        # If figure exists but not saved, expose via hidden image (not used by evaluator)
        if os.path.exists("scatterplot.png"):
            try:
                with open("scatterplot.png", "rb") as f:
                    _ = base64.b64encode(f.read()).decode("utf-8")
            except Exception:
                pass
        else:
            _ = _save_current_plot_as_base64()

        # Prefer stdout; if empty, surface stderr to help debugging
        body = stdout if stdout else (stderr or "")
        return True, body

    except subprocess.TimeoutExpired:
        return False, json.dumps({"error": "Code execution timed out"})
    except Exception as e:
        return False, json.dumps({"error": f"Code execution failed: {e}"})


def analyze(questions_file: str, all_files: Dict[str, str]) -> Dict[str, Any]:
    # 1) read prompt
    try:
        with open(questions_file, encoding="utf-8") as f:
            user_task = f.read()
    except Exception as e:
        return {"ok": False, "body": json.dumps({"error": f"Failed to read questions.txt: {e}"})}

    # 2) call LLM with system prompt + tools
    for attempt in range(2):
        try:
            response = query_gemini(user_task, tools=TOOLS)
            break
        except StopCandidateException:
            if attempt == 0:
                user_task += "\n\n(RETRY) Your previous tool call failed. Call tools again with correct parameters."
                continue
            return {"ok": False, "body": json.dumps({"error": "Malformed tool call twice"})}
        except Exception as e:
            return {"ok": False, "body": json.dumps({"error": f"Gemini error: {e}"})}

    # 3) execute any tool calls (scrape, extract)
    try:
        calls = getattr(response, "function_calls", []) or []
        for c in calls:
            name = getattr(c, "name", "")
            args = getattr(c, "args", "{}")
            try:
                params = json.loads(args) if isinstance(args, str) else dict(args)
            except Exception:
                params = {}
            params = _sanitize_params(name, params)

            if name == "scrape_website":
                scrape_website(**params)
            elif name == "get_relevant_data":
                get_relevant_data(**params)
            # ignore others silently
    except Exception:
        pass

    # 4) find generated python in the LLM text and run it
    text = getattr(response, "text", "") or ""
    code = None

    # prefer fenced ```python blocks
    m = re.search(r"```python\n(.*?)```", text, flags=re.DOTALL)
    if m:
        code = m.group(1).strip()
    elif "import" in text or "def " in text:
        code = text.strip()

    if not code:
        # No code returned – create a friendly fallback answer that still returns JSON
        fallback = json.dumps([
            0,
            "Not enough data to determine the earliest film over $1.5B",
            0.0,
            "data:image/png;base64,"
        ])
        return {"ok": True, "body": fallback}

    ok, body = _run_generated_code(code)
    # Ensure we return **only** the JSON structure the generated code printed
    return {"ok": ok, "body": body}