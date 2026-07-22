"""
Guardrail Agent
----------------
Last line of defense before output reaches the user. Deterministic checks —
no LLM call, so it can't be talked out of enforcing the rules.
"""
import re
from dataclasses import dataclass
from typing import Any, Dict, List

BANNED_PATTERNS = [
    re.compile(r"\byou have\b.*\b(cancer|diabetes|disease|syndrome)\b", re.IGNORECASE),
    re.compile(r"\btake\b.*\b\d+\s?(mg|mcg|ml|units?)\b", re.IGNORECASE),  # concrete dosing
    re.compile(r"\bdiagnosis\s*:\s*", re.IGNORECASE),
]

REQUIRED_DISCLAIMER_SNIPPET = "not a substitute"


@dataclass
class GuardrailResult:
    passed: bool
    issues: List[str]
    safe_output: Dict[str, Any]


def check(reasoning_output: Dict[str, Any]) -> GuardrailResult:
    issues: List[str] = []
    text_blob = str(reasoning_output)

    for pattern in BANNED_PATTERNS:
        if pattern.search(text_blob):
            issues.append(f"Blocked pattern matched: {pattern.pattern}")

    disclaimer = reasoning_output.get("disclaimer", "")
    if REQUIRED_DISCLAIMER_SNIPPET not in disclaimer.lower():
        reasoning_output["disclaimer"] = (
            "This is AI-generated decision support and is not a substitute for "
            "professional medical judgment. All findings must be reviewed by a "
            "licensed clinician before any clinical decision is made."
        )

    urgent = [
        f for f in reasoning_output.get("abnormal_findings", [])
        if f.get("severity") == "urgent"
    ]
    if urgent:
        reasoning_output["urgent_review_required"] = True

    return GuardrailResult(
        passed=len(issues) == 0,
        issues=issues,
        safe_output=reasoning_output,
    )
