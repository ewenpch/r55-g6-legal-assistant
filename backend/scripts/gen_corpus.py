"""Genere un contrat de bail synthetique en versions 6 et 10 pages.

Le contenu est volontairement redondant et stable : il sert uniquement de
support de benchmark (texte francais extractible, plusieurs pages, plusieurs
articles). Il ne constitue pas un modele juridique.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from fpdf import FPDF
from fpdf.enums import MethodReturnValue

FONT_REGULAR = Path(r"C:\Windows\Fonts\arial.ttf")
FONT_BOLD = Path(r"C:\Windows\Fonts\arialbd.ttf")

PAGE_W, PAGE_H = 210, 297
MARGIN_X = 18
MARGIN_TOP = 20
MARGIN_BOTTOM = 20
LINE_H = 5.2
BODY_SIZE = 10.5

CONTRACT_TITLE = "CONTRAT DE BAIL D'HABITATION"
CONTRACT_SUBTITLE = "Location d'un logement a usage de residence principale"


ARTICLES: list[tuple[str, list[str]]] = [
    (
        "Article 1 - Designation des parties",
        [
            "Le present contrat de bail d'habitation est conclu entre les soussignes : "
            "d'une part, Monsieur et Madame Dupont, demeurant 12 rue des Lilas, 75011 Paris, "
            "ci-apres designes collectivement le bailleur, et d'autre part, Madame Lea Martin, "
            "demeurant actuellement 8 avenue Victor Hugo, 93100 Montreuil, ci-apres designee "
            "la locataire. Les parties declarent avoir la capacite juridique de contracter et "
            "s'engagent a executer les obligations mises a leur charge par le present acte.",
            "Le bailleur declare etre proprietaire du logement objet du present contrat et "
            "justifier de la libre disposition de celui-ci pendant toute la duree du bail. "
            "La locataire declare destiner les lieux a son habitation principale et personnelle. "
            "Toute utilisation professionnelle, commerciale ou artisanale est interdite sans "
            "accord ecrit prealable du bailleur.",
            "Les parties elisent domicile aux adresses indiquees ci-dessus pour l'execution du "
            "present contrat. Toute notification relative au bail devra etre adressee par lettre "
            "recommendee avec avis de reception ou remise en main propre contre recu. En cas de "
            "changement d'adresse, chaque partie s'engage a informer l'autre dans un delai de "
            "quinze jours par tout moyen ecrit.",
        ],
    ),
    (
        "Article 2 - Objet du bail",
        [
            "Le bailleur donne en location a la locataire un appartement de type T2 situe au "
            "3e etage de l'immeuble du 12 rue des Lilas, 75011 Paris, comprenant une entree, "
            "un sejour, une chambre, une cuisine equipee, une salle de bains avec WC, ainsi "
            "qu'une cave numero 14 situee au sous-sol. La superficie habitable est estimee a "
            "quarante-huit metres carres selon la surface mentionnee dans le diagnostic joint.",
            "Le logement est loue meuble au sens des dispositions applicables. L'inventaire "
            "du mobilier et de l'equipement est annexe au present contrat. La locataire reconnait "
            "avoir visite les lieux et les avoir trouves en bon etat d'usage et de reparation, "
            "sous reserve des observations consignees dans l'etat des lieux contradictoire.",
            "Le logement comporte les equipements suivants : cuisine amenagee avec plaques de "
            "cuisson, refrigerateur, four encastrable, hotte aspirante, salle de bains avec "
            "baignoire, lavabo et WC, chauffage collectif, fenetres en double vitrage, "
            "interphone et acces a la fibre optique. Le bailleur ne garantit pas l'eligibilite "
            "des lieux a un usage professionnel ni la presence d'un local commercial.",
        ],
    ),
    (
        "Article 3 - Duree du bail",
        [
            "Le present bail est conclu pour une duree d'un an a compter du 1er septembre 2026 "
            "et prendra fin le 31 aout 2027. Il se renouvelle ensuite par periodes d'un an, "
            "sauf congé delivre par l'une ou l'autre des parties dans les conditions et delais "
            "prevus par les textes en vigueur et rappeles a l'article 14 du present contrat.",
            "La prise de possession des lieux interviendra au plus tard le 1er septembre 2026. "
            "La remise des cles sera effectuee contre signature d'un etat des lieux etabli de "
            "maniere contradictoire. Un jeu de trois cles sera remis a la locataire, ainsi que "
            "le badge d'acces a l'immeuble et la telecommande du portail du parking.",
            "Le bail ne peut etre prolonge au-dela de la duree convenue que par un avenant "
            "ecrit signe par les deux parties. Le maintien dans les lieux apres l'echeance du "
            "bail sans opposition du bailleur ne vaut pas renouvellement automatique et ne "
            "cree aucun droit acquis au profit de la locataire, conformement aux dispositions "
            "applicables aux baux d'habitation.",
        ],
    ),
    (
        "Article 4 - Loyer et modalites de paiement",
        [
            "Le loyer mensuel hors charges est fixe a neuf cent cinquante euros (950 EUR). "
            "Une provision sur charges de cent vingt euros (120 EUR) par mois sera versee par "
            "la locataire, portant le montant total mensuel a mille soixante-dix euros "
            "(1 070 EUR). La provision sur charges fera l'objet d'une regularisation annuelle "
            "sur justificatifs, selon les modalites prevues par la reglementation en vigueur.",
            "Le loyer et la provision sur charges sont payables d'avance, au plus tard le "
            "cinquieme jour de chaque mois, par virement bancaire sur le compte indique en "
            "annexe ou par tout autre moyen convenu entre les parties. Un recu sera delivre "
            "a la locataire sur simple demande. Les frais de virement sont a la charge de la "
            "locataire lorsque le bailleur n'impose pas un moyen de paiement gratuit.",
            "Tout retard de paiement pourra entrainer l'application d'une indemnite de retard "
            "dont le montant et les conditions seront conformes aux dispositions legales. "
            "Cette indemnite ne constitue pas une clause penale autonome et ne fait pas "
            "obstacle a la mise en oeuvre de la procedure de recouvrement prevue en cas "
            "d'impaye persistant. Les parties privilegieront une solution amiable.",
            "La revision annuelle du loyer interviendra a la date anniversaire du bail, dans "
            "les limites et selon les modalites prevues par les textes applicables. Toute "
            "revision devra etre notifiee par ecrit a la locataire avec l'indication de la "
            "variation de l'indice de reference utilise. A defaut de notification, le loyer "
            "reste inchange pour l'annee consideree.",
        ],
    ),
    (
        "Article 5 - Charges, taxes et accessoires",
        [
            "La provision sur charges couvre notamment les depenses d'eau froide, de chauffage "
            "collectif, d'electricite des parties communes, d'entretien des espaces verts, de "
            "menage des communs, d'ascenseur, d'assurance de l'immeuble et de gestion courante. "
            "Elle ne couvre pas la consommation personnelle d'electricite de la locataire ni "
            "son abonnement internet, qui restent a sa charge exclusive.",
            "La taxe d'enlevement des ordures menageres et la taxe de balayage seront dues par "
            "la locataire selon les modalites prevues par les textes applicables. La taxe "
            "d'habitation et la contribution audiovisuelle restent a la charge de l'occupant "
            "selon la reglementation en vigueur au moment de leur exigibilite.",
            "Les travaux d'amelioration ou de mise en conformite decides par l'assemblee des "
            "coproprietaires peuvent donner lieu a une contribution de la locataire dans les "
            "limites autorisees par la loi. Le bailleur informera la locataire par ecrit de "
            "toute somme mise a sa charge et precisera le fondement legal de cette contribution.",
        ],
    ),
    (
        "Article 6 - Depot de garantie",
        [
            "La locataire versera au bailleur un depot de garantie d'un montant de mille neuf "
            "cent euros (1 900 EUR), correspondant a deux mois de loyer hors charges. Ce depot "
            "sera verse le jour de la remise des cles et ne pourra en aucun cas etre impute sur "
            "le paiement du loyer ou des charges des derniers mois du bail.",
            "Le depot de garantie sera restitue dans un delai maximum de deux mois a compter de "
            "la restitution des cles, apres deduction des sommes eventuellement dues au titre "
            "des loyers impayes, des charges, des reparations locatives justifiees et des "
            "dommages constates lors de l'etat des lieux de sortie. Les justificatifs seront "
            "communiques a la locataire avec le decompte final.",
            "Si un solde reste du au bailleur apres deduction, la locataire s'engage a le "
            "regler dans un delai de trente jours a compter de la reception du decompte. Si le "
            "depot de garantie est superieur aux sommes dues, le solde sera restitue par "
            "virement sur le compte indique par la locataire.",
        ],
    ),
    (
        "Article 7 - Obligations du bailleur",
        [
            "Le bailleur s'engage a delivrer un logement decent, en bon etat d'usage et de "
            "reparation, conforme a la destination prevue au contrat. Il garantit a la locataire "
            "la jouissance paisible des lieux pendant toute la duree du bail et s'abstient de "
            "tout acte susceptible de troubler cette jouissance, sous reserve des droits des "
            "coproprietaires et des interventions urgentes necessaires.",
            "Le bailleur s'engage a assurer le logement contre les risques locatifs et a "
            "justifier de cette assurance sur demande. Il prend en charge les reparations "
            "autres que locatives, notamment celles relatives a la structure de l'immeuble, "
            "aux installations generales d'eau, de gaz et d'electricite, ainsi qu'aux elements "
            "d'equipement indispensables au respect des normes de salubrite.",
            "Le bailleur remet a la locataire les diagnostics obligatoires et les notices "
            "d'entretien des equipements. Il informe l'occupant de toute intervention susceptible "
            "d'affecter la jouissance des lieux, sauf urgence. Les travaux d'amelioration ne "
            "peuvent etre realises qu'apres information ecrite et dans le respect des regles "
            "protectrices du locataire en place.",
        ],
    ),
    (
        "Article 8 - Obligations de la locataire",
        [
            "La locataire s'engage a payer le loyer, les charges et les accessoires aux "
            "echeances convenues, a user paisiblement des lieux et a respecter le reglement de "
            "copropriete. Elle doit maintenir le logement en bon etat d'entretien courant, "
            "effectuer les menues reparations et signaler sans delai les desordres necessitant "
            "une intervention du bailleur ou d'un professionnel qualifie.",
            "La locataire ne peut transformer les lieux, changer la destination des pieces, "
            "installer une climatisation, percer les murs porteurs ou modifier les reseaux "
            "d'eau, de gaz et d'electricite sans l'accord ecrit prealable du bailleur. Les "
            "travaux autorises devront etre realises par un professionnel et ne pas compromettre "
            "la securite des occupants ni la conformite de l'immeuble.",
            "La locataire doit autoriser l'acces aux lieux pour les visites techniques, les "
            "reparations et les diagnostics obligatoires, dans le respect de la vie privee et "
            "des plages horaires raisonnables convenues avec le bailleur. En cas d'absence "
            "prolongee, elle informera le bailleur et prendra les mesures utiles pour prevenir "
            "les degats des eaux et les intrusions.",
            "La locataire repond des degradations causees aux parties communes par son fait, "
            "celui des personnes vivant avec elle ou de ses invites. Elle doit restituer le "
            "logement en fin de bail dans l'etat constate a l'entree, sous reserve de l'usure "
            "normale et des vetustes. Les objets et meubles laisses apres le depart pourront "
            "etre traites conformement aux regles applicables aux encombrants.",
        ],
    ),
    (
        "Article 9 - Assurance et responsabilite",
        [
            "La locataire s'engage a souscrire et a maintenir en vigueur une assurance "
            "responsabilite civile locative couvrant les risques d'incendie, de degats des eaux "
            "et de responsabilite envers les tiers. Une attestation d'assurance devra etre "
            "remise au bailleur lors de la remise des cles, puis renouvelee chaque annee sur "
            "demande ou a la date d'echeance du contrat.",
            "A defaut de justification d'assurance dans un delai de quinze jours apres relance, "
            "le bailleur pourra souscrire une assurance pour le compte de la locataire et lui "
            "refacturer la prime selon les modalites autorisees par la loi. Cette souscription "
            "ne dispense pas la locataire de son obligation d'information et de mise a jour "
            "des justificatifs.",
            "Chaque partie demeure responsable des dommages causes par son fait ou par les "
            "personnes dont elle repond. La presence d'animaux domestiques est toleree dans "
            "les conditions prevues au reglement de copropriete et sous reserve qu'ils ne "
            "causent aucune nuisance aux voisins ni degradation aux parties communes.",
        ],
    ),
    (
        "Article 10 - Entretien et reparations locatives",
        [
            "La locataire prend en charge l'entretien courant du logement et les reparations "
            "locatives listees par les textes applicables, notamment le remplacement des "
            "ampoules, l'entretien des joints et des siphons, le ramonage lorsque l'installation "
            "le necessite, le nettoyage des filtres et l'entretien des appareils menagers "
            "fournis. Les factures d'intervention pourront etre demandees par le bailleur.",
            "Le bailleur prend en charge les reparations autres que locatives, telles que le "
            "remplacement d'une chaudiere, d'un ballon d'eau chaude ou d'un element de "
            "menuiserie degrade par la vetuste. La qualification d'une reparation sera "
            "recherchee d'un commun accord et, en cas de desaccord persistant, selon la "
            "procedure amiable ou juridictionnelle applicable.",
            "La locataire informera le bailleur sans delai de toute fuite, infiltration, "
            "panne de chauffage ou de production d'eau chaude, panne electrique ou desordre "
            "susceptible d'affecter la securite ou la salubrite. A defaut d'information, elle "
            "pourrait etre tenue des consequences d'un dommage qui aurait pu etre evite par "
            "une intervention rapide.",
        ],
    ),
    (
        "Article 11 - Travaux et ameliorations",
        [
            "Les travaux d'amelioration du logement ou de l'immeuble peuvent etre realises par "
            "le bailleur pendant la duree du bail. Ils ne peuvent toutefois porter atteinte a "
            "la jouissance paisible des lieux ni entrainer une augmentation du loyer sans "
            "accord ecrit de la locataire, sauf dispositions legales contraires. Un planning "
            "previsionnel sera communique dans un delai raisonnable.",
            "La locataire s'abstient de realiser des travaux sans autorisation ecrite. Toute "
            "demande precisera la nature des travaux, leur duree, les entreprises concernees "
            "et les garanties d'assurance. Le bailleur pourra refuser pour un motif legitime, "
            "notamment la securite, la structure de l'immeuble ou l'opposition de la copropriete.",
            "En fin de bail, la locataire pourra retirer les installations qu'elle a realisees "
            "si cela ne cause aucun dommage aux lieux. A defaut, les installations resteront "
            "acquises au logement sans indemnite, sauf accord ecrit contraire. Les trous et "
            "attaches devront etre rebouches et repeints dans une teinte equivalente.",
        ],
    ),
    (
        "Article 12 - Etat des lieux",
        [
            "Un etat des lieux contradictoire sera etabli lors de la remise des cles, en "
            "presence des deux parties ou de leur representant. Il mentionnera l'etat des "
            "revêtements, murs, plafonds, menuiseries, equipements sanitaires, appareils "
            "menagers, compteurs et parties communes accessibles. Chaque partie conservera "
            "un exemplaire signe et date.",
            "L'etat des lieux de sortie sera realise dans les conditions prevues par les textes "
            "applicables, apres comparaison avec l'etat d'entree. Les degradations autres que "
            "l'usure normale seront chiffrees et imputees sur le depot de garantie sur "
            "justificatifs. La locataire pourra solliciter une evaluation contradictoire.",
            "Si l'etat des lieux de sortie ne peut etre etabli de maniere contradictoire, il "
            "sera procede par huissier ou par un professionnel mandataire, a la demande de la "
            "partie la plus diligente. Les frais seront supportes par la partie responsable du "
            "desaccord, sauf decision contraire du juge ou accord entre les parties.",
        ],
    ),
    (
        "Article 13 - Chauffage, energie et telecommunications",
        [
            "Le logement est raccorde au chauffage collectif de l'immeuble. Les periodes de "
            "chauffe sont determinees par la copropriete et peuvent varier selon les conditions "
            "climatiques. La locataire ne peut modifier les reglages collectifs ni installer "
            "un appareil de chauffage individuel sans l'accord ecrit du bailleur et de la "
            "copropriete.",
            "La locataire souscrit a son nom les contrats d'electricite, de gaz et de "
            "telecommunications necessaires a son usage. Elle s'acquitte directement des "
            "factures aupres des fournisseurs. En cas de coupure imputable a un impaye, elle "
            "ne peut se prevaloir d'un trouble de jouissance a l'encontre du bailleur.",
            "Les compteurs individuels seront releves a l'entree et a la sortie. Les consommations "
            "relevees entre ces deux dates sont a la charge de la locataire. Les consommations "
            "communes sont reparties selon les tantièmes ou les cles de repartition prevues "
            "par le reglement de copropriete et annexees au contrat.",
        ],
    ),
    (
        "Article 14 - Resiliation et conge",
        [
            "La locataire peut donner conge a tout moment, sous reserve de respecter le "
            "preavis applicable et les formes prevues par les textes en vigueur. Le conge doit "
            "etre notifie par lettre recommandee avec avis de reception, remise en main propre "
            "contre recu ou par un acte extrajudiciaire. Le delai commence a courir a la date "
            "de reception de la notification.",
            "Le bailleur peut donner conge au terme du bail pour reprendre le logement, le "
            "vendre ou le louer a un tiers, dans les conditions et delais legaux. Le conge doit "
            "etre motive et notifie selon les formes requises. En cas de vente, la locataire "
            "dispose d'un droit de preference dans les conditions prevues par la loi.",
            "En cas de conge delivre par la locataire, celle-ci reste redevable du loyer et "
            "des charges jusqu'a la date d'effet du conge, sauf accord de resiliation anticipee. "
            "Les parties organiseront l'etat des lieux de sortie et la restitution des cles a "
            "une date compatible avec leurs obligations respectives.",
        ],
    ),
    (
        "Article 15 - Clause resolutoire",
        [
            "Le present bail pourra etre resilié de plein droit en cas de manquement grave et "
            "reitere de la locataire a ses obligations, notamment le défaut de paiement du "
            "loyer ou des charges, le trouble de jouissance, la sous-location non autorisee ou "
            "la degradation des lieux. La resolution ne pourra intervenir qu'apres mise en "
            "demeure restee sans effet et dans le respect de la procedure applicable.",
            "La clause resolutoire ne fait pas obstacle a la recherche d'une solution amiable. "
            "Le bailleur informera la locataire des sommes dues et des delais de regularisation. "
            "En cas de contestation, les parties pourront recourir a la commission departementale "
            "de conciliation ou a tout autre mode de resolution amiable prevu par la loi.",
            "La resolution du bail entraine l'obligation pour la locataire de restituer les "
            "lieux et de payer les sommes dues jusqu'a la date de depart effectif. Les meubles "
            "et objets laisses sur place pourront etre traites conformement aux regles "
            "applicables, apres information de la locataire lorsque cela est possible.",
        ],
    ),
    (
        "Article 16 - Sous-location, cession et occupation",
        [
            "La sous-location totale ou partielle des lieux est interdite sans l'accord ecrit "
            "prealable du bailleur. Toute demande precisera l'identite du sous-locataire, la "
            "duree envisagee et la destination des lieux. Le bailleur pourra refuser pour un "
            "motif legitime et devra repondre dans un delai raisonnable.",
            "La location meublee de courte duree, l'hebergement payant et toute activite "
            "d'intermediation locative sont egalement interdits sans accord ecrit. La "
            "locataire demeure responsable du comportement des occupants et des invites et "
            "repond des nuisances causees aux autres occupants de l'immeuble.",
            "En cas de changement de situation familiale, la locataire informera le bailleur "
            "dans les meilleurs delais. Les personnes vivant habituellement dans le logement "
            "devront etre declarees conformement aux obligations d'information prevues par les "
            "textes applicables, sans que cela modifie les conditions financieres du bail.",
        ],
    ),
    (
        "Article 17 - Nuisances, animaux et vie collective",
        [
            "La locataire s'engage a ne pas causer de nuisances sonores, olfactives ou "
            "visuelles aux autres occupants de l'immeuble. Les travaux de bricolage, les "
            "receptions et l'usage d'appareils sonores devront respecter les horaires de "
            "calme fixés par le reglement de copropriete et les regles de voisinage.",
            "Les animaux domestiques sont autorises dans les conditions prevues par le "
            "reglement de copropriete et sous reserve qu'ils ne presentent aucun danger pour "
            "les autres occupants. La locataire assume l'entiere responsabilite des dommages "
            "causes par ses animaux dans le logement et les parties communes.",
            "Les parties communes, les escaliers, l'ascenseur et les espaces exterieurs "
            "doivent etre utilisés conformement a leur destination. Le stationnement dans les "
            "emplacements non autorises, le depot d'encombrants et l'entreposage de materiels "
            "dans les communs sont interdits et pourront entrainer la facturation des frais de "
            "remise en etat.",
        ],
    ),
    (
        "Article 18 - Visites, diagnostics et information",
        [
            "Le bailleur ou son mandataire pourra organiser des visites du logement en vue "
            "d'une vente ou d'une relocation, apres information de la locataire et dans le "
            "respect de plages horaires raisonnables. Les visites ne pourront avoir lieu plus "
            "de deux heures par jour ouvrable, sauf accord de la locataire pour une amplitude "
            "plus large.",
            "La locataire autorisera l'acces aux techniciens pour les diagnostics obligatoires, "
            "les controles de securite, l'entretien des appareils et les travaux urgents. En "
            "cas d'absence, elle pourra deleguer une personne de confiance ou convenir d'un "
            "moyen d'acces securise avec le bailleur.",
            "Les informations relatives a la performance energetique, aux risques naturels et "
            "technologiques, au bruit et a la presence de termites sont annexees au contrat "
            "lorsqu'elles sont exigibles. La locataire reconnait en avoir recu un exemplaire "
            "et avoir pu en prendre connaissance avant la signature.",
        ],
    ),
    (
        "Article 19 - Litiges et droit applicable",
        [
            "Le present contrat est soumis au droit francais et aux dispositions applicables "
            "aux baux d'habitation. Les parties rechercheront en priorite une solution amiable "
            "a tout differend relatif a l'execution ou a l'interpretation du bail. A defaut "
            "d'accord, le litige pourra etre porte devant la juridiction competente.",
            "Les notifications entre les parties seront valablement effectuees par lettre "
            "recommandee avec avis de reception, par remise en main propre contre recu ou par "
            "voie electronique lorsque les parties en sont convenues. Les coordonnees figurent "
            "en tete du present contrat et pourront etre mises a jour par ecrit.",
            "Si une clause du present contrat etait declaree nulle ou inapplicable, les autres "
            "stipulations conserveraient leur plein effet. Les parties se rapprocheront pour "
            "convenir d'une clause de remplacement conforme a l'equilibre du contrat et aux "
            "dispositions legales applicables.",
        ],
    ),
    (
        "Article 20 - Annexes et signatures",
        [
            "Sont annexes au present contrat : l'etat des lieux d'entree, l'inventaire du "
            "mobilier, les diagnostics obligatoires, les notices d'entretien, l'attestation "
            "d'assurance de la locataire, le reglement de copropriete et le decompte des "
            "charges de la derniere annee. Ces documents font partie integrante du bail.",
            "Le present contrat est etabli en deux exemplaires originaux, un pour chaque partie. "
            "Il ne peut etre modifie que par avenant ecrit signe par les deux parties. Les "
            "parties declarent avoir lu et compris l'ensemble des stipulations et en accepter "
            "les termes sans reserve.",
            "Fait a Paris, le 15 aout 2026. Le bailleur : Monsieur et Madame Dupont. La "
            "locataire : Madame Lea Martin. Signatures precedees de la mention lu et approuve. "
            "Chaque partie reconnait avoir recu un exemplaire original du present contrat "
            "accompagne de ses annexes.",
        ],
    ),
    (
        "Article 21 - Garantie et solidarite",
        [
            "La locataire pourra etre tenue de fournir la caution d'une personne physique ou "
            "morale se portant garante solidaire du paiement du loyer et des charges. L'acte "
            "de cautionnement devra etre etabli par ecrit et mentionner expressement la duree "
            "de l'engagement, son caractere solidaire et les obligations garanties.",
            "Le garant s'engage a payer au bailleur les sommes dues par la locataire en cas de "
            "defaut de paiement, apres mise en demeure adressee a la locataire restee sans "
            "effet. Le garant pourra demander une copie des quittances et des decomptes de "
            "charges afin de verifier le montant des sommes reclamees.",
            "La garantie ne pourra etre mise en oeuvre au-dela des limites prevues par l'acte "
            "de cautionnement et par les textes applicables. Toute renonciation du bailleur a "
            "poursuivre la locataire ne pourra etre opposee au garant que dans les conditions "
            "prevues par la loi et par l'acte de cautionnement.",
        ],
    ),
    (
        "Article 22 - Vente du logement et droit de preference",
        [
            "En cas de vente du logement pendant la duree du bail, la locataire beneficie du "
            "droit de preference prevu par les textes applicables. Le bailleur notifiera son "
            "intention de vendre par lettre recommandee avec avis de reception, en precisant "
            "le prix, les conditions de la vente et les modalites d'exercice du droit de "
            "preference.",
            "La locataire disposera du delai legal pour faire connaitre sa decision. En cas "
            "d'exercice du droit de preference, la vente sera conclue aux conditions notifiees, "
            "sous reserve de l'obtention du financement et de la signature de l'acte authentique "
            "dans les delais convenus. A defaut, le bailleur pourra poursuivre la vente.",
            "La vente du logement ne met pas fin au bail en cours. L'acquereur devient le "
            "nouveau bailleur et reprend l'ensemble des droits et obligations du bailleur "
            "precedent. La locataire continuera d'occuper les lieux et de payer le loyer selon "
            "les modalites convenues, jusqu'a la date d'effet d'un eventuel conge.",
        ],
    ),
    (
        "Article 23 - Renovation energetique et travaux de copropriete",
        [
            "Le bailleur informera la locataire des travaux de renovation energetique ou de "
            "mise en conformite decides par la copropriete, dans un delai raisonnable avant "
            "leur demarrage. Un calendrier previsionnel sera communique, ainsi que la duree "
            "estimee des nuisances et les mesures de compensation eventuelles.",
            "Les travaux de renovation energetique ne peuvent avoir pour effet de rendre le "
            "logement impropre a sa destination. Si les travaux rendent temporairement le "
            "logement inhabitable, les parties conviendront d'une reduction de loyer ou d'un "
            "relogement temporaire, dans les conditions prevues par les textes applicables.",
            "La locataire facilitera l'acces aux entreprises mandatees, dans le respect de sa "
            "vie privee et des plages horaires convenues. Elle ne pourra s'opposer aux travaux "
            "necessaires a la securite ou a la mise en conformite de l'immeuble, sous reserve "
            "de l'information prealable et de la protection de ses biens.",
        ],
    ),
    (
        "Article 24 - Securite, acces et gestion des cles",
        [
            "La locataire veillera a la fermeture des portes et des acces de l'immeuble et ne "
            "communiquera pas les codes d'acces a des personnes exterieures. En cas de perte "
            "ou de vol des cles, elle informera immediatement le bailleur et prendra en charge "
            "le remplacement des serrures lorsque cela est necessaire a la securite.",
            "Le bailleur peut installer des dispositifs de securite dans les parties communes, "
            "notamment des cameras dans les conditions prevues par la reglementation et apres "
            "information des occupants. Les dispositifs ne peuvent filmer l'interieur du "
            "logement ni porter atteinte a la vie privee de la locataire.",
            "La locataire s'abstient de modifier les serrures, d'ajouter des verrous non "
            "conformes ou de bloquer les issues de secours. Les installations de securite "
            "existantes doivent rester operationnelles. Toute intervention sur les serrures "
            "devra etre realisee par un professionnel qualifie.",
        ],
    ),
    (
        "Article 25 - Receptions, activites et responsabilite civile",
        [
            "La locataire peut organiser des receptions dans le respect du reglement de "
            "copropriete, des horaires de calme et de la tranquillite des voisins. Elle demeure "
            "responsable des dommages causes par ses invites dans le logement, les parties "
            "communes et les espaces exterieurs de l'immeuble.",
            "L'exercice d'une activite professionnelle dans le logement est soumis a l'accord "
            "ecrit prealable du bailleur et au respect des regles de la copropriete. L'activite "
            "ne doit generer aucune nuisance, aucun passage de clientele ni aucune modification "
            "de la destination de l'immeuble.",
            "La locataire s'engage a souscrire une garantie responsabilite civile couvrant les "
            "dommages causes aux tiers et aux parties communes. Sur demande du bailleur, elle "
            "fournira une attestation a jour. Le defaut d'assurance pourra entrainer la mise en "
            "oeuvre des mesures prevues a l'article 9 du present contrat.",
        ],
    ),
    (
        "Article 26 - Donnees personnelles et correspondance",
        [
            "Les donnees personnelles communiquees pour la gestion du bail sont traitees dans "
            "le respect de la reglementation applicable. Elles sont conservees pendant la duree "
            "du bail et les delais legaux de conservation, puis supprimees ou anonymisees. "
            "Chaque partie peut exercer ses droits d'acces, de rectification et d'opposition.",
            "Les correspondances relatives au bail seront adressees aux coordonnees indiquees "
            "en tete du contrat. La locataire peut demander que les convocations pour les "
            "visites techniques soient adressees par courrier electronique, a condition que "
            "cette modalite soit convenue par ecrit entre les parties.",
            "Le bailleur s'abstient de communiquer les informations personnelles de la "
            "locataire a des tiers non impliques dans la gestion du bail, sauf obligation "
            "legale ou accord prealable de la locataire. Les prestataires intervenant dans "
            "l'immeuble sont tenus a une obligation de confidentialite.",
        ],
    ),
    (
        "Article 27 - Regularisation des charges et justification des sommes",
        [
            "La regularisation annuelle des charges sera accompagnée d'un decompte detaille "
            "indiquant les depenses engagees, les cles de repartition et les sommes deja "
            "versees par la locataire. Les justificatifs correspondants seront tenus a sa "
            "disposition pendant un delai raisonnable et pourront etre consultes sur demande.",
            "Si la regularisation fait apparaitre un solde en faveur du bailleur, la locataire "
            "s'engage a le regler dans le delai indique sur le decompte. Si le solde est en sa "
            "faveur, il sera deduit de la prochaine provision ou rembourse dans les meilleurs "
            "delais, selon les modalites convenues entre les parties.",
            "La locataire peut contester le decompte dans un delai de deux mois a compter de "
            "sa reception, en adressant une demande ecrite motivee au bailleur. Les parties "
            "rechercheront une solution amiable et, a defaut, pourront saisir la commission "
            "departementale de conciliation competente.",
        ],
    ),
    (
        "Article 28 - Dispositions finales et entree en vigueur",
        [
            "Le present contrat entre en vigueur a la date de sa signature par les deux "
            "parties et produit ses effets jusqu'a la fin du bail ou jusqu'a la survenance "
            "d'un evenement prevu par la loi ou par les stipulations contractuelles. Les "
            "annexes ont la meme valeur juridique que le corps du contrat.",
            "Toute modification du contrat doit faire l'objet d'un avenant ecrit signe par les "
            "deux parties. Les echanges par courrier electronique ne vaudront modification du "
            "bail que si les parties en sont expressément convenues et si l'avenant est signe "
            "selon les formes requises.",
            "Les parties declarent que le present contrat constitue l'integralite de leur "
            "accord relatif a la location du logement et remplace toute convention anterieure, "
            "orale ou ecrite, ayant le meme objet. Elles reconnaissent avoir beneficie d'un "
            "delai suffisant pour en prendre connaissance et poser toutes questions utiles.",
        ],
    ),
]


FILLER: list[str] = [
    "Clause complementaire 1 - Les parties conviennent que toute tolerance ou abstention "
    "dans l'exercice d'un droit prevu au present contrat ne vaut pas renonciation a ce droit. "
    "Une renonciation ne peut resulter que d'un ecrit signe par la partie qui y renonce et "
    "doit etre limitee a la situation expressement visee.",
    "Clause complementaire 2 - La locataire s'engage a respecter les consignes de tri des "
    "dechets, les horaires de sortie des containers et les regles de stationnement des "
    "vehicules dans l'enceinte de l'immeuble. Tout manquement pourra etre signale au "
    "syndic et, le cas echeant, donner lieu a facturation des frais de nettoyage.",
    "Clause complementaire 3 - Le bailleur informera la locataire de tout changement de "
    "mandataire ou de gestionnaire. Les coordonnees du nouveau gestionnaire seront "
    "communiquees par ecrit et le paiement du loyer continuera d'etre effectue selon les "
    "modalites convenues jusqu'a notification contraire.",
    "Clause complementaire 4 - La locataire autorise le bailleur a communiquer ses "
    "coordonnees aux entreprises mandatées pour les interventions techniques, dans la "
    "limite strictement necessaire a l'execution des travaux et dans le respect de la "
    "confidentialite des donnees personnelles.",
    "Clause complementaire 5 - En cas de degat des eaux, la locataire prendra immediatement "
    "les mesures de prevention utiles, coupera l'arrivee d'eau si elle est accessible et "
    "informera le bailleur ainsi que le syndic dans les meilleurs delais, sans attendre "
    "l'intervention d'un professionnel.",
    "Clause complementaire 6 - Les parties s'engagent a conserver une copie de l'etat des "
    "lieux et des diagnostics pendant toute la duree du bail et jusqu'a la restitution du "
    "depot de garantie. Ces documents pourront etre utilises pour justifier l'etat du "
    "logement a l'entree et a la sortie.",
    "Clause complementaire 7 - La locataire ne peut installer d'antenne, de parabole ou de "
    "panneau solaire sur les parties communes ou en facade sans autorisation ecrite du "
    "bailleur et de la copropriete. Les installations autorisees devront respecter les "
    "regles d'urbanisme et de securite.",
    "Clause complementaire 8 - Le bailleur pourra demander la communication des justificatifs "
    "d'assurance et des attestations d'entretien des appareils. La locataire s'engage a "
    "fournir ces documents dans un delai de quinze jours a compter de la demande ecrite.",
    "Clause complementaire 9 - En cas d'absence prolongee, la locataire informera le "
    "bailleur, fermera les arrivées d'eau et de gaz, maintiendra un chauffage minimal pour "
    "eviter le gel des canalisations et veillera a la securite des acces au logement.",
    "Clause complementaire 10 - La locataire s'engage a ne pas entreposer de matieres "
    "inflammables, explosives ou dangereuses dans le logement, la cave ou les parties "
    "communes. Les installations electriques ne doivent pas etre surchargees par des "
    "appareils inadaptes.",
    "Clause complementaire 11 - Les parties reconnaissent que les performances energetiques "
    "du logement peuvent varier selon l'usage, l'occupation et les conditions climatiques. "
    "Les diagnostics remis a la locataire constituent une information et non une garantie "
    "de consommation.",
    "Clause complementaire 12 - En cas de travaux urgents, le bailleur ou son representant "
    "pourra acceder au logement sans accord prealable, sous reserve d'informer la locataire "
    "dans les meilleurs delais et de limiter l'intervention au strict necessaire.",
    "Clause complementaire 13 - La locataire s'engage a maintenir une temperature minimale "
    "suffisante pour prevenir les degats causes par le gel et l'humidite. En cas d'absence "
    "durant la periode hivernale, elle prendra les mesures utiles pour proteger les "
    "installations sanitaires.",
    "Clause complementaire 14 - Le bailleur peut demander une copie des quittances de loyer "
    "pour tout dossier administratif, dans le respect de la vie privee de la locataire. "
    "Les informations transmises ne pourront etre utilisees a d'autres fins.",
    "Clause complementaire 15 - Les parties conviennent de privilegier les echanges ecrits "
    "pour toute demande relative au bail. Les demandes urgentes liees a la securite pourront "
    "etre transmises par telephone et confirmees par ecrit dans les meilleurs delais.",
    "Clause complementaire 16 - La locataire s'engage a respecter les regles relatives aux "
    "travaux de bricolage et aux nuisances sonores. Les travaux generant une gene importante "
    "devront etre realises en semaine, aux horaires autorises et apres information des "
    "voisins lorsque cela est nécessaire.",
]


def _split_sentences(text: str, max_chars: int) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if len(current) + len(sentence) + 1 <= max_chars:
            current = f"{current} {sentence}".strip()
        else:
            if current:
                chunks.append(current)
            current = sentence
    if current:
        chunks.append(current)
    return chunks


class ContractPDF(FPDF):
    def __init__(self, target_pages: int) -> None:
        super().__init__(orientation="P", unit="mm", format="A4")
        self.target_pages = target_pages

    def footer(self) -> None:
        self.set_y(-14)
        self.set_font("Arial", "", 8)
        self.cell(0, 6, f"Page {self.page_no()} / {self.target_pages}", align="C")


def _setup(pdf: ContractPDF) -> None:
    pdf.add_font("Arial", "", str(FONT_REGULAR))
    pdf.add_font("Arial", "B", str(FONT_BOLD))
    pdf.set_margins(MARGIN_X, MARGIN_TOP, MARGIN_X)
    pdf.set_auto_page_break(auto=False)


def _new_page(pdf: ContractPDF) -> None:
    pdf.add_page()
    pdf.set_font("Arial", "B", 11)
    pdf.cell(
        0,
        6,
        CONTRACT_TITLE,
        new_x="LMARGIN",
        new_y="NEXT",
        align="C",
    )
    pdf.set_font("Arial", "", 8.5)
    pdf.cell(
        0,
        4,
        CONTRACT_SUBTITLE,
        new_x="LMARGIN",
        new_y="NEXT",
        align="C",
    )
    pdf.ln(3)


def _write_block(pdf: ContractPDF, text: str, target_pages: int, bold: bool = False) -> bool:
    pdf.set_font("Arial", "B" if bold else "", BODY_SIZE)
    height = pdf.multi_cell(0, LINE_H, text, dry_run=True, output=MethodReturnValue.HEIGHT)
    limit = pdf.h - MARGIN_BOTTOM

    if pdf.get_y() + height > limit:
        if pdf.page_no() >= target_pages:
            return False
        _new_page(pdf)
        if pdf.get_y() + height > limit:
            available_chars = max(200, int((limit - pdf.get_y()) / LINE_H) * 90)
            for chunk in _split_sentences(text, available_chars):
                if not _write_block(pdf, chunk, target_pages, bold=bold):
                    return False
            return True

    pdf.multi_cell(0, LINE_H, text)
    pdf.ln(1.8)
    return True


def render(path: Path, target_pages: int) -> None:
    pdf = ContractPDF(target_pages)
    _setup(pdf)
    _new_page(pdf)

    stopped = False
    for title, paragraphs in ARTICLES:
        if stopped or not _write_block(pdf, title, target_pages, bold=True):
            stopped = True
            break
        for paragraph in paragraphs:
            if not _write_block(pdf, paragraph, target_pages):
                stopped = True
                break

    filler_index = 0
    while pdf.page_no() < target_pages:
        _new_page(pdf)
        while filler_index < len(FILLER):
            if not _write_block(pdf, FILLER[filler_index], target_pages):
                break
            filler_index += 1
        if filler_index >= len(FILLER):
            FILLER.append(
                "Clause complementaire additionnelle - Les parties rappellent que le present "
                "contrat doit etre execute de bonne foi et que chacune d'elles s'engage a "
                "informer l'autre de toute difficulte susceptible d'affecter son execution."
            )

    pdf.output(str(path))


def main() -> None:
    parser = argparse.ArgumentParser(description="Genere le corpus de benchmark.")
    parser.add_argument("--out-dir", type=Path, default=Path("corpus/bench"))
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    for pages in (6, 10):
        path = args.out_dir / f"bail_{pages}p.pdf"
        render(path, pages)
        size = path.stat().st_size
        print(f"{path} ({pages} pages, {size} octets)")

    try:
        import fitz
    except ImportError:
        print("PyMuPDF absent : verification du texte ignoree.")
        return

    for pages in (6, 10):
        path = args.out_dir / f"bail_{pages}p.pdf"
        document = fitz.open(path)
        text = "\n".join(page.get_text("text") for page in document)
        print(
            f"verification {path.name}: {document.page_count} pages, "
            f"{len(text)} caracteres, ~{round(len(text) / 4)} tokens (approx.)"
        )


if __name__ == "__main__":
    main()
