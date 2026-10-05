# Découpage en tâches — r55-g6-legal-assistant

> Décomposition du cahier des charges (`docs/CDC.md`, v1.0) en tâches ordonnées, prêtes à être assignées.
> Chaque tâche est petite, vérifiable et rattachée à une section du CDC.

| | |
|---|---|
| **Équipe** | Ewen Pichoff, Mathys Gallienne, Malo Denis--Maignan, Johnny Granger |
| **Durée** | 4 semaines |
| **Document lié** | `docs/CDC.md` |
| **Version** | 1.0 |

---

## Conventions

- Les identifiants `F*`, `§*` renvoient au CDC : `F4` = exigence fonctionnelle F4, `§7.1` = section 7.1.
- L'ordre est impératif : une tâche ne démarre pas avant que celle qui la précède soit faite et relue.
- Priorité MoSCoW : les *Could* ne sont jamais commencés avant que tous les *Must* soient verts.
- Chaque tâche se termine par une pull request relue par un autre rôle (§10).

## Rôles

| Rôle | Abréviation | Responsabilités |
|---|---|---|
| Frontend | `FE` | Interface React, parcours utilisateur, accessibilité |
| Backend | `BE` | API FastAPI, extraction et validation PDF, stockage mémoire |
| IA | `IA` | Benchmark modèles, prompts, découpage, synthèse, vérification des citations |
| Qualité / corpus | `QC` | Corpus annoté, tests, documentation, démo |

---

## S1 — Fondations

| # | Tâche | Rôle | CDC | Livrable |
|---|---|---|---|---|
| 1 | Créer l'arborescence `backend/`, `frontend/`, `corpus/`, `docs/` | BE | — | Arborescence poussée |
| 2 | Scaffolder FastAPI + `pyproject.toml` + Ruff + pytest | BE | §7.6 | `backend/` lançable, `GET /api/health` répond |
| 3 | Implémenter `GET /api/health` (API + joignabilité Ollama) | BE | §8.4 | Route opérationnelle, returns modèle chargé |
| 4 | Scaffolder Vite + React + TS + ESLint + Prettier + Vitest | FE | §7.6 | `frontend/` lançable |
| 5 | Installer Ollama, pulls `qwen2.5:7b-instruct` et `llama3.2:3b` | IA | §8.1 | Versions notées dans `docs/benchmark.md` |
| 6 | Rédiger 3 contrats français de 6 pages (fixture benchmark) | QC | §7.1 | 3 PDF texte dans `corpus/bench/` |
| 7 | Script de benchmark : temps de chargement, prefill tok/s, génération tok/s, RSS pic, détection de swap | IA | §7.1 | `backend/scripts/bench.py` |
| 8 | Benchmark à `num_ctx` 2048 puis 4096, sur 6 puis 10 pages, pour les 2 modèles | IA | §7.1 | Résultats bruts |
| 9 | Décider modèle par défaut, page limit et `num_ctx` ; rédiger `docs/benchmark.md` | IA + QC | §7.1, §9 | Modèle et limites actés |
| 10 | Constituer le corpus : 9 contrats français publics (3 bail, 3 travail, 3 abonnement) | QC | §11.2 | PDF dans `corpus/` |
| 11 | Annoter le corpus : type attendu + clauses à vérifier repérées à la main | QC | §11.2 | `corpus/annotations.json` |

### Points d'attention S1

- Le **modèle par défaut reste un 7–8B Q4** (§8.1). Le 3B est le repli, pas le défaut.
- Le benchmark doit répondre à deux questions, pas une : *le 7B tourne-t-il de façon stable sur 8 Go*, et *avec quel `num_ctx`*. Sans la seconde, le plafond de stabilité reste inconnu.
- Chaque PDF du corpus doit être **texte extractible et en français** : le vérifier à l'entrée, sinon il sort du périmètre (§5.3).

---

## S2 — Pipeline IA

| # | Tâche | Rôle | CDC | Livrable |
|---|---|---|---|---|
| 12 | Store mémoire : `id` → doc + résultat + statut, TTL 1 h, suppression explicite | BE | §7.2, §8.1 | Module testé |
| 13 | Validation upload : extension, ≤ 5 Mo, nombre de pages, présence de texte | BE | F2 | Un message distinct par cas d'échec (§4) |
| 14 | Extraction texte page par page avec numéros de page (PyMuPDF) | BE | F3 | Tests unitaires |
| 15 | Pré-contrôles : détection français, détection « est un contrat », typologie | IA | F4 | Messages §4 pour non-contrat et non-français |
| 16 | Découpage ~2 000 tokens sur les titres d'articles, offsets de page conservés | IA | §8.3.3 | Blocs + métadonnées de page |
| 17 | Modèles Pydantic : forme §8.4 + forme par bloc | IA | §8.4, §7.3 | Schémas validés |
| 18 | Prompts par bloc F5–F8 : citation obligatoire, niveaux info/attention/important, temp 0.1–0.2, mode JSON | IA | F5–F8, §7.3 | Prompts versionnés |
| 19 | Fusion, dédoublonnage, résumé global | IA | §8.3.5 | Résultat conforme §8.4 |
| 20 | Vérification des citations : recherche approximative dans la page source, clause écartée si absente | IA | F9 | Tests sur citations vraies et fausses |
| 21 | Une nouvelle tentative sur JSON invalide | BE | §7.3 | Retry borné à 1 |
| 22 | `POST /api/analyses` (multipart → `{id, status}`) | BE | §8.4 | Route opérationnelle |
| 23 | `GET /api/analyses/{id}` (statut, étape courante, résultat) | BE | §8.4 | Route opérationnelle |
| 24 | `DELETE /api/analyses/{id}` (suppression immédiate) | BE | §8.4, §4 | Route opérationnelle |
| 25 | Tests pytest : extraction, validation, vérification des citations | BE | §7.6 | Suite verte |
| 26 | Smoke test de bout en bout en ligne de commande | IA | — | Un contrat analysé entièrement sans le front |

---

## S3 — Interface

| # | Tâche | Rôle | CDC | Livrable |
|---|---|---|---|---|
| 27 | Layout applicatif + bandeau d'avertissement permanent | FE | F11, §7.4 | Texte exact §7.4 affiché |
| 28 | Écran d'import : glisser-déposer + sélecteur de fichier | FE | F1 | Parcours utilisable au clavier |
| 29 | Écran de progression : polling + étape en cours | FE | F10 | Avancement visible |
| 30 | Résultat : type, résumé, fiche d'identité (parties, objet, durée, dates, montants) | FE | F4–F6 | Sections rendues |
| 31 | Résultat : obligations de chaque partie | FE | F7 | Sections rendues |
| 32 | Résultat : liste des clauses par niveau, avec extrait, explication, page | FE | F8 | Liste hiérarchisée |
| 33 | Clic sur une clause → extrait dans son contexte, page indiquée | FE | F12 | Extrait élargi |
| 34 | Suppression du document et du résultat au départ de la page résultat | FE | §4 étape 7 | `DELETE` appelé |
| 35 | Rendu de tous les scénarios d'erreur du §4 avec leur message attendu | FE | §4, §11.5 | 6 messages conformes |
| 36 | Passes responsive + clavier + contrastes (bases RGAA) | FE | §7.5 | Parcours complet au clavier |
| 37 | Vitest sur 2 à 3 composants | FE | §7.6 | Suite verte |

---

## S4 — Fiabilisation

| # | Tâche | Rôle | CDC | Livrable |
|---|---|---|---|---|
| 38 | Passage sur le corpus complet, mesure des 3 chiffres d'acceptation | QC + IA | §11.2 | Type ≥ 8/9, rappel ≥ 70 %, 0 citation inventée |
| 39 | Ajuster prompts et taille de blocs jusqu'à tenir les seuils | IA | §11.2 | Résultats consignés dans `docs/` |
| 40 | Vérifier le budget de temps sur la machine cible | IA | §7.1 | Temps mesurés |
| 41 | README : installation d'Ollama, pull du modèle, lancement des deux serveurs | QC | §10 | README à jour |
| 42 | *Could* : glossaire au survol | FE | F13 | Si temps |
| 43 | *Could* : export de l'analyse en PDF | FE | F14 | Si temps |
| 44 | *Could* : question libre sur le contrat analysé | IA | F15 | Si temps |

---

## Révisions du CDC retenues

Décisions prises lors du découpage, à intégrer au CDC (§7.1 et §9).

**§7.1 Performance et mémoire.** La machine de développement fait 7,9 Go de RAM, CPU Intel HD Graphics 630 sans CUDA. Le CDC retenait 16 Go et ne mentionnait pas de mode dégradé.

| Réglage | Valeur |
|---|---|
| Machine cible (nominale) | 16 Go |
| Machine de repli | 8 Go, CPU seul, documentée |
| Modèle par défaut | 7–8B Q4 sur 16 Go |
| Repli automatique | 3B Q4 sur 8 Go, ≤ 6 pages |
| Budget de temps | < 5 min pour 10 pages sur machine nominale |
| Budget de temps (repli) | < 5 min pour 6 pages sur 8 Go |

**§9 Risques.** Ajouter : *sur 8 Go, le 7B peut swapper ; le contrôle de santé doit indiquer le modèle réellement chargé afin que l'interface puisse avertir l'utilisateur.*

**§11.2.** Les chiffres d'acceptation doivent préciser le modèle et la machine qui les ont produits, sinon ils ne sont pas reproductibles d'une machine à l'autre.

---

## Décision en attente

**Repli automatique ou explicite ?** Sur 8 Go, le modèle 3B est plus rapide mais moins fiable : c'est lui qui produit le chiffre de rappel de 70 % (§11.2).

- *Automatique* : l'utilisateur ne voit jamais d'erreur, mais la différence de qualité reste invisible.
- *Explicite* : l'interface indique le modèle utilisé et avertit que l'analyse est moins précise.

À trancher avant la tâche 12, car le mécanisme de sélection du modèle conditionne le store mémoire et la route de santé.