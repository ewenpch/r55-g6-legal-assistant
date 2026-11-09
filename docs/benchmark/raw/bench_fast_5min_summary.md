# Resultats bruts du benchmark

- Date : 2026-11-03T14:56:36.361555+00:00
- Hote Ollama : http://localhost:11434
- Version Ollama : 0.40.14
- Mode : chunked
- Repetitions : 1
- Contrat : bail

| Modele | ctx | pages | runs | charge (s) | temps chaud median (s) | s/page | prefill tok/s | gen tok/s | RSS pic (Mo) | JSON valide |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| llama3.2:3b | 2048 | 6 | 1 | 8.64 | 32.68 | 5.45 | 63.95 | 7.44 | 2336.1 | 0 |
| llama3.2:3b | 4096 | 6 | 1 | 3.17 | 26.36 | 4.39 | 64.34 | 7.91 | 2560.2 | 0 |
| qwen2.5:7b-instruct | 2048 | 6 | 1 | 17.37 | 65.93 | 10.99 | 28.92 | 4.5 | 4831.9 | 0 |
| qwen2.5:7b-instruct | 4096 | 6 | 1 | 7.69 | 56.69 | 9.45 | 28.89 | 4.48 | 4944.2 | 0 |

Notes :
- `charge` est la mediane du temps de chargement des runs a froid.
- `temps chaud median` exclut le chargement du modele.
- `RSS pic` est vide si Ollama tourne sur un hote distant.
- `JSON valide` est la proportion de blocs dont la reponse est un JSON parsable.
- Le mode chunké decoupe le document selon `num_ctx - reserve`.

- Mode express : 1 bloc par config et sortie courte ; `JSON valide` n'est pas representatif.