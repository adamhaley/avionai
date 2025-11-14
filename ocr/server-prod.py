import io
import os
from typing import List, Any

import numpy as np
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from paddleocr import PaddleOCR
from pdf2image import convert_from_bytes
from PIL import Image
import uvicorn

# ---------- Config ----------
OCR_LANG = os.getenv("PADDLE_LANG", "en")
OCR_PORT = int(os.getenv("PADDLE_PORT", "6000"))
OCR_HOST = os.getenv("PADDLE_HOST", "0.0.0.0")

# ---------- App + CORS ----------
app = FastAPI(title="PaddleOCR Microservice", version="1.0.0")

# Adjust allowed origins as needed (for n8n Cloud, put your domain here)
allowed_origins = os.getenv("PADDLE_ALLOWED_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- OCR Engine ----------
ocr_engine = PaddleOCR(
    use_textline_orientation=True,   # replaces use_angle_cls
    lang=OCR_LANG
)


def normalize_result(ocr_raw: List[Any]) -> List[dict]:
    """
    Normalize PaddleOCR result into a friendly list of dicts:
    [
      { "bbox": [[x1,y1]..[x4,y4]], "text": "...", "confidence": 0.99 },
      ...
    ]
    """
    normalized = []
    # ocr_raw is typically [ [ [box, (txt, conf)], ... ] ]
    for block in ocr_raw:
        for line in block:
            box, (txt, conf) = line
            normalized.append(
                {
                    "bbox": box,
                    "text": txt,
                    "confidence": float(conf),
                }
            )
    return normalized

# ---------- Endpoints ----------

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/ocr")
async def ocr_endpoint(file: UploadFile = File(...)):
    """
    Accepts a PDF or image and returns OCR results per page.

    Response shape:
    {
      "filename": "lease-summary.pdf",
      "pages": [
        {
          "page": 1,
          "results": [ {bbox, text, confidence}, ... ]
        },
        ...
      ]
    }
    """
    content = await file.read()
    filename = file.filename or "document"
    content_type = file.content_type or ""

    pages_output = []

    is_pdf = filename.lower().endswith(".pdf") or content_type == "application/pdf"

    if is_pdf:
        # Convert each PDF page to PIL Image
        images = convert_from_bytes(content, dpi=300)
        for idx, img in enumerate(images, start=1):
            img_np = np.array(img.convert("RGB"))
            raw = ocr_engine.ocr(img_np, cls=True)
            pages_output.append(
                {
                    "page": idx,
                    "results": normalize_result(raw),
                }
            )
    else:
        # Assume it's a single image
        img = Image.open(io.BytesIO(content)).convert("RGB")
        img_np = np.array(img)
        raw = ocr_engine.ocr(img_np, cls=True)
        pages_output.append(
            {
                "page": 1,
                "results": normalize_result(raw),
            }
        )

    return {
        "filename": filename,
        "pages": pages_output,
    }

if __name__ == "__main__":
    uvicorn.run(app, host=OCR_HOST, port=OCR_PORT)

