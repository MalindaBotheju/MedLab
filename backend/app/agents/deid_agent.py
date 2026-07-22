"""
De-identification Agent
------------------------
Runs BEFORE anything else touches an external API, a log file, or disk.

This is a baseline regex/heuristic redactor (fast, offline, no data leaves
the process). For real deployments, swap in a proper clinical NLP
de-identifier (e.g. Microsoft Presidio with a medical recognizer set, or a
dedicated PHI-scrubbing model) — regex alone WILL miss things like unusual
name formats or free-text narrative fields. Treat this module as a
starting point, not a compliance guarantee.
"""
import re
from dataclasses import dataclass


PHI_PATTERNS = {
    "date": re.compile(r"\b(0?[1-9]|1[0-2])[/\-](0?[1-9]|[12]\d|3[01])[/\-](\d{2,4})\b"),
    "mrn": re.compile(r"\b(MRN|Medical Record Number)[:#]?\s*\d{4,12}\b", re.IGNORECASE),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "phone": re.compile(r"\b\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    "email": re.compile(r"\b[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}\b"),
    "zip": re.compile(r"\b\d{5}(?:-\d{4})?\b"),
}

# Very common report header fields that carry direct identifiers.
NAME_FIELD_PATTERN = re.compile(
    r"(?im)^(patient\s*name|name|dob|date of birth|address|phone|guarantor)\s*[:\-]\s*.+$"
)


@dataclass
class DeidResult:
    redacted_text: str
    redaction_count: int


def deidentify(text: str) -> DeidResult:
    count = 0
    out = text

    out, n = NAME_FIELD_PATTERN.subn(lambda m: m.group(1) + ": [REDACTED]", out)
    count += n

    for label, pattern in PHI_PATTERNS.items():
        out, n = pattern.subn(f"[REDACTED-{label.upper()}]", out)
        count += n

    return DeidResult(redacted_text=out, redaction_count=count)
