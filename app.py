import os
import uvicorn
import tempfile
import shutil
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import PlainTextResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict

from analyzer import analyze

app = FastAPI(title="TDS Data Analyst Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/", response_class=PlainTextResponse)
async def root(questions: List[UploadFile] = File(...)):
    """
    Accepts multipart form-data. Must include `questions.txt`.
    Returns **only** the JSON string produced by the agent (no extra text).
    """
    workdir = tempfile.mkdtemp(prefix="agent_")
    try:
        saved: Dict[str, str] = {}
        questions_path = None

        for uf in questions:
            target = os.path.join(workdir, uf.filename)
            with open(target, "wb") as f:
                f.write(await uf.read())
            saved[uf.filename] = target
            filename = uf.filename.lower()
            if filename in ["questions.txt", "question.txt"]:
                questions_path = target

        if not questions_path:
            return PlainTextResponse("{\"error\": \"questions.txt is required\"}", status_code=400)

        # Run analysis (LLM + generated code)
        result = analyze(questions_path, saved)

        # `analyze` returns a dict with keys: ok, body (string)
        if not result.get("ok"):
            # Surface the error in a JSON envelope to avoid evaluator parse issues
            return PlainTextResponse(result.get("body", "{\"error\": \"analysis failed\"}"), status_code=200)

        # Return EXACT text (LLM-generated JSON string)
        body = result["body"].strip()
        return PlainTextResponse(body, media_type="application/json")

    finally:
        try:
            shutil.rmtree(workdir, ignore_errors=True)
        except Exception:
            pass

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))