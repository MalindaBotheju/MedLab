from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from . import db
from .config import settings
from .orchestrator import run_pipeline

app = FastAPI(title="Medical Report Analysis Agent (Scaffold)")

# Tighten this for production — restrict to your actual frontend origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_TYPES = {"application/pdf", "image/png", "image/jpeg", "image/webp"}


@app.on_event("startup")
def on_startup():
    db.init_db()  # no-op if DATABASE_URL isn't set


@app.get("/health")
def health():
    return {"status": "ok", "database_configured": db.is_configured()}


@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, f"Unsupported file type: {file.content_type}")

    contents = await file.read()
    if len(contents) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(400, f"File exceeds {settings.max_upload_mb}MB limit")

    try:
        result = run_pipeline(contents, file.filename, file.content_type)
    except Exception as e:
        # In production: log the exception server-side (without patient data),
        # return a generic error to the client.
        raise HTTPException(500, f"Pipeline error: {e}")

    report_id = db.save_report(result.report, result.trace, result.guardrail_issues)

    return {
        "id": report_id,
        "report": result.report,
        "trace": result.trace,
        "guardrail_issues": result.guardrail_issues,
    }


@app.get("/reports")
def list_reports(limit: int = 50):
    return {"configured": db.is_configured(), "reports": db.list_reports(limit)}


@app.get("/reports/{report_id}")
def get_report(report_id: int):
    result = db.get_report(report_id)
    if result is None:
        raise HTTPException(404, "Report not found")
    return result