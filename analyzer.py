# analyzer.py
import os
import json
import tempfile
import pandas as pd
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
from typing import List, Dict, Any, Tuple, Union
import io
from io import BytesIO
import base64
import subprocess
import sys

from tools.scrape_website import scrape_website
from tools.get_relevant_data import get_relevant_data
from openai_llm import query_openai


# ---------------- Helpers ----------------
def _json_default(obj):
    import numpy as np
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.ndarray,)):
        return obj.tolist()
    return str(obj)

def df_to_base64(fig) -> str:
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=80)
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return b64

def safe_preview(value):
    try:
        if isinstance(value, pd.DataFrame):
            return value.head(5).to_dict()
        return str(value)[:1000]
    except Exception as e:
        return f"[Preview error: {e}]"


# ---------------- Universal Analyzer ----------------
def analyze(
    files: List[str],
    questions: str,
    return_code: bool = False
) -> Union[Dict[str, Any], Tuple[Dict[str, Any], str]]:
    """
    Universal analyzer:
    - Handles CSV, Excel, JSON, HTML tables, or URLs (Wikipedia/others).
    - Passes preview of data + questions to OpenAI.
    - Executes generated Python code that sets `results`.
    - Always returns a clean JSON object.
    """
    extracted_data: Dict[str, Dict[str, Any]] = {}

    # Load files or scrape websites
    for f in files:
        key = os.path.basename(f)
        try:
            if f.startswith("http://") or f.startswith("https://"):
                html_file = tempfile.mktemp(suffix=".html")
                scrape_website(f, html_file)
                extracted_data[key] = get_relevant_data(html_file)
            elif f.endswith(".csv"):
                df = pd.read_csv(f)
                extracted_data[key] = {"data": df}
            elif f.endswith((".xlsx", ".xls")):
                df = pd.read_excel(f)
                extracted_data[key] = {"data": df}
            elif f.endswith(".json"):
                df = pd.read_json(f)
                extracted_data[key] = {"data": df}
            elif f.endswith(".html"):
                extracted_data[key] = get_relevant_data(f)
            else:
                with open(f, "r", encoding="utf-8") as fh:
                    extracted_data[key] = {"data": fh.read()}
        except Exception as e:
            extracted_data[key] = {"data": None, "error": str(e)}

    # Prepare LLM input
    preview_data = {k: safe_preview(v.get("data")) for k, v in extracted_data.items()}

    llm_input = f"""
You are a Python data analysis assistant.
Data (preview): {json.dumps(preview_data, indent=2)}
Question: {questions}

Generate Python code that produces a variable `results` (a JSON-serializable dict).
Rules:
- **Don't generate markdown code blocks.**
- Don't import any undefined packages.
- if the package not defined then install it using `pip install` and then regenerate the code.
- if you need to import libraries, do so at the top of the code.
- if you need to define functions, do so at the top of the code.
- Use `pd.read_csv`, `pd.read_excel`, `pd.read_json` for data loading.
- Use `plt` for plotting, and convert figures to base64 with `df_to_base64`.
- Use pandas/numpy/matplotlib as needed.
- Prefer the first table if multiple are present.
- Handle missing columns or empty data gracefully.
- If creating charts, convert matplotlib figures with df_to_base64(fig).
- `results` must always be JSON serializable (convert numpy types).
- after generating the full code, try to fix all errors and ensure it runs without issues.
- If you need to import libraries, do so at the top of the code.
- If you need to define functions, do so at the top of the code.
- If you need to use any external libraries, ensure they are imported at the top of the code.
"""

    # Query OpenAI
    code = query_openai(llm_input, model="gpt-4.1")

    # Save for debugging
    temp_code_path = os.path.join(tempfile.gettempdir(), "temp_code.py")
    with open(temp_code_path, "w", encoding="utf-8") as f:
        f.write(code)

    # Execution environment
    sandbox = {
        # core analysis libraries
        "pd": pd,
        "np": np,
        "plt": plt,
        # utilities
        "df_to_base64": df_to_base64,
        "extracted_data": extracted_data,
        "results": {},
        # common builtins / modules
        "io": io,
        "BytesIO": io.BytesIO,
        "base64": base64,
        "subprocess": subprocess,
        "os": os,
        "sys": sys,
        "json": json,
        "networkx": nx
    }
    try:
        exec(code, sandbox)   # use sandbox for globals
        results = sandbox.get("results", {})
    except Exception as e:
        results = {"error": f"Execution error: {e}"}

    if return_code:
        return results, code
    return results
