# CLAUDE.md — Mémoire du projet (lu automatiquement par Claude Code)

> Ce fichier sert de **passation** entre sessions. Lis-le en premier : il résume le
> projet, l'état d'avancement, ce qui a été construit et les pistes restantes.

## 0. Reprise rapide (TL;DR)

- Projet : **Aletheia**, un laboratoire de **débat multi-agents** (dossier `aletheia/`).
- Branche : **`claude/ai-debate-framework-setup-9mp1B`** (tout est dessus). Repo
  `github.com/guillaumelacroix1-hash/dadrobot`.
- **Déployé et fonctionnel** sur le VPS Hostinger : systemd `aletheia`, **port 8500**,
  **http://148.230.114.24:8500** (login par mot de passe). Accès **SSH `root@148.230.114.24`**
  opérationnel (clé en place). Code dans `/root/dadrobot`.
- Les 16 agents répondent. **OpenRouter crédité (~20 $)** + **Groq** + **Anthropic** configurés.
- Tout est **en français** ; le porteur (Guillaume) dicte ses messages (Wispr) → interpréter
  l'intention, pas le littéral.

## 1. Vision du porteur (cadre — à respecter)

Guillaume veut un « cercle de parole » entre IA spécialisées qui **débattent** pour générer
des **techniques concrètes et testables**, d'abord pour aider l'humain à « retirer ses
filtres » et accéder à son plein potentiel (perception, conscience, capacités extra-
sensorielles). C'est un **postulat de travail**, pas une thèse à prouver : le système est un
**générateur d'hypothèses** qu'il **teste lui-même dans le réel**. Rester utile et
intellectuellement honnête (distinguer le démontré du spéculatif **sans mépriser**, sans
débunker par réflexe). Depuis peu, le labo doit aussi servir à **tout sujet** (voir §2 « cadre
par débat »).

## 2. Ce qu'est Aletheia

- **16 agents** = **12 praticiens** (Hypnose, Lumière, Résonance/Ondes, Géométrie sacrée,
  Mythologie, Spiritualité, Mathématiques, Médiumnité, Physique quantique, Neurosciences,
  Biophysique & Champs, États de conscience) + **4 de processus** (Modérateur,
  Expérimentateur, Avocat du diable, Synthétiseur de cycle). Un agent = un YAML dans
  `aletheia/agents/`.
- **Modèles (état actuel)** : les **12 praticiens sont tous sur OpenRouter PAYANT** (fiables) —
  **Grok 4.3** sur les explorateurs « frontière » (Médiumnité, Spiritualité, États de
  conscience) + DeepSeek V3, GPT-4o-mini, Mistral Small, Llama 3.3 70B, Cohere Command-R,
  Qwen 2.5 72B. **Groq a été abandonné** pour les praticiens (limite de tokens/minute trop
  basse → `413` quand le contexte grossit). Les **4 process** sont sur **Claude**
  (`claude-sonnet-4-6`). Affectation faite via `assign_models.py` (valide les modèles en
  direct contre les APIs). ⚠️ Les YAMLs d'agents sur le VPS sont **modifiés à chaud et NON
  commités** (voir §4).
- **Déroulé d'un tour** : cadrage (+ sélection des intervenants) → positions → critiques
  (anti-conformité) → convergence (+ rapport minoritaire + **score de consensus**) →
  **livrable** (Fiche Protocole / synthèse / rien) → garde-fou → tous les 3 tours, synthèse
  de cycle.
- **Avancement** : par défaut le débat **enchaîne les tours automatiquement jusqu'au
  consensus** (≥ 75 %, évalué par le Modérateur) ou jusqu'à `max_rounds` (8) → puis pause
  pour test réel. Mode « pas à pas » possible (pause à chaque tour).
- **Cadre par débat** : chaque débat a son **objectif** (étoile polaire propre), ses **axiomes
  choisis** (postulats cochés au lancement) et son **type de livrable**
  (`protocole` | `synthese` | `libre`). → on peut débattre de **n'importe quel sujet** sans
  rester accroché à l'éveil. Défaut = objectif éveil (rien ne casse).

## 3. Fonctionnalités construites (session de juin 2026)

- **UI refondue** (`frontend/index.html`, Tailwind CDN + vanilla JS) : rendu **markdown** du
  fil, badge **● EN DIRECT**, boutons contextuels + toasts, **reconnexion WebSocket auto**,
  **pleine largeur**, **🧭 Plan du débat** cliquable (sauter à une intervention),
  **auto-scroll intelligent** (ne ramène plus en bas si on a remonté ; verrou 🔒/🔓 + bouton
  « nouveaux messages »), **taille de texte A−/A+** (persistée), séparateurs de tours, encart
  **« cadre commun injecté »** (onglet Agents), onglet **⚙️ Réglages** (saisie des clés API).
- **Pépites** : cycle de vie `candidate → retenue → confirmée → écartée`. Créées **à la main**
  (⭐ message ou **sélection d'une phrase**) **ou en auto** (le Modérateur propose des
  `PÉPITE CANDIDATE` à la convergence). **Contexte de 2-3 phrases par pépite** (le Modérateur
  pour les candidates ; Claude via `explain_highlight` pour les épinglages manuels). Statuts +
  boutons Retenir/Écarter/Confirmée. Table `highlights` (colonnes `status`, `context`).
- **Apprentissage des agents** (mémoire évolutive) : toggle **📚 Apprentissage** par praticien
  (ON par défaut). À la **clôture** (bouton « Clôturer & consolider » = `POST /api/debates/{id}/close`),
  chaque praticien tire **1-3 prises de conscience** (de ses interventions, des critiques, des
  **tests réels**), plafonnées à 6. Elles sont injectées dans son prompt **aux débats
  suivants uniquement** (jamais en cours). Visibles + effaçables par agent. Table `learnings`.
- **MISSION** : l'esprit « précurseur / interdisciplinarité » est désormais un **postulat
  éditable** (onglet Postulats), plus codé en dur.
- **Reprise de débat** : `DebateManager.resume` (async) recrée le moteur après Stop ou
  redémarrage serveur, en relisant le cadre depuis la base (`/api/debates/{id}/resume`).
- **Robustesse LLM** (`llm.py`) : retry/back-off sur `429/5xx`, masquage des balises
  `<think>…</think>` (modèles raisonneurs), **User-Agent explicite** (sinon Groq renvoie 403).

## 4. Architecture & déploiement

```
aletheia/
├── backend/  FastAPI + WebSocket
│   ├── main.py          routes API + WS + sert le frontend ; seed des postulats (dont MISSION)
│   ├── orchestrator.py  moteur : tours, sélection, consensus, auto-advance, pépites,
│   │                    explain_highlight, consolidate_learnings, shared_frame(objective,…)
│   ├── agents.py        Agent (dont champ `learning`) ; load/save/update YAML
│   ├── llm.py           OpenRouter / Groq / Anthropic ; retry, _clean(<think>), User-Agent
│   ├── ingestion.py     PDF, texte, web, YouTube (réparé), audio/vidéo (Whisper/Groq)
│   ├── db.py            SQLite : debates(objective,postulate_ids,deliverable), turns,
│   │                    highlights(status,context), learnings, test_logs, metrics, …
│   ├── rag.py · memory.py · auth.py · config.py(set_keys/keys_status)
├── agents/   16 YAML  (⚠️ modifiés à chaud sur le VPS, NON commités)
├── fix_models.py · use_groq.py · mix_models.py · assign_models.py   (scripts d'affectation)
└── frontend/index.html   tableau de bord (onglets Débats/Agents/Sources/Postulats/Pépites/Réglages)
```

**Workflow de déploiement (important) :**
1. Coder en local, vérifier l'import (`.venv\Scripts\python.exe -c "import backend.main"`).
2. `git commit` (email **`guillaumelacroix1@gmail.com`**) + `git push` — **ne JAMAIS committer
   `aletheia/agents/*.yaml`** (modifiés à chaud sur le VPS), ni `.env`, ni `data/`.
3. Sur le VPS : `cd /root/dadrobot && git pull --ff-only ...`.
   - **Changement frontend pur** (`index.html`) → **aucun redémarrage** (servi à chaque requête).
   - **Changement backend** → `systemctl restart aletheia` (⚠️ coupe le débat en cours ;
     il est ensuite reprenable via « Relancer »).
4. **Piloter un débat en SSH** (pause/relance/clôture) : lire `APP_PASSWORD` dans `.env`,
   faire `POST /api/login` (localhost:8500) pour un token, puis appeler les routes. Le mot de
   passe **ne doit jamais transiter par le chat**.
- Astuce SSH pour commandes complexes : encoder en base64 et `echo <b64> | base64 -d | bash`
  (ou `| .venv/bin/python3 -`) pour éviter l'enfer du quoting.
- Le port **8000/8001 sont pris par Docker** (autre app du porteur) → Aletheia sur **8500**.

## 5. Secrets / clés

- Dans **`aletheia/.env`** sur le serveur (gitignoré). `OPENROUTER_API_KEY` (crédité ~20 $),
  `ANTHROPIC_API_KEY`, `GROQ_API_KEY`, `APP_PASSWORD`, `SECRET_KEY`.
- **Éditables depuis l'onglet ⚙️ Réglages** (écrit dans `.env` + prise en compte immédiate,
  `config.set_keys`).
- ⚠️ D'anciennes clés ont transité en clair dans le chat par le passé → idéalement à
  **régénérer** (openrouter.ai/keys, console.anthropic.com, console.groq.com).

## 6. Lancer en LOCAL (Windows ARM64 — machine du porteur)

⚠️ Sur cette machine, `python`/`python3`/`py` sont des shims uv cassés. Utiliser le venv :
`aletheia\.venv\Scripts\python.exe` (créé avec `C:\Users\guill\AppData\Local\Programs\Python\Python312-arm64\python.exe`).
`uvicorn[standard]` ne compile pas en ARM64 (httptools) → installer **`uvicorn` simple +
`websockets`** (ne PAS toucher `requirements.txt`, correct pour le VPS Linux).

```
.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000   # cwd = aletheia
```
Sans `APP_PASSWORD`, accès local ouvert. Pour prévisualiser/QA : MCP Claude_Preview
(`preview_start` via `.claude/launch.json`).

## 7. Pistes restantes

1. **Persister le cadre au resume** : participants + mode d'avancement ne sont pas restaurés
   après redémarrage (le resume repart sur les défauts auto). À stocker en base si gênant.
2. **Durcir le consensus** : c'est l'auto-évaluation du Modérateur — éventuellement exiger 2
   tours consécutifs ≥ seuil.
3. **Export d'une Fiche Protocole en PDF** ; **upload multi-fichiers** de sources.
4. **YouTube** : l'IP du VPS est bloquée par YouTube (transcript ET yt-dlp). Voie fiable =
   déposer le fichier audio/vidéo (→ Groq Whisper) ou coller le texte. Récupération de
   transcript possible depuis une machine non bloquée puis injection via `ingestion._store`.
5. **ChromaDB** (RAG sémantique) si l'instance a ≥ 1 Go (décommenter `requirements.txt`).
6. **HTTPS + domaine** via Nginx (`DEPLOY_VPS.md`).

## 8. Conventions

- **Tout en français** (UI, commits, échanges).
- Branche `claude/ai-debate-framework-setup-9mp1B`. **Pas de PR sans accord explicite.**
- **Push uniquement quand Guillaume le demande** ; commits au fil de l'eau OK.
- **Ne jamais committer** : secrets, `.env`, `data/`, et **`aletheia/agents/*.yaml`** (état à
  chaud sur le VPS). Le `index.html` racine du dépôt est un projet sans rapport — ne pas y toucher.
- Personas des agents : rigoureuses **et** ouvertes (postulat « garder l'esprit ouvert »).
