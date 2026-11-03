# Benchmark — modèles Ollama

> Tâche #5 — S1 : installation Ollama et pull des modèles (§8.1).
> Ce document enregistre les versions installées, les tailles des tirages et le contexte machine qui les a produites.

## Machine

| Champ | Valeur |
|---|---|
| OS | Windows 11 Professionnel Éducation 64 bits |
| Mémoire vive | 7,73 Go (machine cible nominale : 16 Go ; mode repli à 8 Go) |
| CPU | Intel HD Graphics 630, sans CUDA (exécution en mode CPU) |
| Logiciel | Ollama 0.40.3 |
| Date | 12 octobre 2026 |

## Modèles installés

| Modèle | Taille | ID | Statut |
|---|---|---|---|
| `qwen2.5:7b-instruct` | 4,7 GB | 845dbda0ea48 | Tiré avec succès |
| `llama3.2:3b` | 2,0 GB | a80c4f17acd5 | Tiré avec succès |

## Choix du modèle

- **Modèle par défaut : `qwen2.5:7b-instruct`** (famille 7–8B, quantifié Q4) — choisi pour la qualité du français et la capacité à produire du JSON structuré (justification du CDC §8.1).
- **Repli : `llama3.2:3b`** — modèle 3B quantifié Q4 pour machine à 8 Go, ≤ 6 pages (§9).
- **Fenêtre de contexte : `num_ctx = 4096`** (configuration README / `.env`).
- Pas de CUDA disponible : toutes les mesures de performance (chargement, tok/s, RSS, swap) seront réalisées en mode CPU, ce qui impose le budget de temps < 5 min pour 10 pages (§7.1) et le contrôle de santé du §9.

## Commandes utilisées

```bash
ollama pull qwen2.5:7b-instruct   # 4,7 GB
ollama pull llama3.2:3b           # 2,0 GB
ollama ls
ollama --version                  # 0.40.3
```

## Script de benchmark

> Tâche #7 — S1 : `backend/scripts/bench.py` (CDC §7.1).

Le script rejoue le pipeline d'analyse sur la fixture `corpus/bench/` : le document est découpé en blocs qui tiennent dans `num_ctx` (coupure sur les titres d'articles), puis chaque bloc part dans un appel `/api/chat` en mode JSON, comme le fera l'API. Pour chaque combinaison modèle × `num_ctx` × nombre de pages, il mesure :

| Mesure | Comment |
|---|---|
| Temps de chargement | Tous les modèles sont déchargés (`keep_alive: 0`), puis le modèle est chargé à froid avec le `num_ctx` testé ; durée mesurée côté client |
| Prefill tok/s | `prompt_eval_count / prompt_eval_duration` cumulés sur les blocs. Un préfixe unique par requête empêche Ollama de réutiliser son cache KV : tout le prompt est réellement évalué |
| Génération tok/s | `eval_count / eval_duration` cumulés sur les blocs |
| Durée du document | Temps total côté client pour tous les blocs, modèle déjà chargé, comparé au budget de 5 min |
| RSS pic | Somme des RSS des processus Ollama (serveur, runner, `llama-server`), échantillonnée toutes les 0,25 s |
| Swap | **oui** si un processus Ollama a des pages en swap (Linux), si des pages sont écrites en swap ou si le swap système augmente ; **suspect** si la RAM disponible tombe sous 3 % (min. 256 Mo) ou si le modèle est rechargé en cours de route |

Le script signale aussi les blocs qui débordent de `num_ctx` (Ollama tronque le prompt sans erreur), les réponses coupées par `num_predict` et la proportion de réponses JSON valides. RSS et swap ne sont mesurés que si Ollama tourne sur la même machine.

Un document de 6 pages correspond au bail de la fixture. Un document de 10 pages prend les 6 pages du bail, puis les 4 premières pages de l'abonnement. Aucun texte de contrat n'est écrit dans les résultats ni dans la console.

```bash
cd backend
pip install -e ".[bench]"

python scripts/bench.py --dry-run     # découpage prévu, sans Ollama
python scripts/bench.py               # qwen2.5:7b-instruct + llama3.2:3b, num_ctx 2048/4096, 6/10 pages
python scripts/bench.py --models llama3.2:3b --num-ctx 2048 --pages 6 --repeats 3 --tag repli-8go
```

Options utiles : `--host` (défaut `$OLLAMA_HOST`), `--contracts all` (les 3 contrats de la fixture comme point de départ), `--repeats N`, `--num-predict` (défaut 512 tokens par bloc), `--no-monitor`. Voir `python scripts/bench.py --help`.

Les résultats bruts sont écrits dans `docs/benchmark/raw/bench_<date>[_<tag>]` en trois formats : `.json` (détail par bloc + machine + versions des modèles), `.csv` (une ligne par run) et `.md` (tableau de synthèse). Ils sont réécrits après chaque run : un benchmark interrompu (Ctrl+C) garde ses mesures.
