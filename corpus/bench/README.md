# Fixture de benchmark — `corpus/bench/`

Trois contrats français **fictifs** de **6 pages** chacun, servant d'entrée fixe au benchmark des modèles (tâche 6 de `docs/taches.md`, CDC §7.1). Les tâches 7 et 8 (`backend/scripts/bench.py`, mesures à `num_ctx` 2048 / 4096) s'appuient dessus.

> Ce n'est **pas** le corpus d'évaluation de la tâche 10 (9 contrats publics annotés, CDC §11.2). Ici, le but est d'avoir des documents identiques d'une machine à l'autre pour mesurer des temps, pas de mesurer la qualité.

## Contenu

| Fichier | Type | Pages | Mots | Tokens (estim.) |
|---|---|---|---|---|
| `bail-habitation.pdf` | Bail d'habitation, logement nu (loi du 6 juillet 1989), colocation | 6 | ~3 100 | ~5 500 |
| `contrat-travail-cdi.pdf` | CDI cadre au forfait jours (convention Syntec) | 6 | ~2 950 | ~5 600 |
| `abonnement-salle-sport.pdf` | Abonnement à un club de sport, engagement de 24 mois | 6 | ~2 800 | ~5 400 |

Les tokens sont estimés à ~3,5 caractères par token (texte français) ; la valeur exacte dépend du tokenizer de chaque modèle et sera relevée par le script de benchmark. Un contrat entier ne tient pas dans un `num_ctx` de 4096 : il passe forcément par le découpage en blocs (CDC §8.3.3).

Caractéristiques communes, choisies pour coller au périmètre du CDC (§5) :

- **PDF texte** (pas de scan), texte extractible page par page ;
- **mise en page simple** : une colonne, pas de tableau (CDC §9, risque « mise en page complexe ») ;
- structure en **articles numérotés** (titres `Article N – …`), comme la plupart des contrats réels, pour exercer le découpage sur les titres d'articles ;
- pied de page `Page X / 6` et mention « Document fictif », que le pipeline doit savoir ignorer ;
- personnes, sociétés et adresses **inventées**.

## Clauses à vérifier insérées volontairement

Chaque contrat mélange des clauses ordinaires et quelques clauses qui méritent l'attention d'un lecteur (déséquilibrées, inhabituelles ou probablement contraires à la loi). Elles ne servent pas au calcul des seuils d'acceptation, mais permettent un premier contrôle à l'œil lors du smoke test (tâche 26).

| Contrat | Clauses notables (article) |
|---|---|
| Bail | Pénalité forfaitaire de 40 € et intérêts à 12 % en cas de retard, frais de relance et frais de gestion mensuels à la charge du locataire (art. 17) ; solidarité des colocataires (art. 16) ; clause résolutoire (art. 15) ; assurance souscrite par le bailleur majorée de 10 % (art. 12) |
| CDI | Mobilité sur toute la France métropolitaine avec délai de 15 jours (art. 4) ; non-concurrence de 24 mois sur toute la France avec contrepartie de 10 % et pénalité de 12 mois de salaire (art. 16) ; cession de toutes les créations, même hors travail (art. 15) ; dédit-formation sans dégressivité (art. 12) ; période d'essai renouvelable, prolongée par toute absence (art. 3) ; retenue sur solde de tout compte (art. 18) |
| Abonnement | Engagement ferme de 24 mois et reconduction tacite de 12 mois avec préavis de 3 mois (art. 5) ; hausse de prix applicable pendant l'engagement (art. 7) ; déchéance du terme et frais de rejet (art. 6) ; frais de résiliation de 150 € même pour motif légitime (art. 9) ; pas de rétractation en club (art. 15) ; exonération de responsabilité pour les vols (art. 18) ; droit à l'image par défaut pendant 10 ans (art. 19) ; acceptation tacite des nouvelles conditions (art. 21) |

## Régénérer les PDF

Les PDF sont générés à partir des sources texte de `sources/` : c'est là qu'on modifie un contrat, jamais dans le PDF.

```bash
pip install reportlab pypdf
python corpus/bench/build_pdfs.py
```

Le script échoue si un PDF ne fait pas exactement 6 pages ou si une page n'a pas de texte extractible. Le rendu est déterministe : sans modification des sources, les fichiers régénérés sont identiques à l'octet près. Pour vérifier que les PDF versionnés sont à jour (en CI par exemple) :

```bash
python corpus/bench/build_pdfs.py --check
```

Après une modification de texte, vérifier que le contrat fait toujours 6 pages : ajouter ou retirer un paragraphe si besoin.
