#!/usr/bin/env python3
"""Bascule les praticiens sur Groq (gratuit, rapide, fiable).

Interroge l'API Groq pour les modèles de chat réellement disponibles, puis
réassigne `provider: groq` + un modèle Groq à chaque praticien (en variant les
modèles pour garder de la diversité dans le débat). Les agents de processus
(Claude / Anthropic) ne sont PAS touchés.

À utiliser quand les modèles gratuits OpenRouter sont saturés en amont (429).

Usage sur le serveur :
    cd /root/dadrobot/aletheia && .venv/bin/python3 use_groq.py
Puis : `systemctl restart aletheia` (les agents sont relus à chaud).
"""
from __future__ import annotations

import glob
import json
import os
import re
import urllib.request

from dotenv import load_dotenv

HERE = os.path.dirname(os.path.abspath(__file__))
AGENTS_DIR = os.path.join(HERE, "agents")
load_dotenv(os.path.join(HERE, ".env"))

# Modèles de chat Groq privilégiés (multilingues, bons en français), par ordre.
PREFERRED = [
    "llama-3.3-70b-versatile",
    "openai/gpt-oss-120b",
    "qwen/qwen3-32b",
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "openai/gpt-oss-20b",
    "llama-3.1-8b-instant",
]
# Non-conversationnels ou inadaptés à un débat en français.
EXCLUDE = ("whisper", "tts", "guard", "embed", "compound", "orpheus", "allam", "canopylabs")


def groq_chat_models() -> list[str]:
    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key:
        raise RuntimeError("GROQ_API_KEY absente du .env")
    req = urllib.request.Request(
        "https://api.groq.com/openai/v1/models",
        headers={"Authorization": "Bearer " + key, "User-Agent": "Mozilla/5.0 Aletheia"},
    )
    with urllib.request.urlopen(req, timeout=25) as r:
        data = json.load(r)
    avail = {m["id"] for m in data.get("data", [])
             if m.get("active") and not any(b in m["id"].lower() for b in EXCLUDE)}
    ordered = [m for m in PREFERRED if m in avail]      # préférés d'abord…
    ordered += sorted(avail - set(ordered))             # …puis le reste pour compléter
    return ordered


def main() -> None:
    try:
        models = groq_chat_models()
    except Exception as e:  # noqa: BLE001
        print(f"❌ Groq : {e}")
        return
    if not models:
        print("❌ Aucun modèle de chat Groq disponible.")
        return
    print(f"✅ {len(models)} modèles Groq retenus : {', '.join(models)}\n")
    files = sorted(glob.glob(os.path.join(AGENTS_DIR, "*.yaml")))
    i = 0
    for f in files:
        txt = open(f, encoding="utf-8").read()
        if not re.search(r"^role:\s*praticien", txt, re.M):
            continue
        model = models[i % len(models)]
        i += 1
        if re.search(r"^provider:", txt, re.M):
            txt = re.sub(r"^provider:.*$", 'provider: "groq"', txt, count=1, flags=re.M)
        else:
            txt = f'provider: "groq"\n{txt}'
        txt = re.sub(r"^model:.*$", f'model: "{model}"', txt, count=1, flags=re.M)
        open(f, "w", encoding="utf-8").write(txt)
        print(f"  • {os.path.basename(f):28s} → groq / {model}")
    print(f"\n✅ {i} praticiens basculés sur Groq. Redémarre Aletheia (ou recharge).")


if __name__ == "__main__":
    main()
