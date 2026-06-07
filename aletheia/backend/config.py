"""Configuration centrale : chemins et variables d'environnement."""
from __future__ import annotations

import os
import re
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


_EDITABLE_KEYS = ("ANTHROPIC_API_KEY", "OPENROUTER_API_KEY", "GROQ_API_KEY")


def _mask(v: str) -> str:
    if not v:
        return ""
    return (v[:4] + "…" + v[-4:]) if len(v) > 10 else "••••"


def keys_status() -> dict:
    """État des clés (présence + indice masqué), sans jamais révéler la valeur."""
    vals = {"ANTHROPIC_API_KEY": ANTHROPIC_API_KEY,
            "OPENROUTER_API_KEY": OPENROUTER_API_KEY,
            "GROQ_API_KEY": GROQ_API_KEY}
    return {k: {"set": bool(v), "hint": _mask(v)} for k, v in vals.items()}


def set_keys(updates: dict) -> None:
    """Écrit/met à jour des clés dans .env (en préservant le reste du fichier) et
    en mémoire (effet immédiat, sans redémarrage du serveur)."""
    updates = {k: v.strip() for k, v in updates.items() if k in _EDITABLE_KEYS and v and v.strip()}
    if not updates:
        return
    env_path = ROOT / ".env"
    lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    seen, out = set(), []
    for line in lines:
        m = re.match(r"\s*([A-Z_][A-Z0-9_]*)\s*=", line)
        if m and m.group(1) in updates:
            out.append(f"{m.group(1)}={updates[m.group(1)]}")
            seen.add(m.group(1))
        else:
            out.append(line)
    for k, v in updates.items():
        if k not in seen:
            out.append(f"{k}={v}")
    env_path.write_text("\n".join(out) + "\n", encoding="utf-8")
    for k, v in updates.items():        # met à jour les variables du module en place
        globals()[k] = v
