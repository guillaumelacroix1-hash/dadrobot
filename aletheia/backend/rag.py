"""Base de connaissances (RAG) — un espace de documents par agent.

Utilise ChromaDB (embeddings CPU par défaut, aucun GPU requis). Si Chroma n'est
pas installé, on retombe sur un index mot-clé naïf persisté en JSON : le labo
reste fonctionnel, simplement moins fin sur la recherche.
"""
from __future__ import annotations

import json
import re

from .config import CHROMA_DIR, DATA_DIR

_chroma_client = None
_backend = "naive"


def _get_chroma():
    global _chroma_client, _backend
    if _chroma_client is not None:
        return _chroma_client
    try:
        import chromadb

        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        _backend = "chroma"
    except Exception:  # noqa: BLE001
        _chroma_client = None
        _backend = "naive"
    return _chroma_client


def backend_name() -> str:
    _get_chroma()
    return _backend


# ----------------------------------------------------------- index naïf (repli)
_NAIVE_PATH = DATA_DIR / "naive_index.json"


def _naive_load() -> dict:
    if _NAIVE_PATH.exists():
        return json.loads(_NAIVE_PATH.read_text(encoding="utf-8"))
    return {}


def _naive_save(data: dict) -> None:
    _NAIVE_PATH.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"\w+", text.lower()))


# ------------------------------------------------------------------- API publique
def add_texts(agent_id: str, chunks: list[str], metadatas: list[dict]) -> int:
    if not chunks:
        return 0
    client = _get_chroma()
    if client is not None:
        col = client.get_or_create_collection(f"agent_{agent_id}")
        base = col.count()
        ids = [f"{agent_id}-{base + i}" for i in range(len(chunks))]
        col.add(documents=chunks, metadatas=metadatas, ids=ids)
        return len(chunks)
    # repli naïf
    data = _naive_load()
    bucket = data.setdefault(agent_id, [])
    for ch, md in zip(chunks, metadatas):
        bucket.append({"text": ch, "meta": md})
    _naive_save(data)
    return len(chunks)


def query(agent_id: str, question: str, k: int = 4) -> list[dict]:
    client = _get_chroma()
    if client is not None:
        try:
            col = client.get_or_create_collection(f"agent_{agent_id}")
            if col.count() == 0:
                return []
            res = col.query(query_texts=[question], n_results=min(k, col.count()))
            docs = res.get("documents", [[]])[0]
            metas = res.get("metadatas", [[]])[0]
            return [{"text": d, "meta": m} for d, m in zip(docs, metas)]
        except Exception:  # noqa: BLE001
            return []
    # repli naïf : score par recouvrement de mots
    data = _naive_load()
    bucket = data.get(agent_id, [])
    qtok = _tokenize(question)
    scored = []
    for item in bucket:
        score = len(qtok & _tokenize(item["text"]))
        if score:
            scored.append((score, item))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [it for _, it in scored[:k]]


def context_for(agent_id: str, question: str, k: int = 4) -> str:
    """Construit un bloc de contexte cité, prêt à injecter dans le prompt."""
    hits = query(agent_id, question, k)
    if not hits:
        return ""
    lines = []
    for h in hits:
        src = h.get("meta", {}).get("title", "source")
        lines.append(f"[{src}] {h['text']}")
    return "\n\n".join(lines)
