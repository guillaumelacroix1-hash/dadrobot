# 🚀 Mettre Aletheia en ligne (Render)

Objectif : ton labo accessible 24h/24 depuis n'importe quel navigateur, protégé par
mot de passe. Compte ~10-15 minutes. Formule « éco fiable ».

## 1. Récupère tes 3 clés (gratuit pour démarrer)

| Clé | Où la créer | Rôle |
|---|---|---|
| `OPENROUTER_API_KEY` | https://openrouter.ai/keys | Les 8 praticiens |
| `ANTHROPIC_API_KEY` | https://console.anthropic.com/ | Modérateur / Expérimentateur / Avocat / Synthétiseur |
| `GROQ_API_KEY` *(optionnel)* | https://console.groq.com/keys | Vitesse + transcription audio/vidéo |

Choisis aussi un **mot de passe** pour entrer dans le labo (`APP_PASSWORD`).

## 2. Crée le service sur Render

1. Va sur https://render.com et connecte ton compte **GitHub**.
2. **New ➜ Blueprint**, choisis le dépôt `guillaumelacroix1-hash/dadrobot`.
3. Sélectionne la branche **`claude/ai-debate-framework-setup-9mp1B`** (ou `main`
   une fois fusionnée).
4. Render détecte le fichier `render.yaml` à la racine et propose le service **aletheia**.
5. Renseigne les variables d'environnement quand il le demande :
   - `APP_PASSWORD` = ton mot de passe
   - `ANTHROPIC_API_KEY`, `OPENROUTER_API_KEY`, `GROQ_API_KEY` = tes clés
   - `SECRET_KEY` est généré automatiquement.
6. Clique **Apply / Create**. Render installe et démarre tout seul.

> Le service inclut un **disque persistant** (`data/`) : tes débats, postulats, pépites
> et sources survivent aux redéploiements.

## 3. Utilise-le

- Ouvre l'URL fournie par Render (ex. `https://aletheia.onrender.com`).
- Entre ton mot de passe.
- Onglet **Postulats** : ajuste tes axiomes.
- Onglet **Agents** : règle modèles / températures / **orientations**.
- Onglet **Débats** : lance une session, interviens en direct, épingle les **⭐ pépites**,
  note tes **📓 tests réels**.
- Onglet **Pépites** : retrouve les idées et toutes les **Fiches Protocole**.

## Notes

- **Recherche sémantique (RAG fin)** : par défaut, index mot-clé léger (idéal petite
  instance). Pour activer ChromaDB, décommente-le dans `requirements.txt` et prends une
  instance ≥ 1 Go.
- **Mise en veille** : sur les paliers d'entrée, l'instance peut s'endormir après
  inactivité et mettre quelques secondes à se réveiller. Une instance « Starter » la
  garde toujours active.
- **Coût** : hébergement ~5-15 €/mois + tokens à la demande (réduits par les paliers
  gratuits des praticiens et les interventions ciblées des agents Claude).
- **Lancer en local d'abord** (recommandé pour tester) : voir `README.md`.
