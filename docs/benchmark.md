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
