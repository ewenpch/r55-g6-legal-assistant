# Cahier des charges — Assistant de lecture de contrats

| | |
|---|---|
| **Projet** | `r55-g6-legal-assistant` |
| **Équipe** | Ewen Pichoff, Mathys Gallienne, Malo Denis--Maignan, Johnny Granger |
| **Version** | V1 |
| **Durée prévue** | 4 semaines |

## 1. Présentation du projet

Le projet consiste à créer une application web locale qui aide un particulier à parcourir et à mieux comprendre un contrat rédigé en français. L'utilisateur importe un PDF, consulte son texte page par page et accède à des repères simples : recherche, montants, dates, mots-clés et définitions de termes juridiques courants.

La V1 est un outil d'aide à la lecture. Elle ne produit ni analyse juridique, ni recommandation, ni conclusion sur la légalité d'une clause.

## 2. Problème traité

Les contrats sont souvent longs et emploient un vocabulaire difficile à comprendre pour une personne non juriste. Les dates, montants, durées et clauses importantes peuvent être difficiles à retrouver rapidement.

L'application doit faciliter la navigation dans le document et l'identification de ces éléments, sans transmettre le contrat à un service externe. Elle ne remplace pas l'avis d'un professionnel du droit.

## 3. Utilisateurs cibles

La V1 s'adresse aux particuliers sans connaissances juridiques particulières, par exemple une personne qui souhaite relire un bail, un contrat de travail ou un contrat d'abonnement avant de le signer.

L'utilisateur cible sait utiliser un navigateur et importer un fichier, mais souhaite disposer d'une interface plus accessible qu'un lecteur PDF classique.

## 4. Cas d'usage principal

> En tant que particulier, je veux importer un contrat au format PDF afin de le parcourir plus facilement et de retrouver rapidement ses dates, montants et termes importants.

Parcours principal :

1. L'utilisateur ouvre l'application.
2. Il sélectionne ou dépose un fichier PDF.
3. L'application vérifie le format, la taille et la présence de texte extractible.
4. Le texte du contrat est affiché page par page.
5. L'utilisateur consulte les repères détectés, recherche un mot et ouvre les définitions proposées.
6. Il supprime le document ou quitte la consultation.

## 5. Fonctionnalités de la V1

Les fonctionnalités prévues sont :

- importer un PDF par sélection ou glisser-déposer ;
- refuser les fichiers non PDF, supérieurs à 5 Mo ou à 10 pages ;
- signaler les PDF scannés dont aucun texte ne peut être extrait ;
- extraire et afficher le texte en conservant les numéros de page ;
- naviguer entre les pages du document ;
- rechercher un mot ou une expression dans le texte ;
- repérer, à l'aide de règles déterministes, les dates et les montants présents dans le document ;
- mettre en évidence une liste définie de mots-clés contractuels, comme « durée », « résiliation », « préavis », « renouvellement » ou « pénalité » ;
- afficher un glossaire statique pour les termes juridiques connus par l'application ;
- afficher en permanence un avertissement précisant que l'outil ne fournit pas de conseil juridique ;
- supprimer le document et les données extraites à la demande de l'utilisateur.

## 6. Hors périmètre

Ne font pas partie de la V1 :

- toute fonctionnalité d'IA générative ;
- l'analyse automatique de la légalité, du risque ou du caractère abusif d'une clause ;
- le résumé automatique du contrat ;
- les recommandations juridiques et les références automatiques à la loi ou à la jurisprudence ;
- la génération ou la modification de contrats et de courriers ;
- les questions-réponses automatiques sur le document ;
- l'OCR des documents scannés et l'import de photos ;
- les langues autres que le français ;
- les comptes utilisateurs, l'authentification, l'historique et le partage de documents ;
- la mise en ligne publique de l'application.

## 7. Écrans principaux

### Écran d'accueil et d'import

Il présente brièvement le service, ses limites et une zone permettant de sélectionner ou de déposer un PDF. Les contraintes de format, de taille et de nombre de pages sont visibles avant l'import.

### Écran de consultation

Il affiche le texte du contrat, le numéro de la page consultée, les commandes de navigation et un champ de recherche. Un panneau regroupe les dates, montants et mots-clés repérés. Un clic sur un résultat amène l'utilisateur à son emplacement dans le document.

### Glossaire

Il affiche les définitions courtes des termes reconnus. Il peut prendre la forme d'un panneau latéral ou d'une fenêtre accessible depuis un terme mis en évidence.

### États d'erreur

L'interface affiche un message compréhensible pour un mauvais format, un fichier trop volumineux, un document trop long, un PDF sans texte extractible ou une erreur technique.

## 8. Données manipulées

L'application manipule :

- le fichier PDF importé ;
- le texte extrait, séparé par page ;
- les occurrences trouvées lors d'une recherche ;
- les dates, montants et mots-clés détectés par des règles ;
- les définitions du glossaire, fournies avec l'application.

Le document et son texte restent locaux. Ils sont conservés uniquement pendant la consultation, sans base de données, puis supprimés au plus tard une heure après l'import. Leur contenu ne doit jamais apparaître dans les journaux techniques.

## 9. Stack technique

| Partie | Technologie envisagée | Rôle |
|---|---|---|
| Interface | React, Vite et TypeScript | Import, navigation et affichage du document |
| Serveur | Python et FastAPI | Validation du fichier et exposition de l'API locale |
| Lecture PDF | PyMuPDF | Extraction du texte page par page |
| Repérage | Expressions régulières et listes de mots-clés | Détection déterministe des dates, montants et termes connus |
| Tests | pytest et Vitest | Tests du serveur et de l'interface |
| Qualité | Ruff, ESLint et Prettier | Vérification et formatage du code |

## 10. Architecture générale

L'application est composée de deux parties exécutées localement :

```text
Navigateur (React)
        |
        | HTTP / JSON
        v
API locale (FastAPI)
        |
        +-- validation du PDF
        +-- extraction du texte par page
        +-- détection par règles
        +-- stockage temporaire en mémoire
```

Le navigateur envoie le PDF à l'API locale. Le serveur vérifie le fichier, extrait son texte et renvoie les pages ainsi que les repères détectés. Aucun service distant n'est nécessaire au fonctionnement de la V1.

## 11. IA envisagée pour la suite

Dans une version future seulement, un modèle de langage exécuté localement pourrait produire un résumé en langage clair et suggérer des clauses à vérifier, avec citation obligatoire du texte source et avertissement explicite sur les limites de l'analyse.

## 12. Contraintes

- La V1 doit fonctionner sans IA générative et sans API externe.
- Seuls les PDF textuels en français, de 10 pages et 5 Mo maximum, sont acceptés.
- Les documents scannés ne sont pas pris en charge.
- Le document et le texte extrait ne doivent pas quitter la machine de l'utilisateur.
- L'application ne conserve ni compte ni historique et ne nécessite pas de base de données.
- Le parcours principal doit rester utilisable sur ordinateur et mobile, au clavier comme à la souris.
- Les textes et contrastes doivent respecter les principes de base de l'accessibilité web.
- Un avertissement visible doit rappeler que l'application ne fournit pas de conseil juridique et que les repères affichés peuvent être incomplets.
- Le projet doit rester réalisable par quatre personnes en quatre semaines.
- Chaque fonctionnalité est considérée comme terminée lorsqu'elle a été relue, testée, commitée et poussée sur le dépôt.
