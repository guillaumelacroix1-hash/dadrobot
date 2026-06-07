#!/usr/bin/env python3
"""Répartit les praticiens en MIX : Groq (gratuit) + OpenRouter payant (fiable).

Objectif : diversité maximale (chaque praticien un modèle différent) ET fiabilité
(zéro 429). La moitié des praticiens tourne sur Groq (gratuit, rapide), l'autre
moitié sur des modèles payants OpenRouter (fiables, pas chers — quelques centimes
au million de tokens). Les modèles sont validés EN DIRECT contre les deux APIs
pour ne jamais réécrire un identifiant périmé. Les agents de processus (Claude)
ne sont pas touchés.

Usage VPS : cd /root/dadrobot/aletheia && .venv/bin/python3 mix_models.py
Puis : systemctl restart aletheia
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

GROQ_PREFERRED = [
    "llama-3.3-70b-versatile", "openai/gpt-oss-120b", "qwen/qwen3-32b",
    "meta-llama/llama-4-scout-17b-16e-instruct", "openai/gpt-oss-20b",
    "llama-3.1-8b-instant",
]
GROQ_EXCLUDE = ("whisper", "tts", "guard", "embed", "compound", "orpheus", "allam", "canopylabs")

# Payants OpenRouter : fiables, pas chers, bons en français (par ordre de préférence).
PAID_PREFERRED = [
    "openai/gpt-4o-mini",
    "mistralai/mistral-small-3.2-24b-instruct",
    "deepseek/deepseek-chat-v3-0324",
    "cohere/command-r-08-2024",
    "amazon/nova-lite-v1",
    "qwen/qwen-2.5-72b-instruct",
    # secours si l'un disparaît du catalogue :
    "meta-llama/llama-3.3-70b-instruct", "mistralai/mistral-nemo",
    "mistralai/mistral-small-24b-instruct-2501", "deepseek/deepseek-chat",
]
MAX_COMPLETION_PRICE = 2e-6   # $2 / million de tokens en sortie : on reste bon marché


def groq_models() -> list[str]:
    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key:
        return []
    try:
        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": "Bearer " + key, "User-Agent": "Mozilla/5.0 Aletheia"})
        data = json.load(urllib.request.urlopen(req, timeout=25))
    except Exception as e:  # noqa: BLE001
        print(f"⚠️ Groq indisponible : {e}")
        return []
    avail = {m["id"] for m in data.get("data", []) if m.get("active")
             and not any(b in m["id"].lower() for b in GROQ_EXCLUDE)}
    out = [m for m in GROQ_PREFERRED if m in avail]
    return out + sorted(avail - set(out))


def paid_models() -> list[str]:
    try:
        req = urllib.request.Request("https://openrouter.ai/api/v1/models",
                                     headers={"User-Agent": "Aletheia/1.0"})
        data = json.load(urllib.request.urlopen(req, timeout=30))
    except Exception as e:  # noqa: BLE001
        print(f"⚠️ OpenRouter indisponible : {e}")
        return []
    price = {}
    for m in data.get("data", []):
        if m["id"].endswith(":free"):
            continue
        try:
            price[m["id"]] = float((m.get("pricing") or {}).get("completion", "0") or 0)
        except ValueError:
            price[m["id"]] = 0.0
    return [m for m in PAID_PREFERRED if m in price and price[m] <= MAX_COMPLETION_PRICE]


def main() -> None:
    groq, paid = groq_models(), paid_models()
    print(f"Groq ({len(groq)}) : {', '.join(groq) or '—'}")
    print(f"Payants ({len(paid)}) : {', '.join(paid) or '—'}\n")
    if not groq and not paid:
        print("❌ Aucun modèle disponible (vérifie les clés).")
        return
    files = sorted(glob.glob(os.path.join(AGENTS_DIR, "*.yaml")))
    prats = [f for f in files
             if re.search(r"^role:\s*praticien", open(f, encoding="utf-8").read(), re.M)]
    gi = pi = 0
    for n, f in enumerate(prats):
        # Alterne Groq / payant ; bascule sur l'autre si une liste est vide.
        want_groq = (n % 2 == 0)
        if (want_groq and groq) or not paid:
            provider, model = "groq", groq[gi % len(groq)]; gi += 1
        else:
            provider, model = "openrouter", paid[pi % len(paid)]; pi += 1
        txt = open(f, encoding="utf-8").read()
        if re.search(r"^provider:", txt, re.M):
            txt = re.sub(r"^provider:.*$", f'provider: "{provider}"', txt, count=1, flags=re.M)
        else:
            txt = f'provider: "{provider}"\n{txt}'
        txt = re.sub(r"^model:.*$", f'model: "{model}"', txt, count=1, flags=re.M)
        open(f, "w", encoding="utf-8").write(txt)
        print(f"  • {os.path.basename(f):28s} → {provider:10s} / {model}")
    print(f"\n✅ {len(prats)} praticiens répartis ({gi} Groq + {pi} payants OpenRouter). "
          "Redémarre Aletheia.")


if __name__ == "__main__":
    main()
