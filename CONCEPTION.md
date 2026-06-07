# Aletheia — Laboratoire de débat multi-agents

> *Aletheia* (ἀλήθεια) : en grec ancien, le « dévoilement », ce qui apparaît quand on
> retire le voile. Le nom du projet dit son intention : **retirer les filtres**.

Document de conception. C'est la référence du projet : on le fait évoluer au fil de
l'avancement. Aucune ligne de code n'est encore écrite — ceci est le plan verrouillé.

---

## 1. Intention

Mettre en place un **cercle de parole entre IA spécialisées** — un cénacle — qui
**débattent entre elles** autour d'un objectif commun, chacune dotée d'un savoir
particulier et de ses propres sources. Le but n'est pas de discuter pour discuter,
mais de **produire des idées concrètes, testables dans le réel**, dans une boucle :

```
débat  →  protocole concret  →  test dans la matière  →  observations  →  débat suivant
```

### Postulat de départ (cadre de travail)

Le porteur du projet part du principe que les capacités humaines sont bridées par des
« filtres », et qu'il est possible de les lever pour accéder à un potentiel élargi
(perception, conscience, capacités extra-sensorielles). Ce postulat est **le cadre du
laboratoire**, pas une thèse à démontrer par les IA.

### Position épistémologique du système

Le système ne cherche pas à *prouver* le postulat. Il fonctionne comme un
**générateur d'hypothèses** : les agents proposent des **protocoles**, et c'est
l'humain qui **valide empiriquement** dans le réel. C'est cette boucle test/retour qui
transforme une conversation d'IA en démarche de recherche.

---

## 2. Étoile polaire (objectif commun)

> **« Comment éveiller le plein potentiel humain — perception, conscience, capacités
> latentes — sans présupposer la forme du résultat ? »**

Objectif volontairement **large et ouvert** : on ne fige pas d'avance la forme de la
solution (technique, objet, induction, dispositif…).

### Hypothèse-pivot du laboratoire

> Il existerait un **pattern commun, caché, reliant son, fréquence et lumière** (et
> peut-être d'autres ondes) — un motif unificateur exploitable par le cerveau humain.
> En découvrir la structure et l'appliquer est une piste centrale du cercle.

Cette hypothèse est confiée en priorité à l'agent **Résonance / Ondes** (voir §3).

---

## 3. Le cénacle

Deux familles d'agents. Cette séparation est volontaire : elle évite que le débat ne
tourne en bouillie et garantit qu'on produit toujours quelque chose d'actionnable.

### Praticiens — apportent un savoir (modèle local + persona + sources RAG propres)

| Agent | Rôle dans le débat | Apporte |
|---|---|---|
| 🌀 **Hypnose** *(pivot)* | Inductions, langage, installation des états modifiés | Le « comment on installe l'état » |
| 💡 **Lumière** | Lumière pulsée, fréquences lumineuses, entraînement cérébral, sécurité photosensible | Le levier physique privilégié |
| 〰️ **Résonance / Ondes** | Quête du **pattern unificateur son/fréquence/lumière** et de son application au cerveau | Le motif caché recherché |
| 📐 **Géométrie sacrée** | Formes, ratios, supports visuels de focalisation | Le support symbolique/visuel |
| 📜 **Mythologie & textes anciens** | Récurrences interculturelles des techniques d'éveil | La sagesse éprouvée |
| ✨ **Spiritualité / conscience** | Cadres de l'expérience intérieure, intention, direction | Le sens |
| 🔢 **Mathématiques / structure** | Rythmes, ratios, motifs, rigueur formelle | La structure sous-jacente |
| 🔮 **Médiumnité / perception extra-sensorielle** | Phénoménologie des perceptions élargies | L'expérience visée |

### Agents de processus — font avancer le débat (API Claude, pour la qualité de synthèse)

| Agent | Rôle |
|---|---|
| 🎙️ **Modérateur** | Pose l'objectif + la sous-question du jour, distribue la parole, recentre, résume |
| 🧪 **Expérimentateur** | Transforme les pistes en **Fiche Protocole** testable (mesure + sécurité) |
| ⚖️ **Avocat du diable** | Cherche les failles, signale l'invérifiable et les risques, évite l'auto-illusion collective |

> **8 praticiens + 3 agents de processus = 11 agents.** Le cercle est extensible :
> ajouter un agent = créer un fichier de configuration (voir §6).

---

## 4. Le Registre des Postulats

Brique de premier plan, à la demande du porteur : *« pouvoir mettre mes postulats et
les faire évoluer »*.

- Espace où l'humain **écrit ses postulats fondateurs**. Exemples de départ :
  - « La conscience ne se réduit pas à la matière. »
  - « Les capacités extra-sensorielles sont réelles et entraînables. »
  - « Un pattern commun relie son, fréquence et lumière. »
- Ces postulats sont **injectés automatiquement dans le contexte de chaque agent**
  comme cadre partagé. C'est ainsi que le cercle « garde le postulat en tête » à
  chaque débat.
- Ils sont **éditables et versionnés** : on les fait évoluer dans le temps, et chaque
  débat enregistre **quels postulats étaient actifs** au moment où il s'est tenu. On
  peut ainsi observer comment l'évolution des axiomes change les conclusions.

---

## 5. Déroulé d'une session de débat

1. **Cadrage** — le Modérateur rappelle l'étoile polaire, les postulats actifs et la
   sous-question du jour.
2. **Positions** — chaque Praticien s'exprime depuis sa spécialité, en puisant dans ses
   sources RAG.
3. **Critique croisée** — chacun réagit à 2 autres : accords, tensions, manques.
4. **Convergence** — le Modérateur extrait les 2-3 pistes les plus prometteuses.
5. **Mise en protocole** — l'Expérimentateur rédige une **Fiche Protocole**.
6. **Garde-fou** — l'Avocat du diable signale risques et points invérifiables.
7. **Enregistrement** — tout est stocké (base + transcript). L'humain teste dans le
   réel, revient avec ses observations → la session suivante démarre de là.

### Sortie concrète — la « Fiche Protocole » (le livrable)

C'est ce que l'humain teste. Format type :

- **Nom**
- **Objectif visé**
- **Matériel**
- **Durée**
- **Déroulé pas-à-pas**
- **Ce qu'on cherche à observer** (signes mesurables)
- **Précautions** (sécurité — ex. photosensibilité pour la lumière pulsée)
- **Variante à tester au prochain tour**

---

## 6. Architecture technique

### Choix structurants

| Brique | Choix | Pourquoi |
|---|---|---|
| **Hébergement** | Serveur web géré (cible **Render**), accessible 24h/24 | Disponible à tout moment depuis n'importe quel navigateur |
| **Accès** | **Login protégé** (mot de passe) | L'URL est publique : le labo, les sources et les clés restent privés |
| **Modèles praticiens** | **Via API — passerelle OpenRouter** (+ Groq pour la vitesse) | Paliers gratuits / très bon marché ; changer le modèle d'un agent = changer une ligne |
| **Modèles processus** | **API Claude (Anthropic)** | Synthèse et cadrage de haute qualité, peu de tokens (interventions ciblées) |
| **Cerveau de chaque agent** | **RAG** — ChromaDB + documents par agent | Permet d'injecter des sources *hors internet* fournies par l'humain |
| **Mémoire / grand contexte** | Tableau noir partagé + résumés roulants | Fil long sans explosion de tokens |
| **Persistance** | **SQLite** + transcripts Markdown | Tout est enregistré : tours, synthèses, protocoles, postulats actifs |
| **Backend** | **Python + FastAPI + WebSocket** | Débat visible en direct |
| **Frontend** | Tableau de bord web (style Tailwind, cohérent avec l'existant) | Lancer, régler, uploader, éditer, relire |

### Hébergement & accès (100 % web)

Le labo est **hébergé sur un serveur, accessible à tout moment** depuis un navigateur —
le PC du porteur n'est plus dans la boucle (la contrainte GPU AMD Vega disparaît).

- **Formule retenue : « éco fiable ».** L'application (tableau de bord, base, RAG) tourne
  sur un petit serveur géré et fiable (cible recommandée : **Render**, avec disque
  persistant pour SQLite + ChromaDB ; alternative : VPS Hetzner ~4 €/mois).
- **Les praticiens passent par API** plutôt que par des modèles locaux : passerelle
  **OpenRouter** (un seul accès → des dizaines de modèles, dont des **gratuits**) et/ou
  **Groq** (inférence très rapide, palier gratuit). Changer le modèle d'un agent revient
  à changer une ligne de configuration.
- **Les agents de processus** (Modérateur, Expérimentateur, Avocat du diable) passent par
  l'**API Claude**.
- **Accès protégé par login** : l'URL étant publique, un mot de passe protège le labo, les
  sources et les clés.
- **Mise en place gérée de bout en bout** : je recommande la plateforme et prépare tout ;
  le porteur n'a qu'à créer les comptes et fournir les clés (Anthropic, OpenRouter…).
- Ordre de grandeur du coût : **~5-15 €/mois** d'hébergement + **tokens à la demande**
  (réduits par les paliers gratuits des praticiens et les interventions ciblées des
  agents de processus).

### Structure de projet envisagée

```
aletheia/
├── backend/
│   ├── main.py              # serveur FastAPI + WebSocket
│   ├── orchestrator.py      # moteur du débat (tours, critique croisée, synthèse)
│   ├── agents.py            # chargement des agents + appels API (OpenRouter/Groq) + Claude
│   ├── rag.py               # ingestion des sources + recherche (Chroma)
│   ├── memory.py            # tableau noir + résumés roulants
│   ├── postulates.py        # Registre des Postulats (édition + versionnage)
│   ├── auth.py              # login / accès protégé par mot de passe
│   └── db.py                # SQLite (débats, tours, protocoles, postulats)
├── agents/                  # 1 fichier de config par agent
│   ├── hypnose.yaml
│   ├── lumiere.yaml
│   ├── resonance.yaml
│   ├── geometrie_sacree.yaml
│   ├── mythologie.yaml
│   ├── spiritualite.yaml
│   ├── mathematiques.yaml
│   ├── mediumnite.yaml
│   ├── moderateur.yaml
│   ├── experimentateur.yaml
│   └── avocat_du_diable.yaml
├── sources/                 # documents fournis, un sous-dossier par agent
│   ├── hypnose/
│   └── ...
├── data/                    # SQLite + transcripts générés
└── frontend/
    └── index.html           # tableau de bord
```

### Les « leviers » réglables par agent

Chaque fichier `agents/*.yaml` expose les réglages modifiables :

- `model` — quel modèle (via OpenRouter/Groq, ou API Claude pour les agents de processus)
- `temperature`, `top_p` — créativité / rigueur
- `persona` — le rôle et le ton (prompt système)
- `sources` — dossier RAG associé
- `max_context` — taille de fenêtre allouée

---

## 7. Décisions actées

- **Hébergement** : **100 % web**, serveur géré fiable (cible **Render**), accessible 24h/24. Le PC local n'est plus utilisé (fin de la contrainte AMD Vega).
- **Mode modèles** : praticiens **via API** (OpenRouter/Groq, paliers gratuits), processus via **API Claude**.
- **Accès** : **login protégé** par mot de passe.
- **Mise en place** : je recommande la plateforme et gère le déploiement ; le porteur crée les comptes/clés.
- **Interface** : **tableau de bord web**.
- **Cénacle** : **8 praticiens** (dont **agent Résonance dédié**) + **3 processus**.
- **Objectif** : formulation **large et ouverte**.
- **Postulats** : **Registre éditable et versionné**, injecté dans tous les agents.

---

## 8. Étapes de construction (à venir)

1. Squelette projet + base SQLite + fichiers de configuration des agents.
2. Connexion des modèles **via API** (OpenRouter/Groq) + **API Claude** + login d'accès.
3. **RAG** : ingestion des sources par agent.
4. **Registre des Postulats** (édition, versionnage, injection).
5. **Moteur de débat** + mémoire / résumés roulants.
6. **Tableau de bord web** (débat live, réglages, sources, postulats, historique).
7. **Déploiement** sur le serveur géré (cible Render) + mise en ligne accessible 24h/24.
8. Première session de test sur l'étoile polaire.

> État actuel : **plan verrouillé, document de référence écrit.** Prochaine étape sur
> validation : passage au squelette de code (étape 1).
