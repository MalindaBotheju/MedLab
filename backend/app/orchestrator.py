"""
Orchestrator
------------
Sequential pipeline (simple and debuggable — swap for LangGraph/a proper
state machine once you need branching, retries, or parallel fan-out).

Flow:
  ingest -> de-identify -> extract -> research (RAG) -> reason -> guardrail
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List

from .agents import (
    deid_agent,
    extraction_agent,
    guardrail_agent,
    ingestion_agent,
    reasoning_agent,
    research_agent,
)


@dataclass
class PipelineResult:
    report: Dict[str, Any]
    trace: List[str] = field(default_factory=list)
    guardrail_issues: List[str] = field(default_factory=list)


def run_pipeline(file_bytes: bytes, filename: str, content_type: str) -> PipelineResult:
    trace: List[str] = []

    # 1. Ingestion
    if content_type == "application/pdf" or filename.lower().endswith(".pdf"):
        ingestion = ingestion_agent.ingest_pdf(file_bytes)
    else:
        ingestion = ingestion_agent.ingest_image(file_bytes, media_type=content_type or "image/png")
    trace.append(f"Ingested {len(ingestion.pages)} page(s)")

    # 2. De-identification (before anything is logged or persisted)
    deid = deid_agent.deidentify(ingestion.full_text)
    trace.append(f"De-identification redacted {deid.redaction_count} field(s)")

    # 3. Extraction
    extraction = extraction_agent.extract(deid.redacted_text)
    trace.append("Structured extraction complete")

    # 4. Research (RAG)
    research = research_agent.research(extraction.data)
    trace.append(f"Retrieved context for {len(research.context_by_topic)} topic(s)")

    # 5. Reasoning / synthesis
    reasoning = reasoning_agent.reason(extraction.data, research.context_by_topic)
    trace.append("Synthesis complete")

    # 6. Guardrail
    guardrail = guardrail_agent.check(reasoning.data)
    trace.append(f"Guardrail check: {'passed' if guardrail.passed else 'FLAGGED'}")

    return PipelineResult(
        report=guardrail.safe_output,
        trace=trace,
        guardrail_issues=guardrail.issues,
    )
