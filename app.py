from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from typing import List
import shutil
import os
from analyzer import analyze

app = FastAPI()
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/")
async def analyze_agent(files: List[UploadFile] = File(...)):
    saved_files = {}
    
    # Save uploaded files
    for file in files:
        path = os.path.join(UPLOAD_DIR, file.filename)
        with open(path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        saved_files[file.filename] = path

    # Ensure questions.txt exists
    question_file = next(
        (path for fname, path in saved_files.items() if fname.lower() == "questions.txt"),
        None
    )
    if question_file is None:
        return JSONResponse(
            status_code=400,
            content={"error": "Missing required file: questions.txt"}
        )

    try:
        # Let analyze() decide number & format of answers
        result = analyze(question_file, saved_files)

        # Must be JSON-serializable
        if not isinstance(result, (list, dict)):
            return JSONResponse(
                status_code=500,
                content={"error": "Invalid response format — must be list or dict"}
            )

        return JSONResponse(content=result)

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
