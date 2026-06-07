"""Ingestion multi-source vers la base de connaissances d'un agent.

Sources : texte, PDF/livre, page web, YouTube (transcription auto), audio/vidéo
(transcription Whisper via Groq). Chaque source garde sa provenance.

Toutes les dépendances « lourdes » sont importées paresseusement : si l'une
manque, seule cette source-là est indisponible, le reste du labo fonctionne.
"""
from __future__ import annotations

import re

import httpx

from . import db, rag


def chunk_text(text: str, size: int = 1000, overlap: int = 150) -> list[str]:
    text = re.sub(r"\s+", " ", text or "").strip()
    if not text:
        return []
    chunks, start = [], 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks


def _store(agent_id: str, kind: str, title: str, origin: str, text: str) -> dict:
    chunks = chunk_text(text)
    metas = [{"title": title, "kind": kind, "origin": origin} for _ in chunks]
    n = rag.add_texts(agent_id, chunks, metas)
    db.add_source(agent_id, kind, title, origin, n)
    return {"agent_id": agent_id, "kind": kind, "title": title,
            "origin": origin, "chunks": n}


# ------------------------------------------------------------------ texte brut
def ingest_text(agent_id: str, title: str, text: str) -> dict:
    return _store(agent_id, "texte", title, title, text)


# ------------------------------------------------------------------- PDF/livre
def ingest_pdf(agent_id: str, title: str, file_bytes: bytes) -> dict:
    from io import BytesIO

    from pypdf import PdfReader

    reader = PdfReader(BytesIO(file_bytes))
    text = "\n".join((page.extract_text() or "") for page in reader.pages)
    return _store(agent_id, "pdf", title, title, text)


# -------------------------------------------------------------------- page web
def ingest_web(agent_id: str, url: str) -> dict:
    from bs4 import BeautifulSoup

    r = httpx.get(url, timeout=30, follow_redirects=True,
                  headers={"User-Agent": "Mozilla/5.0 Aletheia"})
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    title = (soup.title.string.strip() if soup.title and soup.title.string else url)
    text = soup.get_text(separator=" ")
    return _store(agent_id, "web", title, url, text)


# --------------------------------------------------------------------- youtube
_YT_RE = re.compile(r"(?:v=|youtu\.be/|/shorts/|/embed/)([A-Za-z0-9_-]{11})")


def youtube_id(url: str) -> str | None:
    m = _YT_RE.search(url)
    return m.group(1) if m else (url if re.fullmatch(r"[A-Za-z0-9_-]{11}", url) else None)


def _seg_text(seg) -> str:
    """Texte d'un segment, quelle que soit la version de l'API (dict ou objet)."""
    if isinstance(seg, dict):
        return seg.get("text", "")
    return getattr(seg, "text", "") or ""


def _fetch_youtube_transcript(vid: str) -> list | None:
    """Récupère la transcription en gérant les deux API : >=1.0 (instance.fetch)
    et <1.0 (classmethod get_transcript). Essaie fr, puis en, puis défaut."""
    from youtube_transcript_api import YouTubeTranscriptApi

    fetch = None
    try:                                    # API récente : YouTubeTranscriptApi().fetch(...)
        fetch = YouTubeTranscriptApi().fetch
    except Exception:  # noqa: BLE001       # API ancienne : pas d'instance utile
        fetch = None
    for langs in (["fr"], ["en"], ["fr", "en"], None):
        try:
            if fetch is not None:
                data = fetch(vid, languages=langs) if langs else fetch(vid)
            else:
                data = (YouTubeTranscriptApi.get_transcript(vid, languages=langs)
                        if langs else YouTubeTranscriptApi.get_transcript(vid))
            segs = list(data)
            if segs:
                return segs
        except Exception:  # noqa: BLE001
            continue
    return None


def ingest_youtube(agent_id: str, url: str, title: str | None = None) -> dict:
    vid = youtube_id(url)
    if not vid:
        raise ValueError("Lien YouTube non reconnu")
    transcript = _fetch_youtube_transcript(vid)
    if not transcript:
        raise RuntimeError(
            "Transcription YouTube indisponible : soit la vidéo n'a pas de sous-titres, "
            "soit YouTube bloque les requêtes venant du serveur (fréquent en hébergement). "
            "👉 Télécharge l'audio/la vidéo et ajoute-le via « 📕 Fichier » (transcription "
            "automatique par Groq Whisper), ou colle le texte dans « 📝 Texte / note »."
        )
    text = " ".join(_seg_text(s) for s in transcript).strip()
    return _store(agent_id, "youtube", title or f"YouTube {vid}",
                  f"https://youtu.be/{vid}", text)


# ----------------------------------------------------- audio / vidéo (Whisper)
def ingest_media(agent_id: str, title: str, file_bytes: bytes, filename: str) -> dict:
    """Transcription audio/vidéo via Whisper (Groq). Repli si pas de clé."""
    from . import config

    if not config.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY requise pour la transcription audio/vidéo.")
    url = "https://api.groq.com/openai/v1/audio/transcriptions"
    files = {"file": (filename, file_bytes)}
    data = {"model": "whisper-large-v3", "response_format": "text"}
    headers = {"Authorization": f"Bearer {config.GROQ_API_KEY}"}
    r = httpx.post(url, headers=headers, files=files, data=data, timeout=300)
    r.raise_for_status()
    text = r.text
    return _store(agent_id, "media", title, filename, text)
