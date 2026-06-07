"""Configuration centrale : chemins et variables d'environnement."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Racine du projet : .../aletheia
ROOT = Path(__file__).resolve().parent.parent

# Charge le .env s'il existe (sinon on s'appuie sur l'environnement du serveur).
load_dotenv(ROOT / ".env")

# --- Dossiers ---
AGENTS_DIR = ROOT / "agents"
SOURCES_DIR = ROOT / "sources"
DATA_DIR = ROOT / "data"
FRONTEND_DIR = ROOT / "frontend"
TRANSCRIPTS_DIR = DATA_DIR / "transcripts"
CHROMA_DIR = DATA_DIR / "chroma"
DB_PATH = DATA_DIR / "aletheia.db"

for _d in (DATA_DIR, TRANSCRIPTS_DIR, SOURCES_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# --- Secrets / accès ---
APP_PASSWORD = os.getenv("APP_PASSWORD", "")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")

# --- Clés API des fournisseurs de modèles ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")


def missing_keys() -> list[str]:
    """Liste les clés non configurées, pour avertir dans le tableau de bord."""
    out = []
    if not ANTHROPIC_API_KEY:
        out.append("ANTHROPIC_API_KEY (agents de processus / Claude)")
    if not OPENROUTER_API_KEY:
        out.append("OPENROUTER_API_KEY (praticiens)")
    if not GROQ_API_KEY:
        out.append("GROQ_API_KEY (vitesse + transcription audio, optionnel)")
    return out
