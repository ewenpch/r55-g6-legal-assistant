# Cahier des charges — r55-g6-legal-assistant

> Application d'aide à la compréhension de contrats, assistée par une IA exécutée en local.

| | |
|---|---|
| **Équipe** | Ewen Pichoff, Mathys Gallienne, Malo Denis--Maignan, Johnny Granger |
| **Durée** | 4 semaines |
| **Version** | 1.0 |

---

## 1. Contexte et problème

Les particuliers signent régulièrement des contrats (bail, contrat de travail, abonnement, crédit, assurance…) sans réellement les comprendre : vocabulaire juridique, documents longs, clauses importantes noyées dans le texte. Consulter un avocat pour relire chaque contrat est coûteux et rarement fait.

**Problème à résoudre :** permettre à un particulier de comprendre rapidement ce qu'il s'apprête à signer — qui s'engage à quoi, pour combien, pour combien de temps — et de repérer les clauses qui méritent son attention, sans envoyer un document personnel à un service tiers.

## 2. Objectifs

1. Expliquer un contrat en **langage clair** (niveau « non-juriste »).
2. **Extraire** les informations clés : parties, objet, durée, dates, montants, obligations.
3. **Signaler** les clauses à vérifier, en citant le texte original.
4. **Garantir la confidentialité** : le document n'est jamais envoyé à un service externe (IA locale) et n'est pas conservé.

### Ce que l'application n'est pas

L'application **ne fournit pas de conseil juridique**. Elle aide à lire un contrat ; elle ne remplace pas un professionnel du droit. Un avertissement visible le rappelle sur chaque analyse (voir §7.4).

## 3. Utilisateurs

**Cible unique : les particuliers**, sans connaissances juridiques.

**Persona — Léa, 24 ans, jeune active**
- Va signer son premier bail et un contrat de travail en CDD.
- À l'aise avec le web, mais ne comprend pas « clause résolutoire » ou « préavis ».
- Ne veut pas envoyer ses documents personnels (identité, salaire, adresse) à un service en ligne.
- Attend une réponse simple : « Est-ce qu'il y a un piège dans ce contrat ? »

## 4. Cas d'usage principal

> **En tant que** particulier, **je veux** importer le PDF d'un contrat **afin d'**obtenir un résumé clair et la liste des points à vérifier avant de signer.

### Scénario nominal

1. L'utilisateur ouvre l'application dans son navigateur.
2. Il dépose un fichier PDF (glisser-déposer ou sélection).
3. L'application vérifie le fichier (format, taille, nombre de pages, présence de texte).
4. L'analyse démarre ; une barre de progression indique l'étape en cours.
5. L'utilisateur obtient une page de résultat :
   - type de contrat détecté et résumé en quelques phrases ;
   - fiche d'identité : parties, objet, durée, dates clés, montants ;
   - obligations de chaque partie ;
   - clauses à vérifier, classées par importance, avec l'extrait original et une explication simple.
6. Il peut cliquer sur une clause pour voir l'extrait dans son contexte (numéro de page).
7. En quittant la page, le document et l'analyse sont supprimés.

### Scénarios d'erreur

| Situation | Comportement attendu |
|---|---|
| Fichier non PDF | Message : « Seuls les fichiers PDF sont acceptés. » |
| PDF scanné (pas de texte extractible) | Message expliquant que les scans ne sont pas pris en charge dans cette version. |
| Document > 10 pages ou > 5 Mo | Refus avec message indiquant la limite. |
| Document qui n'est pas un contrat | Avertissement « Ce document ne semble pas être un contrat », analyse non réalisée. |
| Document non francophone | Message : seule la langue française est prise en charge. |
| Modèle IA indisponible / délai dépassé | Message d'erreur clair et possibilité de relancer. |

## 5. Périmètre

### 5.1 Décisions de simplification

Plusieurs propositions initiales ont été jugées trop ambitieuses pour 4 semaines et un PC portable sans GPU :

| Proposition initiale | Décision | Raison |
|---|---|---|
| Analyser tout type de contrat sans limite | Contrats **en français**, **≤ 10 pages** ; analyse **générique** non exhaustive | Fenêtre de contexte et vitesse d'un modèle 7B sur CPU |
| Liste de clauses abusives par type de contrat | Pas de base de règles ; l'IA signale les clauses « à vérifier » | Impossible à constituer pour tous les types en 4 semaines |
| PDF + images scannées | **PDF texte uniquement** | L'OCR ajoute une brique lourde et peu fiable |
| Comptes utilisateurs + historique | **Aucun compte, aucune conservation** | Moins de travail, et meilleur pour la confidentialité (RGPD) |
| Base PostgreSQL | **Pas de base de données** | Plus nécessaire sans comptes ni historique |
| Chat de questions/réponses sur le contrat | Reporté (« Could ») | Le cas d'usage principal est la lecture guidée |
| Citer la loi / la jurisprudence | Hors périmètre | Risque élevé d'hallucination, nécessiterait une base juridique (RAG) |

Le jeu de test se concentre sur **3 types de contrats** représentatifs : bail d'habitation, contrat de travail, contrat d'abonnement (téléphonie/salle de sport).

### 5.2 Dans le périmètre

- Import d'un PDF texte, en français, ≤ 10 pages, ≤ 5 Mo.
- Analyse générique du contrat par un LLM local.
- Page de résultat structurée (§4, étape 5).
- Interface web responsive (ordinateur et mobile).

### 5.3 Hors périmètre

- OCR / documents scannés, photos.
- Comptes, authentification, historique.
- Langues autres que le français.
- Génération ou modification de contrats, rédaction de courriers.
- Références à des textes de loi ou à la jurisprudence.
- Mise en ligne publique de l'application (usage local / démonstration).

## 6. Exigences fonctionnelles

Priorisation **MoSCoW** : *Must* (indispensable au MVP), *Should* (important), *Could* (si le temps le permet).

| ID | Exigence | Priorité |
|---|---|---|
| F1 | Importer un fichier PDF par glisser-déposer ou sélection | Must |
| F2 | Valider le fichier : type, taille ≤ 5 Mo, ≤ 10 pages, texte extractible | Must |
| F3 | Extraire le texte du PDF en conservant le numéro de page | Must |
| F4 | Détecter si le document est un contrat et identifier son type | Must |
| F5 | Produire un résumé en langage clair (5 phrases max) | Must |
| F6 | Extraire la fiche d'identité : parties, objet, durée, dates clés, montants | Must |
| F7 | Lister les obligations de chaque partie | Must |
| F8 | Lister les clauses à vérifier avec : extrait original, explication simple, niveau (info / attention / important), page | Must |
| F9 | Vérifier côté serveur que chaque extrait cité existe bien dans le document ; écarter sinon | Must |
| F10 | Afficher la progression de l'analyse (étape en cours) | Should |
| F11 | Afficher l'avertissement « ceci n'est pas un conseil juridique » | Must |
| F12 | Afficher un extrait dans son contexte au clic sur une clause | Should |
| F13 | Glossaire : définition des termes juridiques détectés au survol | Could |
| F14 | Exporter l'analyse en PDF | Could |
| F15 | Poser une question libre sur le contrat analysé | Could |

## 7. Exigences non fonctionnelles

### 7.1 Performance

- Analyse d'un contrat de 10 pages en **moins de 5 minutes** sur la machine cible (PC portable, CPU, 16 Go de RAM).
- Interface réactive pendant l'analyse (traitement asynchrone + suivi de l'état).
- Un benchmark est réalisé en semaine 1 ; si l'objectif n'est pas tenu, on bascule sur un modèle plus petit ou on réduit la limite de pages.

### 7.2 Confidentialité et données personnelles

- **Aucun appel à une API externe** : le LLM tourne en local.
- Document et résultat conservés **uniquement en mémoire**, supprimés après consultation ou au plus tard 1 heure après l'analyse.
- Aucun contenu de document dans les logs.

### 7.3 Fiabilité de l'IA

- Sortie du modèle au **format JSON imposé** (schéma §8.4), validée par Pydantic ; nouvelle tentative (1 max) si invalide.
- Toute clause signalée doit citer le texte original (F9) : limite les hallucinations.
- Température basse (≈ 0,1–0,2) pour des résultats stables.

### 7.4 Responsabilité

- Bandeau permanent : « Cette analyse est générée automatiquement et peut contenir des erreurs. Elle ne constitue pas un conseil juridique. En cas de doute, consultez un professionnel (avocat, ADIL, association de consommateurs). »
- Formulations prudentes : « clause à vérifier » plutôt que « clause illégale ».

### 7.5 Ergonomie et accessibilité

- Parcours en 3 écrans maximum : import → progression → résultat.
- Vocabulaire non juridique, contrastes et navigation clavier conformes aux bases du RGAA.
- Responsive (mobile et ordinateur).

### 7.6 Qualité du code

- Lint/format : Ruff (Python), ESLint + Prettier (React).
- Tests unitaires backend (pytest) sur l'extraction PDF, la validation et la vérification des citations.
- Revue de code par pull request avant fusion dans `main`.

## 8. Architecture et stack technique

### 8.1 Stack

| Couche | Choix | Justification |
|---|---|---|
| Frontend | **React** (Vite, TypeScript) | Connu de l'équipe, outillage rapide |
| Backend | **Python / FastAPI** | Écosystème IA et PDF en Python, validation Pydantic native |
| Extraction PDF | **PyMuPDF** (ou pdfplumber) | Texte par page, rapide |
| LLM | **Ollama** + modèle 7–8B quantifié (Q4) | Exécution locale sur CPU |
| Modèle candidat | Qwen2.5-7B-Instruct ou Mistral-7B-Instruct ; repli : Llama 3.2 3B | Bon français, sortie JSON ; choix final après benchmark semaine 1 |
| Stockage | Mémoire du processus (dictionnaire avec expiration) | Pas de comptes ni d'historique |
| Tests | pytest, Vitest | |

### 8.2 Schéma

```
┌──────────────┐  HTTP/JSON   ┌───────────────────────────┐   HTTP    ┌─────────────┐
│ React (Vite) │ ───────────▶ │ FastAPI                   │ ────────▶ │ Ollama      │
│  - Upload    │ ◀─────────── │  - validation PDF         │ ◀──────── │ (LLM local) │
│  - Progress  │   polling    │  - extraction texte/page  │           └─────────────┘
│  - Résultat  │              │  - découpage + prompts    │
└──────────────┘              │  - vérification citations │
                              │  - stockage mémoire (TTL) │
                              └───────────────────────────┘
```

### 8.3 Pipeline d'analyse

1. **Extraction** du texte page par page.
2. **Contrôles** : texte présent, langue française, document de type contrat (prompt court).
3. **Découpage** en blocs (~2 000 tokens) en respectant les articles/sections si possible.
4. **Analyse par bloc** : extraction des informations et des clauses à vérifier.
5. **Synthèse** : fusion des résultats, dédoublonnage, résumé global.
6. **Vérification** des citations (recherche approximative de l'extrait dans le texte source) ; clauses non retrouvées écartées.

### 8.4 API

| Méthode | Route | Description |
|---|---|---|
| `POST` | `/api/analyses` | Envoie le PDF (multipart). Retourne `{ "id": "...", "status": "pending" }` |
| `GET` | `/api/analyses/{id}` | Retourne l'état (`pending`, `running`, `done`, `error`), l'étape en cours et le résultat si terminé |
| `DELETE` | `/api/analyses/{id}` | Supprime immédiatement document et résultat |
| `GET` | `/api/health` | Vérifie que l'API et Ollama répondent |

Format du résultat :

```json
{
  "contract_type": "Bail d'habitation",
  "summary": "Contrat de location d'un appartement meublé ...",
  "parties": [{ "name": "M. Dupont", "role": "Bailleur" }],
  "object": "Location d'un T2 situé à ...",
  "duration": "1 an, renouvelable tacitement",
  "key_dates": [{ "label": "Prise d'effet", "date": "2026-09-01" }],
  "amounts": [{ "label": "Loyer mensuel", "value": "750 € charges comprises" }],
  "obligations": [{ "party": "Locataire", "items": ["Payer le loyer avant le 5 du mois"] }],
  "clauses_to_check": [
    {
      "title": "Pénalité de retard",
      "quote": "Tout retard de paiement entraînera une pénalité de 50 € par jour.",
      "explanation": "Le montant de cette pénalité est élevé ; renseignez-vous avant de signer.",
      "level": "important",
      "page": 3
    }
  ]
}
```

## 9. Contraintes et risques

| Risque | Impact | Mesure |
|---|---|---|
| Lenteur du modèle sur CPU | Analyse > 5 min | Benchmark semaine 1 ; modèle 3B en repli ; limite de pages ajustable |
| Hallucinations (clauses inventées) | Perte de confiance, information fausse | Citation obligatoire + vérification côté serveur (F9) ; avertissement |
| Analyse incomplète (clause importante manquée) | Faux sentiment de sécurité | Formulation « points relevés, liste non exhaustive » ; tests sur corpus |
| JSON invalide renvoyé par le modèle | Erreur d'affichage | Mode JSON d'Ollama + validation Pydantic + 1 nouvelle tentative |
| Mise en page PDF complexe (colonnes, tableaux) | Texte mal extrait | Hors périmètre ; corpus de test choisi en conséquence |
| Délai de 4 semaines | Fonctionnalités non livrées | MoSCoW strict : les *Could* ne sont commencés qu'une fois les *Must* terminés |

## 10. Planning (4 semaines)

| Semaine | Objectifs | Livrables |
|---|---|---|
| **S1** — Fondations | Squelettes React + FastAPI, installation Ollama, **benchmark des modèles**, constitution du corpus de test (≥ 9 contrats : 3 par type) | Repo initialisé, choix du modèle documenté, corpus annoté |
| **S2** — Pipeline IA | Extraction PDF, validations (F2–F3), prompts et découpage, sortie JSON validée, vérification des citations (F4–F9) | API `/api/analyses` fonctionnelle en ligne de commande |
| **S3** — Interface | Écrans import / progression / résultat, intégration API, avertissement (F1, F10–F12) | MVP utilisable de bout en bout |
| **S4** — Fiabilisation | Tests sur le corpus, ajustement des prompts, gestion des erreurs, accessibilité, *Could* si temps, préparation de la démo | Version finale, README d'installation, démo |

### Répartition indicative des rôles

| Rôle | Responsabilités |
|---|---|
| Frontend | Interface React, parcours utilisateur, accessibilité |
| Backend | API FastAPI, extraction et validation PDF, stockage mémoire |
| IA | Benchmark modèles, prompts, découpage, synthèse, vérification des citations |
| Qualité / corpus | Corpus de test annoté, tests, documentation, préparation de la démo |

Les rôles sont attribués lors du lancement du projet ; chacun relit les pull requests d'au moins un autre rôle.

## 11. Critères d'acceptation

Le MVP est accepté si :

1. Toutes les exigences **Must** sont implémentées.
2. Sur le corpus de test (≥ 9 contrats, 3 types) :
   - le type de contrat est correctement identifié dans **≥ 8 cas sur 9** ;
   - **≥ 70 %** des clauses à vérifier annotées manuellement sont détectées ;
   - **0** extrait cité qui n'existe pas dans le document (grâce à F9).
3. Une analyse de 10 pages se termine en **moins de 5 minutes** sur la machine cible.
4. Aucune requête réseau sortante vers un service tiers pendant une analyse.
5. Les scénarios d'erreur du §4 affichent le message attendu.

## 12. Glossaire

| Terme | Définition |
|---|---|
| **LLM** | *Large Language Model* : modèle d'IA générant du texte. |
| **Ollama** | Outil permettant d'exécuter un LLM sur sa propre machine. |
| **Quantification (Q4)** | Compression d'un modèle pour réduire sa taille mémoire, au prix d'une légère perte de qualité. |
| **Hallucination** | Information inventée par le modèle et présentée comme vraie. |
| **MoSCoW** | Méthode de priorisation : *Must, Should, Could, Won't*. |
| **OCR** | Reconnaissance de texte dans une image (document scanné). |
| **RGPD** | Règlement général sur la protection des données. |
