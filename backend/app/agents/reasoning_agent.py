"""
Reasoning / Synthesis Agent
----------------------------
Combines structured extraction + RAG context into a clinician-review-ready
summary. Explicitly instructed to avoid definitive diagnosis language and
avoid concrete prescriptions — see guardrail_agent.py for the enforcement
layer that double-checks this.
"""
import json
from dataclasses import dataclass
from typing import Any, Dict

from groq import Groq

from ..config import settings

client = Groq(api_key=settings.groq_api_key)

SYSTEM_PROMPT = """You are a clinical decision-support assistant. You are NOT a
doctor and your output will always be reviewed by a licensed clinician before
any action is taken on it. Given structured report data and retrieved
reference context, produce:

1. A plain-language summary of the report.
2. A list of abnormal findings, each with severity (routine / needs follow-up / urgent).
3. Possible differential considerations — framed as "may be associated with", never as a diagnosis.
4. Suggested next steps (e.g. "recommend correlating with clinical history", "consider specialist referral") — never a specific drug name + dose.
5. A short disclaimer.

Return ONLY valid JSON, no markdown fences, with keys:
summary, abnormal_findings (array of {finding, severity, note}), differential_considerations (array of strings),
suggested_next_steps (array of strings), disclaimer (string).

Rules:
- Never state a definitive diagnosis.
- Never output a specific medication name with a dose or instructions to take it.
- If any finding could indicate an acute/emergency condition, say so plainly in severity="urgent" and mention seeking immediate care.
- Ground differential considerations in the retrieved context provided; do not invent sources.
"""


@dataclass
class ReasoningResult:
    data: Dict[str, Any]


def reason(extraction: Dict[str, Any], research_context: Dict[str, list]) -> ReasoningResult:
    user_payload = json.dumps(
        {"extracted_data": extraction, "retrieved_context": research_context}, indent=2
    )

    resp = client.chat.completions.create(
        model=settings.model,
        max_completion_tokens=2500,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_payload},
        ],
    )
    raw = (resp.choices[0].message.content or "").strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {"parse_error": True, "raw_output": raw}

    return ReasoningResult(data=data)
