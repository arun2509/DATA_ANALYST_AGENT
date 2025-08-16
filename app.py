from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from typing import Optional
import shutil
import os
from analyzer import analyze

TEMP_FILE = "temp_code.py"
if os.path.exists(TEMP_FILE):
    os.remove(TEMP_FILE)
    print(f"Deleted old {TEMP_FILE}")

app = FastAPI()
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/")
async def analyze_agent(
    questions: UploadFile = File(..., alias="questions.txt"),
    image: Optional[UploadFile] = File(None, alias="image.png"),
    data: Optional[UploadFile] = File(None, alias="data.csv")
):
    saved_files = {}

    # Save questions.txt (required)
    q_path = os.path.join(UPLOAD_DIR, "questions.txt")
    with open(q_path, "wb") as f:
        shutil.copyfileobj(questions.file, f)
    saved_files["questions.txt"] = q_path

    # Save image.png (optional)
    if image:
        img_path = os.path.join(UPLOAD_DIR, "image.png")
        with open(img_path, "wb") as f:
            shutil.copyfileobj(image.file, f)
        saved_files["image.png"] = img_path

    # Save data.csv (optional)
    if data:
        csv_path = os.path.join(UPLOAD_DIR, "data.csv")
        with open(csv_path, "wb") as f:
            shutil.copyfileobj(data.file, f)
        saved_files["data.csv"] = csv_path

    try:
        # Run analyzer with paths
        result = analyze(saved_files["questions.txt"], saved_files)

        # Ensure JSON serializable
        if not isinstance(result, (list, dict)):
            return JSONResponse(
                status_code=500,
                content={"error": "Invalid response format — must be list or dict"}
            )

        return JSONResponse(content=result)

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
