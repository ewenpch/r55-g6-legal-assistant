# Benchmark et choix des modèles Ollama

> Décision S1 — modèle par défaut, modèle de repli, limite de pages et fenêtre de contexte.

## Décision retenue

| Profil | Modèle | `num_ctx` | Limite PDF | Statut |
|---|---|---:|---:|---|
| Machine nominale, 16 Go de RAM | `qwen2.5:7b-instruct` Q4 | 4096 | 10 pages | Modèle par défaut du projet ; validation finale à effectuer sur la machine nominale |
| Machine de repli, 8 Go de RAM | `llama3.2:3b` Q4 | 2048 | 6 pages | Profil validé sur la machine de développement |

Le profil 8 Go doit être **explicite** : l'application indique le modèle réellement chargé et avertit l'utilisateur que le modèle 3B peut produire une analyse moins complète. Il ne faut pas tenter silencieusement le 7B puis basculer après un échec, car le test a provoqué un arrêt d'Ollama et une forte utilisation du swap.

Les valeurs par défaut du backend (`qwen2.5:7b-instruct`, `num_ctx=4096`) correspondent au profil nominal 16 Go. Sur la machine 8 Go, elles doivent être remplacées par la configuration suivante :

```env
OLLAMA_MODEL=llama3.2:3b
OLLAMA_NUM_CTX=2048
```

La limite de 6 pages appartient au profil de repli et doit être appliquée lors de la validation du PDF.

## Environnement mesuré

| Élément | Valeur |
|---|---|
| Date | 3 novembre 2026 |
| Système | Windows 11 64 bits |
| Processeur | Intel Pentium Gold 7505, 2 cœurs / 4 threads, 2,00 GHz |
| Mémoire vive | 7,73 Gio |
| Accélération | CPU uniquement, pas de CUDA |
| Ollama | 0.40.3 |
| Modèle 7B | `qwen2.5:7b-instruct`, ID `845dbda0ea48`, 4,7 Go |
| Modèle 3B | `llama3.2:3b`, ID `a80c4f17acd5`, 2,0 Go |

Cette machine représente le profil de repli 8 Go, pas la cible nominale 16 Go.

## Protocole

Deux PDF textuels ont été utilisés :

- 6 pages : `corpus/bench/bail-habitation.pdf` ;
- 10 pages : `corpus/abonnement-03-piscine-oullins-pierre-benite.pdf`.

Pour chaque cas, le texte des pages est envoyé à `/api/generate` avec une consigne identique demandant un résultat JSON, une température de `0.1`, une graine fixe (`42`) et une génération limitée à 64 tokens. Le modèle est déchargé entre les cas afin de mesurer un chargement à froid.

Les métriques viennent de la réponse Ollama (`load_duration`, `prompt_eval_count`, `prompt_eval_duration`, `eval_count`, `eval_duration`) et d'un suivi de la mémoire système. Les valeurs sont arrondies. Le RSS propre au moteur Ollama n'était pas accessible de façon fiable sous Windows ; la RAM système disponible et le swap sont donc les indicateurs mémoire retenus.

Ce protocole envoie volontairement le document entier pour éprouver la limite de contexte. En production, le texte doit être découpé en blocs : les nombres de tokens évalués montrent que les entrées longues sont tronquées.

## Résultats bruts

### Qwen 2.5 7B

| `num_ctx` | Document | Résultat | Temps mur | Chargement | Tokens prompt | Prefill | Génération | Swap observé |
|---:|---|---|---:|---:|---:|---:|---:|---:|
| 2048 | 6 pages | Succès | 198,1 s | 75,3 s | 1 026 | 16,9 tok/s | 1,17 tok/s | 4,79 Gio |
| 2048 | 10 pages | **Échec : arrêt d'Ollama** | 178,3 s avant échec | — | — | — | — | 3,78 Gio |
| 4096 | 6 pages | Non exécuté après l'arrêt à 2048 | — | — | — | — | — | — |
| 4096 | 10 pages | Non exécuté après l'arrêt à 2048 | — | — | — | — | — | — |

Le 7B n'est pas stable sur cette machine 8 Go. Tester `num_ctx=4096` après un arrêt au contexte 2048 aurait augmenté la pression mémoire sans apporter d'information utile à la décision de repli.

### Llama 3.2 3B

| `num_ctx` | Document | Temps mur | Temps Ollama | Chargement | Tokens prompt | Prefill | Génération | RAM utilisée max. | RAM disponible min. | Swap observé |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2048 | 6 pages | 45,3 s | 43,1 s | 7,3 s | 1 026 | 43,9 tok/s | 5,18 tok/s | 7,30 Gio | 0,44 Gio | 1,88 Gio |
| 2048 | 10 pages | 44,5 s | 42,3 s | 7,7 s | 1 026 | 45,0 tok/s | 5,44 tok/s | 7,23 Gio | 0,50 Gio | 1,99 Gio |
| 4096 | 6 pages | 75,5 s | 73,3 s | 9,5 s | 2 050 | 42,0 tok/s | 4,37 tok/s | 7,48 Gio | 0,26 Gio | 2,02 Gio |
| 4096 | 10 pages | 88,4 s | 86,1 s | 8,0 s | 2 050 | 34,7 tok/s | 3,43 tok/s | 7,51 Gio | 0,23 Gio | 1,95 Gio |

Les quatre cas 3B se terminent, mais `num_ctx=4096` ne laisse que 230 à 260 Mio de RAM disponible et ralentit la génération. Le contexte 2048 offre une marge légèrement meilleure et réduit le temps d'une requête à environ 45 secondes.

## Analyse et conséquences

### Stabilité mémoire

- Le 7B provoque plus de 4 Gio de swap et finit par arrêter Ollama sur le document de 10 pages : il est exclu sur 8 Go.
- Le 3B reste fonctionnel, mais utilise presque toute la mémoire. Aucun autre service lourd ne doit tourner pendant l'analyse.
- `num_ctx=4096` sur le 3B réduit trop fortement la marge disponible ; `2048` est retenu pour le profil 8 Go.

### Limite de pages

Les requêtes directes sur 6 et 10 pages sont tronquées par la fenêtre de contexte. Le pipeline doit donc analyser des blocs, puis effectuer une synthèse. Avec environ 45 secondes par appel à froid au profil 3B/2048, une limite de 6 pages laisse une marge pour plusieurs blocs et une synthèse dans le budget de 5 minutes. Dix pages sur 8 Go augmenteraient le nombre d'appels et le risque de dépassement ; cette limite est réservée au profil nominal 16 Go.

### Qualité attendue

La présente mesure porte sur la performance et la stabilité, pas sur le rappel des clauses. Le seuil de rappel de 70 % devra être calculé séparément sur `corpus/annotations.json`, en indiquant le modèle, `num_ctx` et la machine utilisés.

## Risques et mesures

| Risque constaté | Mesure retenue |
|---|---|
| Swap massif ou arrêt d'Ollama avec le 7B sur 8 Go | Interdire le profil 7B sur une machine 8 Go |
| Qualité potentiellement moindre du 3B | Afficher explicitement le modèle utilisé et un avertissement de précision réduite |
| Entrée tronquée par le contexte | Découper le contrat en blocs avec conservation des pages |
| Dépassement du budget de 5 minutes | Limiter le profil 8 Go à 6 pages et `num_ctx=2048` |
| Résultats 7B non mesurés sur 16 Go | Rejouer le protocole sur la machine nominale avant validation finale |

## Commandes d'installation

```powershell
ollama pull qwen2.5:7b-instruct
ollama pull llama3.2:3b
ollama list
ollama --version
```
