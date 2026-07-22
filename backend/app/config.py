"""
Central configuration. Values are read from environment variables (loaded
from a local .env file via python-dotenv) so no secrets ever live in
source control.
"""
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()  # reads backend/.env if present; does nothing if it's missing


@dataclass
class Settings:
    groq_api_key: str = os.environ.get("GROQ_API_KEY", "")
    # Text/reasoning model — Groq's current recommended general-purpose model.
    model: str = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
    # Vision model — Groq's only multimodal option as of writing. It's a
    # preview model (eval-only per Groq's own docs, not a production SLA),
    # so keep an eye on console.groq.com/docs/vision for changes.
    vision_model: str = os.environ.get("GROQ_VISION_MODEL", "qwen/qwen3.6-27b")

    # Vector store (RAG knowledge base) location
    chroma_persist_dir: str = os.environ.get("CHROMA_DIR", "./chroma_db")
    knowledge_base_dir: str = os.environ.get("KB_DIR", "./app/rag/knowledge_base")

    # Safety / compliance
    enable_deidentification: bool = os.environ.get("ENABLE_DEID", "true").lower() == "true"
    log_raw_documents: bool = False  # never log unredacted patient data

    max_upload_mb: int = 15


settings = Settings()
