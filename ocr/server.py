from fastapi import FastAPI, UploadFile, File
from paddleocr import PaddleOCR
import tempfile
import shutil

app = FastAPI()

# Load OCR engine ONCE at startup (expensive)
ocr_engine = PaddleOCR(use_angle_cls=True, lang="en")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/ocr")
async def run_ocr(file: UploadFile = File(...)):
    # Save uploaded file to a temp file on disk
    tmp_dir = "/opt/paddleocr/tmp"
    with tempfile.NamedTemporaryFile(delete=False, dir=tmp_dir) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    # Run OCR
    result = ocr_engine.ocr(tmp_path, cls=True)

    # Parse into simpler structure
    parsed = []
    for block in result:
        for line in block:
            text = line[1][0]
            confidence = line[1][1]
            parsed.append({"text": text, "confidence": confidence})

    return {
        "file_name": file.filename,
        "results": parsed
    }

