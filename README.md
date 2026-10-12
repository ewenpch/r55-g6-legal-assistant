# r55-g6-legal-assistant

Application d'aide à la compréhension de contrats (bail, travail, abonnement…) assistée par une **IA exécutée en local**. Elle explique un contrat en langage clair, en extrait les informations clés et signale les clauses à vérifier — sans jamais envoyer le document à un service tiers.

> ⚠️ Cette application **ne fournit pas de conseil juridique**. Elle aide à lire un contrat et ne remplace pas un professionnel du droit.

## Membres

| Nom |
|---|
| Ewen Pichoff |
| Mathys Gallienne |
| Malo Denis--Maignan |
| Johnny Granger |

## Stack

| Couche | Choix |
|---|---|
| Frontend | React (Vite, TypeScript) |
| Backend | Python / FastAPI, validation Pydantic |
| Extraction PDF | PyMuPDF (ou pdfplumber) |
| LLM | Ollama + modèle 7–8B quantifié (Q4) — repli : Llama 3.2 3B |
| Stockage | Mémoire du processus (TTL, pas de base de données) |
| Tests | pytest (backend), Vitest (frontend) |
| Qualité | Ruff, ESLint, Prettier |

## Fonctionnalités disponibles

- **Import PDF** par glisser-déposer ou sélection de fichier.
- **Validation** du fichier : type, taille ≤ 5 Mo, ≤ 10 pages, texte extractible.
- **Extraction** du texte page par page avec conservation du numéro de page.
- **Détection** du type de contrat et **résumé** en langage clair.
- **Fiche d'identité** : parties, objet, durée, dates clés, montants.
- **Obligations** de chaque partie.
- **Clauses à vérifier** classées par importance, avec extrait original, explication simple et page.
- **Vérification des citations** : tout extrait absent du document est écarté.
- **Suivi de progression** de l'analyse.
- **Avertissement** permanent « ceci n'est pas un conseil juridique ».

> Roadmap (*Could*) : glossaire au survol, export de l'analyse en PDF, question libre sur le contrat.

## Structure du projet

```
r55-g6-legal-assistant/
├── backend/        # API FastAPI, extraction/validation PDF, appels Ollama
├── frontend/       # Application React (Vite + TypeScript)
├── corpus/         # Contrats de test et annotations (benchmark, évaluation)
├── docs/           # Documentation (CDC, tâches)
└── README.md
```

> Le code (`backend/`, `frontend/`, `corpus/`) est en cours de développement ; seule la documentation existe pour l'instant.

## Prérequis et installation

**Prérequis**

- Python 3.11+
- Node.js 20+ (npm)
- [Ollama](https://ollama.com) installé et démarré

**Installation**

```bash
git clone https://github.com/ewenpch/r55-g6-legal-assistant.git
cd r55-g6-legal-assistant

# Modèle LLM local
ollama pull qwen2.5:7b-instruct

# Backend
cd backend
python -m venv .venv
# Windows : .venv\Scripts\activate
# Linux/macOS : source .venv/bin/activate
pip install -e .

# Frontend
cd ../frontend
npm install
```

## Configuration

Configuration via un fichier `.env` à la racine de `backend/` :

| Variable | Description | Valeur par défaut |
|---|---|---|
| `OLLAMA_HOST` | Adresse du serveur Ollama | `http://localhost:11434` |
| `OLLAMA_MODEL` | Modèle utilisé | `qwen2.5:7b-instruct` |
| `OLLAMA_NUM_CTX` | Taille de la fenêtre de contexte | `4096` |
| `MAX_PAGES` | Nombre de pages maximum acceptées | `10` |
| `MAX_SIZE_MB` | Taille de fichier maximum (Mo) | `5` |
| `RESULT_TTL_SECONDS` | Durée de conservation en mémoire | `3600` |

## Commande de lancement

```bash
# Backend (depuis backend/)
uvicorn app.main:app --reload

# Frontend (depuis frontend/)
npm run dev
```

- Frontend : http://localhost:5173
- API : http://localhost:8000
- Vérification de santé : `GET http://localhost:8000/api/health`

## Documentation

- [Cahier des charges](docs/CDC.md)
- [Découpage en tâches](docs/taches.md)
- [Kanban (GitHub Project)](https://github.com/users/ewenpch/projects/3)
