"""Run once (and whenever you update knowledge_base/) to (re)build the index:
    python index_kb.py
"""
from app.rag.vector_store import index_knowledge_base

if __name__ == "__main__":
    n = index_knowledge_base()
    print(f"Indexed {n} chunk(s) into the vector store.")
