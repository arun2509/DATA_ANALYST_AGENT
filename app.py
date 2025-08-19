# app.py
import os
import uvicorn
import tempfile
import shutil
import json
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict
from dotenv import load_dotenv

from analyzer import analyze

load_dotenv()

app = FastAPI(title="Universal Data Analyst Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _json_default(obj):
    import numpy as np
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.ndarray,)):
        return obj.tolist()
    return str(obj)


@app.post("/", response_class=PlainTextResponse)
async def root(questions: List[UploadFile] = File(...)):
    """
    Accepts multipart form-data.
    Must include `questions.txt`.
    Other uploaded files can be CSV, Excel, JSON, HTML, or a txt file with a URL.
    Returns ONLY the JSON string produced by the analyzer.
    """
    workdir = tempfile.mkdtemp(prefix="agent_")
    try:
        saved: Dict[str, str] = {}
        questions_path = None

        # Save uploaded files
        for uf in questions:
            target = os.path.join(workdir, uf.filename)
            with open(target, "wb") as f:
                f.write(await uf.read())
            saved[uf.filename] = target
            if uf.filename.lower() in ["questions.txt", "question.txt"]:
                questions_path = target

        if not questions_path:
            return PlainTextResponse(
                json.dumps({"error": "questions.txt is required"}),
                status_code=400
            )

        # Read the question(s)
        with open(questions_path, "r", encoding="utf-8") as fh:
            questions_text = fh.read()

        # Collect other uploaded files (datasets)
        file_paths = [
            path for name, path in saved.items()
            if name.lower() not in ["questions.txt", "question.txt"]
        ]

        # Run analyzer
        results, generated_code = analyze(file_paths, questions_text, return_code=True)

        # Save last generated code for debugging
        with open("temp_code.py", "w", encoding="utf-8") as f:
            f.write(str(generated_code))

        # Dynamically include all keys from analyzer
        stable_results = {k: results.get(k, None) for k in results.keys()}

        # Return clean JSON
        return PlainTextResponse(
            json.dumps(stable_results, default=_json_default),
            media_type="application/json"
        )

    finally:
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
