#!/usr/bin/env python3
"""Affecte un modèle à chaque praticien selon son tempérament (modèles FORTS only).

- Explorateurs « frontière » (médiumnité, spiritualité, états de conscience) → Grok
  (le plus à l'aise pour spéculer librement, peu de disclaimers).
- Explorateurs créatifs → modèles open forts.
- Rigoureux / challengeurs → modèles forts et exigeants.

Mix Groq (gratuit) + OpenRouter payant. Les modèles sont validés EN DIRECT contre
les deux APIs (on n'écrit jamais un identifiant absent). Les agents de processus
(Claude) ne sont pas touchés.

Usage VPS : cd /root/dadrobot/aletheia && .venv/bin/python3 assign_models.py
Puis : systemctl restart aletheia
"""
from __future__ import annotations

import json
import os
import re
import urllib.request

from dotenv import load_dotenv

HERE = os.path.dirname(os.path.abspath(__file__))
AGENTS_DIR = os.path.join(HERE, "agents")
load_dotenv(os.path.join(HERE, ".env"))

# fichier YAML -> (provider, modèle). Uniquement des modèles forts.
ASSIGN = {
    # Explorateurs « frontière » → Grok (liberté de spéculation)
    "mediumnite.yaml":          ("openrouter", "x-ai/grok-4.3"),
    "spiritualite.yaml":        ("openrouter", "x-ai/grok-4.3"),
    "etats_de_conscience.yaml": ("openrouter", "x-ai/grok-4.3"),
    # Explorateurs créatifs → open forts (peu de disclaimer réflexe)
    "mythologie.yaml":          ("groq",       "openai/gpt-oss-120b"),
    "neurosciences.yaml":       ("groq",       "openai/gpt-oss-120b"),
    "geometrie_sacree.yaml":    ("groq",       "llama-3.3-70b-versatile"),
    "biophysique.yaml":         ("groq",       "llama-3.3-70b-versatile"),
    "lumiere.yaml":             ("groq",       "qwen/qwen3-32b"),
    # Rigoureux / challengeurs → forts et exigeants
    "hypnose.yaml":             ("openrouter", "deepseek/deepseek-chat-v3-0324"),
    "mathematiques.yaml":       ("openrouter", "deepseek/deepseek-chat-v3-0324"),
    "physique_quantique.yaml":  ("openrouter", "openai/gpt-4o-mini"),
    "resonance.yaml":           ("openrouter", "qwen/qwen-2.5-72b-instruct"),
}


def available_models() -> set[str]:
    ok: set[str] = set()
    try:
        req = urllib.request.Request("https://openrouter.ai/api/v1/models",
                                     headers={"User-Agent": "Aletheia/1.0"})
        ok |= {m["id"] for m in json.load(urllib.request.urlopen(req, timeout=30)).get("data", [])}
    except Exception as e:  # noqa: BLE001
        print(f"⚠️ OpenRouter indisponible : {e}")
    key = os.getenv("GROQ_API_KEY", "").strip()
    if key:
        try:
            req = urllib.request.Request(
                "https://api.groq.com/openai/v1/models",
                headers={"Authorization": "Bearer " + key, "User-Agent": "Mozilla/5.0 Aletheia"})
            ok |= {m["id"] for m in json.load(urllib.request.urlopen(req, timeout=25)).get("data", [])}
        except Exception as e:  # noqa: BLE001
            print(f"⚠️ Groq indisponible : {e}")
    return ok


def main() -> None:
    ok = available_models()
    applied = 0
    for fname, (provider, model) in ASSIGN.items():
        path = os.path.join(AGENTS_DIR, fname)
        if not os.path.exists(path):
            print(f"  ⚠️ {fname} introuvable"); continue
        if ok and model not in ok:
            print(f"  ⚠️ {fname}: {model} indisponible → laissé tel quel"); continue
        txt = open(path, encoding="utf-8").read()
        if re.search(r"^provider:", txt, re.M):
            txt = re.sub(r"^provider:.*$", f'provider: "{provider}"', txt, count=1, flags=re.M)
        else:
            txt = f'provider: "{provider}"\n{txt}'
        txt = re.sub(r"^model:.*$", f'model: "{model}"', txt, count=1, flags=re.M)
        open(path, "w", encoding="utf-8").write(txt)
        print(f"  • {fname:28s} → {provider:10s} / {model}")
        applied += 1
    print(f"\n✅ {applied}/{len(ASSIGN)} praticiens affectés. Redémarre Aletheia.")


if __name__ == "__main__":
    main()
