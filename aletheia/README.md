# ✨ Aletheia — Laboratoire de débat multi-agents

Un cénacle d'IA spécialisées qui **débattent entre elles** autour d'un objectif
commun pour produire des **idées concrètes, testables dans le réel**.

> Conception détaillée : voir [`../CONCEPTION.md`](../CONCEPTION.md).

## Ce que ça fait

- **8 praticiens** (Hypnose, Lumière, Résonance/Ondes, Géométrie sacrée, Mythologie,
  Spiritualité, Mathématiques, Médiumnité) + **3 agents de processus** (Modérateur,
  Expérimentateur, Avocat du diable).
- **Débat piloté en temps réel** : stop / pause / **calibrage** / reprise. À la fin de
  chaque tour, l'Expérimentateur produit une **Fiche Protocole** à tester dans le réel.
- **Base de connaissances vivante et multi-source** par agent : texte, PDF/livre, page
  web, **YouTube** (transcription auto), audio/vidéo (Whisper via Groq). Enrichissable
  **à chaud**, même en plein débat.
- **Registre des Postulats** éditable et versionné, injecté dans chaque agent.
- **Ajout d'un spécialiste à tout moment** depuis le tableau de bord.
- **Accès protégé** par mot de passe.

## Architecture (résumé)

- **Backend** : FastAPI + WebSocket (`backend/`)
- **Modèles praticiens** : via API (OpenRouter / Groq, paliers gratuits)
- **Modèles de processus** : API Claude (Anthropic)
- **RAG** : ChromaDB (CPU, sans GPU) — repli mot-clé si Chroma absent
- **Persistance** : SQLite + transcripts ; index vectoriel dans `data/`
- **Frontend** : tableau de bord web (`frontend/index.html`)

## Lancer en local

```bash
cd aletheia
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # puis remplis les clés
uvicorn backend.main:app --reload
```

Ouvre http://localhost:8000

> Sans clés API, le serveur démarre quand même : le tableau de bord fonctionne, et les
> agents signalent simplement « modèle indisponible » dans le débat. Renseigne au moins
> `OPENROUTER_API_KEY` (praticiens) et `ANTHROPIC_API_KEY` (processus) pour un vrai débat.

## Clés nécessaires

| Variable | À quoi ça sert | Où |
|---|---|---|
| `ANTHROPIC_API_KEY` | Modérateur / Expérimentateur / Avocat du diable | console.anthropic.com |
| `OPENROUTER_API_KEY` | Les praticiens | openrouter.ai/keys |
| `GROQ_API_KEY` | Vitesse + transcription audio/vidéo (optionnel) | console.groq.com/keys |
| `APP_PASSWORD` | Mot de passe d'accès au labo | toi |
| `SECRET_KEY` | Signe les sessions | une longue chaîne aléatoire |

## Déploiement (Render)

Le fichier `render.yaml` est prêt : crée un service web à partir du dépôt, renseigne les
variables d'environnement, et Render fait le reste (avec un disque persistant pour `data/`).

## État

Squelette fonctionnel (étapes 1→7 du plan). Les modèles indiqués dans `agents/*.yaml`
sont des suggestions de modèles gratuits ; ajuste-les selon les disponibilités
d'OpenRouter. La reprise d'un débat après redémarrage du serveur (relance de la tâche)
est une amélioration prévue.
