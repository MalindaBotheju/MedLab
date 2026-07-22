# Medical Report Analysis Agent (Scaffold)

A multi-agent pipeline that reads an uploaded medical report (PDF/image) and
produces a structured, clinician-review-ready summary. This is a **starting
scaffold**, not a certified medical device or compliance-ready product —
read the "Before you go further" section before using it with real patient
data.

## Architecture

```
 Upload (PDF/image)
        │
        ▼
 1. Ingestion Agent        — vision-based OCR/transcription
        │
        ▼
 2. De-identification      — strips PHI before anything else touches it
        │
        ▼
 3. Extraction Agent       — raw text → structured JSON (labs, vitals, findings)
        │
        ▼
 4. Research Agent (RAG)   — retrieves grounding context from a curated
        │                     knowledge base (Chroma vector store)
        ▼
 5. Reasoning Agent        — synthesizes summary, flags, differential
        │                     considerations, next steps
        ▼
 6. Guardrail Agent        — deterministic checks: no diagnosis language,
        │                     no concrete dosing, disclaimer enforced
        ▼
 Structured report → frontend
```

Each agent is a separate module under `backend/app/agents/` so you can
swap, test, or replace any stage independently (e.g. swap the reasoning
agent's model, or point the research agent at a different vector store).

## Model provider: Groq

This scaffold uses [Groq](https://console.groq.com) instead of a paid
Anthropic API key, since Groq has a usable free tier. Two models are used:

- **`openai/gpt-oss-120b`** for the extraction and reasoning agents (text-only,
  structured JSON output via Groq's JSON mode).
- **`qwen/qwen3.6-27b`** for the ingestion agent's vision/OCR step — this is
  currently Groq's only multimodal model. Groq documents it as a **preview
  model intended for evaluation, not production** — if this pipeline moves
  toward real use, keep an eye on
  [console.groq.com/docs/vision](https://console.groq.com/docs/vision) for a
  production-rated replacement, and don't be surprised if the model ID
  changes (Groq deprecates and swaps models fairly often — check
  [console.groq.com/docs/deprecations](https://console.groq.com/docs/deprecations)
  if something stops working).

Get a free API key at [console.groq.com/keys](https://console.groq.com/keys).

## Why this shape

- **De-identification runs first**, before extraction or any external API
  call, so PHI is scrubbed as early as possible in the pipeline.
- **RAG grounds the reasoning step** in a knowledge base you control,
  instead of relying purely on the model's parametric memory for medical
  facts.
- **The guardrail agent is deterministic (no LLM call)** — regex/rule-based
  checks that can't be prompted around, catching things like concrete
  drug-dose language or definitive-diagnosis phrasing before output ever
  reaches a user.
- **Output is framed as decision support**, not a final answer — every
  report carries a disclaimer and urgent findings are flagged distinctly.

## Project structure

```
medical-ai-agent/
├── .gitignore                   # keeps .env, venvs, caches out of git
├── README.md
├── backend/
│   ├── .env.example             # template — copy to .env and fill in your key
│   ├── requirements.txt
│   ├── index_kb.py              # run once to build the RAG vector index
│   └── app/
│       ├── config.py            # loads .env, holds all settings
│       ├── main.py              # FastAPI app, /analyze endpoint
│       ├── orchestrator.py      # wires the 6 agents together in sequence
│       ├── agents/
│       │   ├── ingestion_agent.py    # PDF/image -> raw text (vision OCR)
│       │   ├── deid_agent.py         # strips PHI before anything else runs
│       │   ├── extraction_agent.py   # raw text -> structured JSON
│       │   ├── research_agent.py     # RAG lookup per abnormal finding
│       │   ├── reasoning_agent.py    # synthesizes the clinician-facing summary
│       │   └── guardrail_agent.py    # deterministic safety checks, no LLM call
│       └── rag/
│           ├── vector_store.py       # Chroma wrapper (index + retrieve)
│           └── knowledge_base/       # your curated reference material goes here
└── frontend/
    └── index.html                # upload UI, calls the backend /analyze endpoint
```

## Setup

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Copy the template and put your real key in .env (gitignored, never committed)
cp .env.example .env
# then edit .env and set GROQ_API_KEY=your_actual_key

# Build the RAG index from knowledge_base/ (replace the example file first!)
python index_kb.py

# Run the API
uvicorn app.main:app --reload --port 8000
```

Then open `frontend/index.html` directly in a browser (or serve it with any
static server). It calls `http://localhost:8000` by default — change
`API_BASE` in the `<script>` tag if you deploy the backend elsewhere.

## Before you go further — read this

This scaffold gets the pipeline shape right, but several things need real
work before this touches actual patient data:

1. **De-identification is a regex baseline, not a guarantee.** Swap in a
   proper clinical de-identifier (e.g. Microsoft Presidio with medical
   recognizers, or a dedicated PHI-scrubbing model) before handling real
   reports. Free-text narrative sections are where regex fails hardest.

2. **The knowledge base is a placeholder.** `backend/app/rag/knowledge_base/`
   ships with one example file. Populate it with vetted, licensed reference
   material you actually have rights to use — condensed guideline
   summaries, reference-range tables, drug class monographs.

3. **This is not a diagnostic device.** By design, the reasoning and
   guardrail agents block definitive-diagnosis language and concrete
   dosing instructions. Keep it that way unless you go through the
   regulatory process required for actual diagnostic/prescriptive
   software (e.g. FDA SaMD clearance in the US) — that's a legal
   requirement, not just a nicety.

4. **Compliance depends on your jurisdiction and use case.** If this ever
   touches real patient data: encryption at rest and in transit, access
   controls, audit logging, a signed Business Associate Agreement with any
   cloud API provider (for HIPAA in the US), and a documented data
   retention/deletion policy are all things you'll need — this scaffold
   does not include them.

5. **Add human sign-off before anything reaches a patient.** The frontend
   should sit in front of a clinician's workflow, not a patient-facing app,
   unless there is direct clinical oversight of every output.

## Extending it

- **Swap orchestration** for [LangGraph](https://github.com/langchain-ai/langgraph)
  once you need branching (e.g. route to a different reasoning path for
  radiology vs lab reports) or parallel agent fan-out.
- **Add an evaluation harness** — a set of sample de-identified reports with
  expected extractions, run on every change to catch regressions in the
  extraction/reasoning agents.
- **Add persistence** (Postgres) if you need to store reports/reports history
  — with encryption and per-user access control from day one.
