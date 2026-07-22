"""
Extraction Agent
----------------
Turns de-identified raw report text into structured JSON: vitals, labs,
findings, medications mentioned. Downstream agents work off this structure
instead of re-parsing free text every time.
"""
import json
from dataclasses import dataclass
from typing import Any, Dict

from groq import Groq

from ..config import settings

client = Groq(api_key=settings.groq_api_key)

SYSTEM_PROMPT = """You extract structured data from a de-identified medical report.
Return ONLY valid JSON (no markdown fences, no preamble) matching this schema:

{
  "report_type": string,
  "vitals": [{"name": string, "value": string, "unit": string, "reference_range": string, "flag": "normal"|"low"|"high"|"critical"|"unknown"}],
  "lab_results": [{"name": string, "value": string, "unit": string, "reference_range": string, "flag": "normal"|"low"|"high"|"critical"|"unknown"}],
  "findings": [string],
  "medications_mentioned": [string],
  "impressions_as_written": [string]
}

Rules:
- Only extract what is explicitly present in the text. Never infer or invent values.
- If a section is absent, return an empty array for it.
- Do not include any patient identifiers even if present in the text.
"""


@dataclass
class ExtractionResult:
    data: Dict[str, Any]


def extract(deidentified_text: str) -> ExtractionResult:
    resp = client.chat.completions.create(
        model=settings.model,
        max_completion_tokens=2000,
        response_format={"type": "json_object"},  # Groq's JSON mode - enforced server-side
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": deidentified_text},
        ],
    )
    raw = (resp.choices[0].message.content or "").strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {"parse_error": True, "raw_output": raw}

    return ExtractionResult(data=data)
