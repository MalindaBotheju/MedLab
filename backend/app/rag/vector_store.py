"""
Vector store wrapper around Chroma. Loads documents from
app/rag/knowledge_base/ (plain .txt/.md files you curate — e.g. condensed
guideline summaries, reference-range tables, drug class overviews from
sources you trust and have the right to use).

IMPORTANT: populate the knowledge_base/ directory yourself with vetted
sources. This scaffold ships with a couple of tiny example files only —
it is NOT a substitute for a real medical knowledge base.
"""
import glob
import os

import chromadb
from chromadb.utils import embedding_functions

from ..config import settings

_client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
_embed_fn = embedding_functions.DefaultEmbeddingFunction()
_collection = _client.get_or_create_collection(
    name="medical_knowledge_base", embedding_function=_embed_fn
)


def index_knowledge_base() -> int:
    """(Re)index every .txt/.md file in knowledge_base_dir. Call once on setup
    or whenever you update the source files."""
    files = glob.glob(os.path.join(settings.knowledge_base_dir, "**/*.*"), recursive=True)
    files = [f for f in files if f.endswith((".txt", ".md"))]

    ids, docs, metas = [], [], []
    for path in files:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        # naive chunking by paragraph — good enough for a starting scaffold
        for i, chunk in enumerate(c.strip() for c in content.split("\n\n") if c.strip()):
            ids.append(f"{os.path.basename(path)}::{i}")
            docs.append(chunk)
            metas.append({"source": os.path.basename(path)})

    if ids:
        _collection.upsert(ids=ids, documents=docs, metadatas=metas)
    return len(ids)


def retrieve(query: str, k: int = 5):
    results = _collection.query(query_texts=[query], n_results=k)
    hits = []
    for doc, meta, dist in zip(
        results["documents"][0], results["metadatas"][0], results["distances"][0]
    ):
        hits.append({"text": doc, "source": meta.get("source"), "distance": dist})
    return hits
