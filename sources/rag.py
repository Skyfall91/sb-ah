"""RAG system: embed wiki chunks with sentence-transformers, store in ChromaDB."""
from __future__ import annotations
import os

os.environ.setdefault("HF_HUB_VERBOSITY", "error")

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "chroma_db")


def _get_collection():
    import chromadb
    client = chromadb.PersistentClient(path=DB_PATH)
    return client.get_or_create_collection("wiki")


def build_index(chunks: list[dict], verbose: bool = True) -> None:
    from sentence_transformers import SentenceTransformer

    if verbose:
        print("Loading embedding model...")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    collection = _get_collection()
    collection.delete(where={"title": {"$ne": ""}})  # clear existing

    texts = [c["text"] for c in chunks]
    ids = [f"{c['title']}_{c['chunk_index']}" for c in chunks]
    metadatas = [{"title": c["title"], "chunk_index": c["chunk_index"]} for c in chunks]

    batch_size = 256
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i + batch_size]
        batch_ids = ids[i:i + batch_size]
        batch_meta = metadatas[i:i + batch_size]
        embeddings = model.encode(batch_texts, show_progress_bar=False).tolist()
        collection.add(documents=batch_texts, embeddings=embeddings,
                       ids=batch_ids, metadatas=batch_meta)
        if verbose:
            print(f"  Indexed {min(i + batch_size, len(texts))}/{len(texts)} chunks")

    if verbose:
        print(f"Index built with {len(texts)} chunks.")


def retrieve(query: str, k: int = 8) -> list[str]:
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("all-MiniLM-L6-v2")
    embedding = model.encode([query])[0].tolist()
    collection = _get_collection()
    results = collection.query(query_embeddings=[embedding], n_results=k)
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    return [f"### {m['title']}\n{d}" for d, m in zip(docs, metas)]


def index_exists() -> bool:
    return os.path.exists(DB_PATH)
