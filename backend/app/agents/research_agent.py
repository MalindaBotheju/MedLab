"""
Research Agent (RAG)
---------------------
For each notable finding/lab flagged non-normal, retrieves grounding
context from the curated knowledge base so the reasoning agent explains
things with cited context rather than from model memory alone.
"""
from dataclasses import dataclass
from typing import Any, Dict, List

from ..rag.vector_store import retrieve


@dataclass
class ResearchResult:
    context_by_topic: Dict[str, List[dict]]


def research(extraction: Dict[str, Any]) -> ResearchResult:
    topics = []

    for item in extraction.get("lab_results", []) + extraction.get("vitals", []):
        if item.get("flag") not in (None, "normal", "unknown"):
            topics.append(item["name"])

    topics.extend(extraction.get("findings", []))

    context_by_topic: Dict[str, List[dict]] = {}
    for topic in topics:
        context_by_topic[topic] = retrieve(topic, k=3)

    return ResearchResult(context_by_topic=context_by_topic)
