"""
Ingestion Agent
---------------
Accepts a PDF or image of a medical report and produces raw extracted text.

Strategy:
- Images: send directly to Claude's vision endpoint for OCR + layout-aware
  transcription (handles messy scans, handwriting, tables far better than
  plain OCR).
- PDFs: render each page to an image (PyMuPDF), then run the same vision
  step per page and concatenate.

Nothing here is logged verbatim (see config.log_raw_documents).
"""
import base64
from dataclasses import dataclass
from typing import List

import fitz  # PyMuPDF
from groq import Groq

from ..config import settings

client = Groq(api_key=settings.groq_api_key)

TRANSCRIBE_PROMPT = (
    "You are transcribing a scanned medical report page. Transcribe ALL visible "
    "text exactly as written, preserving structure (headers, table rows, "
    "labeled values). Do not summarize, interpret, or omit anything. If a "
    "value is illegible, write [ILLEGIBLE]. Output plain text only."
)


@dataclass
class IngestionResult:
    pages: List[str]
    full_text: str


def _transcribe_image_bytes(image_bytes: bytes, media_type: str) -> str:
    b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
    resp = client.chat.completions.create(
        model=settings.vision_model,
        max_completion_tokens=2000,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": TRANSCRIBE_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{media_type};base64,{b64}"},
                    },
                ],
            }
        ],
    )
    return resp.choices[0].message.content or ""


def ingest_image(image_bytes: bytes, media_type: str = "image/png") -> IngestionResult:
    text = _transcribe_image_bytes(image_bytes, media_type)
    return IngestionResult(pages=[text], full_text=text)


def ingest_pdf(pdf_bytes: bytes, dpi: int = 200) -> IngestionResult:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages: List[str] = []
    zoom = dpi / 72
    matrix = fitz.Matrix(zoom, zoom)

    for page in doc:
        pix = page.get_pixmap(matrix=matrix)
        img_bytes = pix.tobytes("png")
        pages.append(_transcribe_image_bytes(img_bytes, "image/png"))

    return IngestionResult(pages=pages, full_text="\n\n--- page break ---\n\n".join(pages))
