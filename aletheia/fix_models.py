#!/usr/bin/env python3
"""Répare les modèles des praticiens.

OpenRouter renomme régulièrement ses modèles gratuits : les anciens identifiants
renvoient alors « 404 No endpoints found ». Ce script interroge OpenRouter (depuis
le serveur, qui a accès au réseau), récupère la liste des modèles GRATUITS
réellement disponibles, et réassigne automatiquement un modèle valide à chaque
praticien (en variant les modèles pour la diversité du débat).

Usage sur le serveur :
    cd /root/dadrobot/aletheia && .venv/bin/python3 fix_models.py
Puis recharge la page Aletheia (F5).
"""
from __future__ import annotations

import glob
import json
import os
import re
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
AGENTS_DIR = os.path.join(HERE, "agents")

# On évite les modèles non-conversationnels.
EXCLUDE = ("vision", "embed", "whisper", "tts", "image", "guard", "coder")


def fetch_free_models() -> list[str]:
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/models",
        headers={"User-Agent": "Aletheia/1.0"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    ids = [m["id"] for m in data.get("data", []) if m["id"].endswith(":free")]
    ids = [i for i in ids if not any(b in i.lower() for b in EXCLUDE)]
    return sorted(set(ids))


def main() -> None:
    try:
        free = fetch_free_models()
    except Exception as e:  # noqa: BLE001
        print(f"❌ Impossible de récupérer la liste OpenRouter : {e}")
        return
    if not free:
        print("❌ Aucun modèle gratuit trouvé. Réessaie plus tard.")
        return

    print(f"✅ {len(free)} modèles gratuits disponibles. Réassignation…\n")
    files = sorted(glob.glob(os.path.join(AGENTS_DIR, "*.yaml")))
    i = 0
    for f in files:
        txt = open(f, encoding="utf-8").read()
        is_prat = re.search(r"^role:\s*praticien", txt, re.M)
        is_or = re.search(r"^provider:\s*openrouter", txt, re.M)
        if is_prat and is_or:
            model = free[i % len(free)]
            i += 1
            new = re.sub(r'^model:.*$', f'model: "{model}"', txt, count=1, flags=re.M)
            open(f, "w", encoding="utf-8").write(new)
            print(f"  • {os.path.basename(f):28s} → {model}")

    print(f"\n✅ {i} praticiens mis à jour. Recharge la page Aletheia (F5) et "
          "relance un débat.")


if __name__ == "__main__":
    main()
