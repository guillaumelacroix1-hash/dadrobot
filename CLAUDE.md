# CLAUDE.md — Mémoire du projet (lu automatiquement par Claude Code)

> Ce fichier sert de **passation** entre sessions. Il résume le projet, l'état
> d'avancement, le blocage en cours et les prochaines étapes. Lis-le en premier.

## 0. Reprise rapide (TL;DR pour la prochaine session)

- Projet : **Aletheia**, un laboratoire de **débat multi-agents** (dossier `aletheia/`).
- Branche de travail : **`claude/ai-debate-framework-setup-9mp1B`** (tout est dessus).
- Déjà **déployé** sur le VPS Hostinger (systemd `aletheia`, **port 8500**, IPv4
  `148.230.114.24`). Accès **SSH `root@148.230.114.24`** opérationnel (clé en place).
  Déploiement : `cd /root/dadrobot && git pull && systemctl restart aletheia`.
- **404 (modèles périmés)** : réglé — `fix_models.py` a tourné. **429 (rate-limit)** : réglé —
  20 $ de crédit OpenRouter + **retry/back-off** dans `llm.py`.
- **Refonte UI (juin 2026)** : rendu **markdown** du fil, badge **● EN DIRECT**, boutons
  contextuels + toasts, reconnexion WebSocket auto, **sélection d'une phrase → pépite**, et
  onglet **⚙️ Réglages** (saisie des clés API depuis le tableau de bord, écrites dans `.env`
  via `config.set_keys`).
- **Reprise de débat** réparée : « Relancer » recrée le moteur après Stop/redémarrage
  (`DebateManager.resume` async — `orchestrator.py` + route `/resume`).
- **À discuter / en cours** : critères d'apparition des **pépites** (manuel vs « candidates »
  proposées par les agents, à valider) ; activer **Groq** (clé à saisir dans ⚙️ Réglages).

## 1. Vision du porteur (cadre de travail — à respecter)

Le porteur (Guillaume) veut créer un « cercle de parole » entre IA spécialisées qui
**débattent** pour concevoir une **technique concrète, testable**, aidant l'humain à
« retirer ses filtres » et accéder à son plein potentiel (perception, conscience,
capacités extra-sensorielles). C'est un **postulat de travail**, pas une thèse à prouver :
le système est un **générateur d'hypothèses** que le porteur **teste lui-même dans le
réel**, en boucle. Garder ce cadre, rester utile et intellectuellement honnête (distinguer
le démontré du spéculatif sans être méprisant).

## 2. Ce qu'est Aletheia

Voir `CONCEPTION.md` (document de référence détaillé) et `aletheia/README.md`.

- **16 agents** = **12 praticiens** (Hypnose, Lumière, Résonance/Ondes, Géométrie sacrée,
  Mythologie, Spiritualité, Mathématiques, Médiumnité, Physique quantique, Neurosciences,
  Biophysique & Champs, États de conscience) + **4 de processus** (Modérateur,
  Expérimentateur, Avocat du diable, Synthétiseur de cycle).
- Praticiens via **OpenRouter** (modèles gratuits) ; processus via **API Claude**
  (Anthropic). Un agent = un fichier YAML dans `aletheia/agents/`.
- **Déroulé d'un tour** : cadrage (+ sélection dynamique des intervenants) → positions →
  critiques (anti-conformité) → convergence (+ rapport minoritaire + score de consensus) →
  Fiche Protocole → garde-fou → tous les 3 tours, synthèse de cycle. Pause auto en fin de
  tour pour tester dans le réel.

## 3. Architecture technique

```
aletheia/
├── backend/        FastAPI + WebSocket
│   ├── main.py            routes API + WS + sert le frontend ; seed des postulats
│   ├── orchestrator.py    moteur de débat (états, pilotage, sélection, consensus, synthèse)
│   ├── agents.py          chargement/édition des agents YAML
│   ├── llm.py             appels OpenRouter / Groq (OpenAI-compat) / Anthropic
│   ├── rag.py             base de connaissances (ChromaDB optionnel, repli mot-clé)
│   ├── ingestion.py       PDF, texte, web, YouTube (transcript), audio/vidéo (Whisper/Groq)
│   ├── memory.py          tableau noir + résumé roulant
│   ├── postulates.py(db)  registre des postulats versionnés
│   ├── auth.py            login par mot de passe (cookie signé)
│   └── db.py              SQLite : débats, tours, calibrations, postulats, sources,
│                          highlights, test_logs, metrics
├── agents/         16 fichiers .yaml (leviers : model, temperature, persona, orientation)
├── sources/        documents par agent (RAG)
├── data/           SQLite + transcripts + index (gitignored)
├── frontend/index.html   tableau de bord (Tailwind CDN + vanilla JS) : onglets Débats /
│                          Agents / Sources / Postulats / Pépites ; intervention humaine ;
│                          journal de tests ; badge consensus
├── requirements.txt  (ChromaDB commenté par défaut → build léger)
├── setup.sh         installe tout sur un VPS Ubuntu + service systemd
├── fix_models.py    réassigne des modèles OpenRouter gratuits valides
├── DEPLOY.md / DEPLOY_VPS.md   guides de déploiement
└── README.md
```

Fonctionnalités clés implémentées : pilotage temps réel (stop/pause/calibrage/reprise),
orientation par agent, **humain dans la boucle**, **journal de tests réels** (prime sur la
théorie), **pépites ⭐** + sorties (Fiches Protocole), **sélection dynamique** des
intervenants, **score de consensus** (alerte chambre d'écho), **synthèse de cycle**.

## 4. État du déploiement

- **VPS Hostinger** (IPv4 `148.230.114.24`), Ubuntu, accès via Browser terminal hPanel.
- Service **systemd `aletheia`** (auto-restart). Code dans `/root/dadrobot`.
- ⚠️ Le port **8000 est occupé par une autre app du porteur (« amadeus-bot »)**. Aletheia
  doit tourner sur un **autre port** (on a utilisé `PORT=8500` ; vérifier le port réel dans
  `/etc/systemd/system/aletheia.service`). Ouvrir le port dans Hostinger ▸ Firewall.
- Mettre à jour le serveur : `cd /root/dadrobot && git pull && systemctl restart aletheia`
  (souvent un `git pull` suffit : les agents sont relus à chaud).

## 5. Secrets / clés

- Les clés sont dans **`aletheia/.env`** sur le serveur (jamais dans le dépôt, gitignoré).
- Configurées : `OPENROUTER_API_KEY` (praticiens), `ANTHROPIC_API_KEY` (processus),
  `APP_PASSWORD`, `SECRET_KEY`. `GROQ_API_KEY` vide (optionnel : transcription audio).
- ⚠️ **Les clés OpenRouter et Anthropic ont transité en clair dans le chat → à RÉGÉNÉRER**
  (openrouter.ai/keys ; console.anthropic.com) et remettre les nouvelles dans `.env`.

## 6. Lancer en LOCAL (mode choisi par le porteur)

```bash
git clone https://github.com/guillaumelacroix1-hash/dadrobot.git
cd dadrobot && git checkout claude/ai-debate-framework-setup-9mp1B
cd aletheia
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # remplir OPENROUTER_API_KEY + ANTHROPIC_API_KEY ; APP_PASSWORD optionnel en local
uvicorn backend.main:app --reload
# → http://localhost:8000  (en local le port 8000 est libre)
```

Sans `APP_PASSWORD`, l'accès local est ouvert (pas de login). Les modèles praticiens
peuvent encore être périmés : lancer `python fix_models.py` une fois (nécessite réseau).

## 7. Prochaines étapes / pistes

1. **(immédiat)** Faire tourner `fix_models.py` et confirmer qu'un débat se déroule
   (praticiens ET agents Claude répondent). Vérifier le crédit Anthropic si besoin.
2. Reprise d'un débat **après redémarrage du serveur** (les tâches sont en mémoire) :
   relancer/rejouer depuis la base au boot.
3. **Export d'une Fiche Protocole en PDF**.
4. **Upload multi-fichiers** (glisser-déposer) pour charger une bibliothèque de sources.
5. Activer **ChromaDB** (RAG sémantique) si l'instance a ≥ 1 Go (décommenter dans
   `requirements.txt`).
6. HTTPS + nom de domaine via Nginx (voir `DEPLOY_VPS.md` étape 8).

## 8. Conventions

- **Tout en français** (UI, commits, échanges) — le porteur parle français.
- Développer sur la branche `claude/ai-debate-framework-setup-9mp1B`. Ne pas créer de PR
  sans accord explicite du porteur.
- Ne jamais committer de secrets. `.env` et `data/` sont gitignorés.
- Le dépôt contient aussi un `index.html` racine sans rapport (un simulateur de rendement) —
  ne pas y toucher.
- Personas des agents : rigoureuses **et** ouvertes ; respecter le postulat « garder
  l'esprit ouvert » (l'absence d'info publique ne prouve pas la fausseté).
