"""Generate a PDF onboarding guide explaining the HR (GRH) business notions behind the Superset dashboards.

Usage: python export_guide.py [--out exports/Guide_metier_GRH.pdf]
Requires: pip install reportlab
"""
from __future__ import annotations

import argparse
import importlib
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    KeepTogether, ListFlowable, ListItem, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from grh_builder import HERE, SUITE

DEFAULT_OUT = HERE / "exports" / "Guide_metier_GRH.pdf"

BLUE = colors.HexColor("#1E3A8A")
LIGHT = colors.HexColor("#EEF2FF")
NOTE_BG = colors.HexColor("#FFF7E6")
GREY = colors.HexColor("#555555")

FONT_CANDIDATES = [("calibri.ttf", "calibrib.ttf", "calibrii.ttf"), ("arial.ttf", "arialbd.ttf", "ariali.ttf")]


def register_fonts() -> str:
    fonts_dir = Path("C:/Windows/Fonts")
    for regular, bold, italic in FONT_CANDIDATES:
        if (fonts_dir / regular).exists() and (fonts_dir / bold).exists():
            pdfmetrics.registerFont(TTFont("Body", str(fonts_dir / regular)))
            pdfmetrics.registerFont(TTFont("Body-Bold", str(fonts_dir / bold)))
            pdfmetrics.registerFont(TTFont("Body-Italic", str(fonts_dir / italic)))
            pdfmetrics.registerFontFamily("Body", normal="Body", bold="Body-Bold", italic="Body-Italic",
                                          boldItalic="Body-Bold")
            return "Body"
    return "Helvetica"


FONT = register_fonts()
STYLES = {
    "title": ParagraphStyle("title", fontName=FONT, fontSize=26, leading=32, textColor=BLUE, alignment=TA_CENTER,
                            spaceAfter=12),
    "subtitle": ParagraphStyle("subtitle", fontName=FONT, fontSize=13, leading=18, textColor=GREY,
                               alignment=TA_CENTER, spaceAfter=6),
    "h1": ParagraphStyle("h1", fontName=FONT, fontSize=17, leading=22, textColor=BLUE, spaceBefore=6, spaceAfter=8),
    "h2": ParagraphStyle("h2", fontName=FONT, fontSize=12.5, leading=16, textColor=BLUE, spaceBefore=10,
                         spaceAfter=4),
    "body": ParagraphStyle("body", fontName=FONT, fontSize=10, leading=14, spaceAfter=6),
    "cell": ParagraphStyle("cell", fontName=FONT, fontSize=8.8, leading=11.5),
    "head": ParagraphStyle("head", fontName=FONT, fontSize=9, leading=11.5, textColor=colors.white),
    "toc": ParagraphStyle("toc", fontName=FONT, fontSize=11, leading=17),
}


# --------------------------------------------------------------------------- content
# Each section is a list of blocks: ("p", text) | ("h2", text) | ("ul", [items]) | ("note", text)
# | ("table", headers, rows, widths_cm). Texts use ReportLab mini-markup (<b>, <i>).

INTRO = [
    ("p", "Ce guide s'adresse aux nouveaux membres de l'équipe. Il explique les <b>notions de base de la gestion "
          "des ressources humaines (GRH)</b> telles qu'elles apparaissent dans les tableaux de bord Superset : "
          "le vocabulaire, d'où viennent les chiffres et comment les lire."),
    ("p", "Les données proviennent du logiciel de gestion RH (base Oracle <b>ENDADB</b>). Superset ne modifie "
          "rien : il lit ces données, les regroupe et les affiche sous forme d'indicateurs et de graphiques."),
    ("p", "La GRH couvre tout le parcours d'un agent dans l'entreprise. On peut la résumer en six grands domaines, "
          "qui structurent la suite de ce document :"),
    ("table", ["Domaine", "Question métier", "Tableaux de bord"], [
        ["Le personnel", "Qui sont nos agents et où travaillent-ils ?", "Tableau de bord RH, Effectif"],
        ["Le parcours", "Comment entrent-ils, évoluent-ils et partent-ils ?",
         "Recrutement, Mobilité et carrière, Évaluation et rendement, Formation, Départs et retraites"],
        ["La paie", "Combien coûtent-ils et combien sont-ils payés ?",
         "Salaires et masse salariale, Budget et réalisé"],
        ["Le temps de travail", "Sont-ils présents ? Pourquoi sont-ils absents ?",
         "Congés et absences, Maladie et accidents, Présence et ponctualité"],
        ["Le social", "Quels avantages et aides leur sont accordés ?",
         "Couverture médicale, Œuvres sociales, Prêts et avances, Endettement"],
        ["Les services RH", "Quels services le département RH rend-il ?", "Services RH"],
    ], [3.2, 6.3, 7.5]),
]

PERSONNEL = [
    ("p", "Tout part de la fiche de l'agent (table <b>PERSONNEL</b>). Chaque agent est identifié par son "
          "<b>matricule</b> (MAT_PERS), unique et stable pendant toute sa carrière. Les tableaux de bord comptent "
          "les agents en « matricules distincts » pour ne jamais compter deux fois la même personne."),
    ("h2", "L'organisation : pôle, direction, service"),
    ("p", "L'entreprise est découpée en une arborescence de services. Un agent est affecté à un <b>service</b> ; "
          "ce service appartient à une <b>direction</b>, elle-même rattachée à un <b>pôle</b>. Les filtres "
          "« Pôle » et « Direction » présents sur presque tous les tableaux s'appuient sur cette arborescence."),
    ("h2", "Le statut de l'agent : catégorie, grade, fonction"),
    ("ul", [
        "<b>Catégorie</b> : grande famille de personnel (par exemple cadres, maîtrise, exécution). Elle sert à "
        "comparer des populations comparables.",
        "<b>Grade</b> : niveau de l'agent à l'intérieur de sa catégorie. Le grade détermine en grande partie le "
        "salaire. Passer au grade supérieur s'appelle une <b>promotion</b>.",
        "<b>Fonction</b> : responsabilité exercée (chef de service, chef d'agence, directeur…). Un agent sans "
        "fonction est « Sans fonction ». Un agent avec une fonction est compté comme <b>responsable</b>.",
    ]),
    ("note", "Grade et fonction sont deux choses différentes : un agent peut avoir un grade élevé sans exercer "
             "de fonction d'encadrement, et inversement."),
    ("h2", "La situation administrative"),
    ("ul", [
        "<b>État</b> : Actif, En position spéciale, Sorti ou Autre. Les indicateurs d'effectif ne retiennent que "
        "les <b>agents actifs</b> (état « 0 » dans la base).",
        "<b>Position administrative</b> : précise la situation (détachement, disponibilité, etc.).",
        "<b>Nature de recrutement</b> : la façon dont l'agent a été recruté (concours, contrat…).",
        "<b>Âge</b> et <b>ancienneté</b> : calculés à la date du jour à partir de la date de naissance et de la "
        "date d'embauche, puis regroupés en tranches (moins de 30 ans, 30-39 ans…, moins de 5 ans, 5-9 ans…).",
    ]),
    ("h2", "Les indicateurs de base sur l'effectif"),
    ("table", ["Indicateur", "Définition", "Comment le lire"], [
        ["Effectif actif", "Nombre d'agents en activité à la date du jour (fiche PERSONNEL).",
         "Photographie du personnel aujourd'hui."],
        ["Effectif payé", "Nombre d'agents ayant reçu une paie mensuelle dans le mois.",
         "Peut différer de l'effectif actif (agents non payés, régularisations)."],
        ["Taux de féminisation", "Part des femmes dans l'effectif actif.", "Suivi de la mixité."],
        ["Pyramide des âges", "Effectif par tranche d'âge et par sexe.",
         "Une base étroite et un sommet large annoncent de nombreux départs à la retraite."],
        ["Taux d'encadrement", "Responsables / effectif payé.",
         "Mesure le poids de l'encadrement dans chaque direction."],
    ], [3.4, 6.6, 7.0]),
]

PARCOURS = [
    ("p", "La vie d'un agent suit un cycle : il est <b>recruté</b>, il <b>évolue</b> (évaluation, formation, "
          "promotion, mutation) puis il <b>part</b> (retraite, démission, fin de contrat…)."),
    ("h2", "Recrutement"),
    ("ul", [
        "Un candidat dépose une <b>candidature</b> (fiche candidat), souvent dans le cadre d'un <b>concours</b>.",
        "Le <b>taux de recrutement</b> = candidats recrutés / candidatures. Un taux faible indique un concours "
        "très sélectif.",
        "Un recrutement correspond à une <b>date d'embauche</b> dans la fiche de l'agent.",
    ]),
    ("h2", "Évaluation et rendement"),
    ("p", "Chaque année, une <b>campagne d'évaluation</b> attribue à chaque agent une <b>note de rendement</b> "
          "sur 20. Elle comprend des sous-critères, dont l'<b>assiduité</b> et les <b>congés de maladie</b> "
          "(notés sur 4). Le tableau de bord suit la note moyenne, sa distribution par tranche (19-20, 17-18,99…) "
          "et le <b>taux de promotion l'année suivante</b>, pour vérifier que les bonnes notes mènent bien à "
          "une promotion."),
    ("h2", "Formation"),
    ("ul", [
        "Une <b>action de formation</b> est une session (intitulé, domaine, dates, lieu, coût).",
        "Une <b>participation</b> est l'inscription d'un agent à une action. Un agent peut participer à "
        "plusieurs actions : « agents formés » compte les personnes, « participations » compte les inscriptions.",
        "Les <b>heures stagiaires</b> = heures de formation × nombre de participants.",
    ]),
    ("h2", "Mobilité et carrière"),
    ("ul", [
        "<b>Mutation</b> : changement de service d'un agent, décidé par une décision numérotée. Une mutation "
        "<b>inter-directions</b> fait changer l'agent de direction.",
        "<b>Demande de mutation</b> : souhait exprimé par l'agent, qui peut être en attente, acceptée ou refusée.",
        "<b>Promotion de grade</b> : passage à un grade supérieur, enregistré avec une date de grade.",
    ]),
    ("h2", "Départs et retraites"),
    ("ul", [
        "Un <b>départ</b> est une sortie définitive, avec un <b>motif</b> (retraite, démission, décès, fin de "
        "contrat…).",
        "Le <b>taux de départ</b> = départs des 12 derniers mois / effectif actif.",
        "La <b>date de retraite prévue</b> vient du dossier de retraite s'il existe, sinon elle est calculée à "
        "partir de la date de naissance et de l'âge maximal paramétré pour la société (60 ans par défaut). "
        "Cette projection permet d'anticiper les remplacements et la transmission des compétences.",
    ]),
    ("h2", "Entrées, sorties, turnover et rétention"),
    ("table", ["Indicateur", "Définition", "Comment le lire"], [
        ["Entrée", "Agent payé ce mois-ci mais pas le mois précédent.", "Arrivées (recrutements, retours)."],
        ["Sortie", "Agent payé ce mois-ci mais pas le mois suivant.", "Départs effectifs."],
        ["Turnover", "(entrées + sorties) / 2 / effectif moyen sur 12 mois.",
         "Mesure le renouvellement du personnel. Un turnover élevé peut signaler un problème d'attractivité."],
        ["Rétention", "Part des agents payés il y a 12 mois qui sont encore payés aujourd'hui.",
         "Proche de 100 % : le personnel est stable."],
    ], [3.0, 7.0, 7.0]),
]

PAIE = [
    ("p", "Chaque mois, chaque agent reçoit un <b>bulletin de paie</b>. Un bulletin est composé de "
          "<b>rubriques</b> : chaque rubrique est une ligne (salaire de base, prime, cotisation, impôt…) "
          "identifiée par un code."),
    ("h2", "Les types de bulletins"),
    ("p", "Le bulletin mensuel ordinaire a le code <b>BN</b>. D'autres bulletins existent pour les versements "
          "ponctuels. Les tableaux de bord les regroupent en familles :"),
    ("table", ["Famille de rémunération", "Contenu"], [
        ["Paie mensuelle", "Bulletin mensuel BN : salaire et indemnités du mois."],
        ["Primes de performance", "Primes de bilan, de rendement et assimilées."],
        ["Primes sociales et fêtes", "Primes versées à l'occasion des fêtes, de la rentrée, etc."],
        ["Avantages", "Tickets restaurant, retraite complémentaire."],
        ["Départs", "Sommes versées au départ de l'agent (indemnités de départ, solde de tout compte)."],
        ["Rappels et divers", "Régularisations et rappels de salaire."],
    ], [5.0, 12.0]),
    ("h2", "Du salaire de base au coût employeur"),
    ("p", "Il faut bien distinguer ce que l'agent touche de ce que l'entreprise paie :"),
    ("table", ["Notion", "Définition"], [
        ["Salaire de base", "Montant fixe lié au grade et à l'échelon de l'agent."],
        ["Primes et indemnités", "Tout ce qui s'ajoute au salaire de base (indemnités de fonction, de "
                                 "transport…)."],
        ["Salaire brut", "Salaire de base + primes et indemnités. C'est la base de la masse salariale."],
        ["Cotisations salariales", "Part des cotisations sociales retenue sur le salaire de l'agent (retraite, "
                                   "assurance maladie…)."],
        ["Impôt et CSS", "Impôt sur le revenu retenu à la source et contribution sociale de solidarité."],
        ["Net à payer", "Ce que l'agent reçoit réellement sur son compte, après toutes les retenues (y compris "
                        "les remboursements de prêts et les cessions sur salaire)."],
        ["Charges patronales", "Cotisations payées par l'employeur en plus du brut."],
        ["Coût employeur", "Brut + charges patronales. C'est ce que l'agent coûte réellement à l'entreprise."],
    ], [4.2, 12.8]),
    ("note", "Exemple simplifié : un agent a un brut de 2 000 DT. Après 200 DT de cotisations salariales et "
             "250 DT d'impôt, son net est de 1 550 DT. Si l'entreprise paie 400 DT de charges patronales, le "
             "coût employeur est de 2 400 DT."),
    ("h2", "Masse salariale et budget"),
    ("ul", [
        "La <b>masse salariale brute</b> est la somme des salaires bruts de tous les agents sur une période. "
        "C'est en général le premier poste de dépenses de l'entreprise.",
        "Chaque année, un <b>budget</b> de masse salariale est voté, découpé en <b>rubriques budgétaires</b> "
        "(salaires, charges sociales, recrutements, promotions, départs…).",
        "Le <b>réalisé</b> est calculé à partir de la paie réellement versée. "
        "Le <b>taux de réalisation</b> = réalisé / budget ; l'<b>écart</b> = réalisé - budget. Un écart positif "
        "est un dépassement.",
    ]),
]

TEMPS = [
    ("h2", "Congés et absences"),
    ("p", "Toute absence fait l'objet d'une <b>demande de congé</b> avec un <b>type</b>, un <b>motif</b>, une "
          "date de début, une date de fin et un nombre de jours. Les principaux types sont :"),
    ("table", ["Type", "Exemples", "Compté dans l'absentéisme ?"], [
        ["Congé annuel", "Vacances payées, acquises chaque année.", "Non : c'est un droit normal."],
        ["Congé de maladie", "Maladie ordinaire, maternité, hospitalisation, chirurgie.", "Oui"],
        ["Congé exceptionnel", "Mariage, naissance, décès d'un proche…", "Oui"],
        ["Sanction", "Mise à pied (absence non payée imposée).", "Oui"],
        ["Autres absences", "Formation, mission, oubli de badge.", "Non : l'agent travaille."],
    ], [3.6, 7.6, 5.8]),
    ("p", "Une demande a un <b>statut</b> : Saisi, En instance, Validé ou Annulé. Les demandes annulées sont "
          "exclues des calculs. Le <b>solde de congé</b> est le nombre de jours de congé annuel qui restent à "
          "l'agent."),
    ("h2", "Absentéisme"),
    ("p", "Le <b>taux d'absentéisme</b> rapporte les jours d'absence aux jours où les agents auraient dû "
          "travailler (les <b>jours théoriques</b>). Par convention, une année compte <b>230 jours ouvrés</b> "
          "par agent, soit environ 19,2 jours par mois."),
    ("note", "Exemple : 100 agents payés pendant 12 mois représentent 23 000 jours théoriques. Avec 690 jours "
             "d'absence pour maladie, maternité, congés exceptionnels et sanctions, le taux d'absentéisme global "
             "est de 690 / 23 000 = 3 %."),
    ("h2", "Maladie et accidents"),
    ("ul", [
        "Un <b>arrêt</b> est une période d'absence pour raison de santé. On suit le nombre d'arrêts, les jours "
        "perdus et la durée moyenne d'un arrêt.",
        "Un <b>accident de travail</b> survient pendant le travail ou sur le trajet. Une <b>maladie "
        "professionnelle</b> est causée par l'activité. Les séquelles peuvent donner un taux d'<b>IPP</b> "
        "(incapacité permanente partielle).",
        "Pendant un arrêt maladie, l'agent peut demander des <b>indemnités</b> à la <b>CNAM</b> (caisse "
        "nationale d'assurance maladie).",
    ]),
    ("h2", "Présence et ponctualité"),
    ("ul", [
        "Le <b>pointage</b> enregistre les heures d'entrée et de sortie de l'agent (badge).",
        "Un <b>retard</b> est une arrivée après l'heure prévue. On suit le nombre de retards, leur durée en "
        "minutes et les jours ou heures où ils sont les plus fréquents.",
        "Une <b>autorisation de sortie</b> permet à un agent de s'absenter quelques heures pendant la journée.",
        "Un <b>intérim</b> désigne le remplacement d'un agent absent (souvent un responsable en congé) par un "
        "collègue, pour assurer la continuité du service.",
    ]),
]

SOCIAL = [
    ("h2", "Couverture médicale"),
    ("p", "Les agents bénéficient d'une couverture des frais de soins pour eux-mêmes et leur famille "
          "(conjoint, enfants). Le circuit est le suivant :"),
    ("ul", [
        "L'agent engage des frais (consultation, pharmacie, analyses…) : ce sont les <b>frais engagés</b>.",
        "Il dépose un <b>bulletin de soins</b>, qui détaille les <b>actes</b> médicaux.",
        "Le bulletin est traité puis remboursé : c'est le <b>montant remboursé</b>.",
        "<b>Taux de remboursement</b> = montant remboursé / frais engagés. Le <b>délai</b> mesure le temps entre "
        "la date des soins et la réception du bulletin.",
    ]),
    ("h2", "Œuvres sociales"),
    ("ul", [
        "<b>Aides et dons</b> : sommes accordées aux agents dans des situations particulières (événements "
        "familiaux, difficultés…). On compare le montant demandé au montant accordé.",
        "<b>Prime de scolarité</b> : aide versée pour chaque enfant scolarisé, à la rentrée.",
    ]),
    ("h2", "Prêts et avances"),
    ("p", "L'entreprise peut prêter de l'argent à ses agents (logement, véhicule, avance sur salaire…). "
          "Les prêts sont classés par <b>groupe</b> et par <b>type</b>. Une demande est accordée ou non ; "
          "si elle est accordée, elle est remboursée par <b>échéances</b> (mensualités) retenues sur la paie."),
    ("ul", [
        "<b>Taux d'accord</b> = demandes accordées / demandes.",
        "<b>Prêt en cours</b> : prêt accordé dont la période de remboursement inclut la date du jour.",
        "<b>Mensualités en cours</b> : total des remboursements mensuels prélevés pour les prêts en cours.",
    ]),
    ("h2", "Cessions sur salaire et endettement"),
    ("p", "Une <b>cession sur salaire</b> est une retenue mensuelle que l'agent autorise sur sa paie au profit "
          "d'un tiers : banque, organisme social, cotisation à l'Amicale ou au syndicat (UGTT), abonnement "
          "téléphonique via l'Amicale, buvette, voyages…"),
    ("p", "Le <b>taux d'endettement</b> = total des retenues mensuelles / salaire. Avant d'accorder un nouveau "
          "prêt, le service RH fait une <b>simulation de capacité d'endettement</b> qui donne le taux avant et "
          "après le prêt. Le seuil d'alerte retenu est <b>40 %</b> : au-delà, une part trop importante du salaire "
          "est déjà engagée."),
    ("note", "Exemple : un agent touche 1 500 DT et rembourse déjà 450 DT par mois. Son taux d'endettement est de "
             "30 %. Un nouveau prêt de 150 DT par mois le ferait passer à 40 %, donc au seuil d'alerte."),
    ("h2", "Services RH"),
    ("ul", [
        "<b>Attestations</b> : documents délivrés à la demande de l'agent (attestation de travail, de salaire…).",
        "<b>Demandes de service</b> : requêtes adressées au service RH, suivies avec un état et un "
        "<b>délai de réponse</b>.",
    ]),
]

KPIS = [
    ("p", "Récapitulatif des indicateurs les plus utilisés dans les tableaux de bord."),
    ("table", ["Indicateur", "Formule", "Tableau de bord"], [
        ["Effectif actif", "Agents distincts à l'état « Actif »", "Effectif"],
        ["Effectif payé", "Agents distincts ayant un bulletin mensuel BN dans le mois", "Tableau de bord RH"],
        ["Turnover", "(entrées + sorties) / 2 / effectif moyen", "Tableau de bord RH"],
        ["Taux de rétention", "Agents payés il y a 12 mois et encore payés / agents payés il y a 12 mois",
         "Tableau de bord RH"],
        ["Taux d'encadrement", "Agents avec une fonction / effectif payé", "Tableau de bord RH"],
        ["Taux d'absentéisme global", "Jours d'absence (maladie, maternité, exceptionnels, sanctions) / jours "
                                      "théoriques (230 par an et par agent)", "Tableau de bord RH"],
        ["Taux d'absentéisme maladie", "Jours de maladie / (effectif actif × 230)", "Maladie et accidents"],
        ["Masse salariale brute", "Somme des salaires bruts", "Salaires"],
        ["Coût employeur", "Brut + charges patronales", "Salaires"],
        ["Taux de charges patronales", "Charges patronales / brut", "Salaires"],
        ["Taux de réalisation", "Réalisé de la paie / budget", "Budget"],
        ["Taux de départ", "Départs des 12 derniers mois / effectif actif", "Départs et retraites"],
        ["Taux de recrutement", "Candidats recrutés / candidatures", "Recrutement"],
        ["Note moyenne", "Moyenne des notes de rendement définitives (sur 20)", "Évaluation et rendement"],
        ["Taux de remboursement", "Montant remboursé / frais engagés", "Couverture médicale"],
        ["Taux d'accord", "Demandes accordées / demandes", "Prêts, Œuvres sociales"],
        ["Taux d'endettement", "Retenues mensuelles / salaire (seuil d'alerte : 40 %)", "Endettement"],
    ], [4.2, 8.6, 4.2]),
]

READING = [
    ("p", "Quelques règles valables sur l'ensemble des tableaux de bord :"),
    ("ul", [
        "<b>Regarder la période</b> sous chaque indicateur : « 12 derniers mois », « année en cours », "
        "« dernier mois de paie », « dernière campagne »… Deux chiffres sur des périodes différentes ne se "
        "comparent pas.",
        "<b>« Dernier mois de paie »</b> désigne le dernier mois pour lequel la paie mensuelle a été calculée, "
        "pas forcément le mois en cours.",
        "<b>Agents actifs</b> : la plupart des photographies (effectif, pyramide des âges) ne comptent que les "
        "agents en activité.",
        "<b>Filtres</b> : les filtres en haut du tableau (pôle, direction, catégorie, sexe…) s'appliquent à "
        "tous les graphiques compatibles. Le filtre « Année » est volontairement sans effet sur les indicateurs "
        "déjà calés sur une période fixe.",
        "<b>Compter des personnes ou des événements</b> : « agents concernés » compte des personnes distinctes, "
        "alors que « demandes », « arrêts » ou « participations » comptent des événements. Un même agent peut en "
        "avoir plusieurs.",
        "<b>« Non renseigné »</b> signale une information absente dans la base, pas une erreur du tableau.",
    ]),
]

GLOSSARY = [
    ["Agent", "Membre du personnel de l'entreprise."],
    ["Amicale", "Association du personnel qui propose des services (cotisations, abonnements, voyages…)."],
    ["Ancienneté", "Nombre d'années depuis la date d'embauche."],
    ["Bulletin BN", "Bulletin de paie mensuel normal."],
    ["Catégorie", "Grande famille de personnel (cadres, maîtrise, exécution…)."],
    ["Cession sur salaire", "Retenue mensuelle sur la paie, autorisée par l'agent, au profit d'un tiers."],
    ["CNAM", "Caisse nationale d'assurance maladie."],
    ["CNRPS / CNSS", "Caisses de sécurité sociale et de retraite (secteur public / secteur privé)."],
    ["Coût employeur", "Salaire brut + charges patronales."],
    ["CSS", "Contribution sociale de solidarité, retenue avec l'impôt."],
    ["DT", "Dinar tunisien, unité de tous les montants."],
    ["Fonction", "Responsabilité d'encadrement exercée (chef de service, directeur…)."],
    ["Grade", "Niveau de l'agent dans sa catégorie ; il évolue par promotion."],
    ["GRH", "Gestion des ressources humaines."],
    ["Intérim", "Remplacement temporaire d'un agent absent par un collègue."],
    ["IPP", "Incapacité permanente partielle, suite à un accident de travail."],
    ["Masse salariale", "Somme des salaires versés sur une période."],
    ["Matricule", "Identifiant unique de l'agent (MAT_PERS)."],
    ["Mise à pied", "Sanction : absence imposée et non payée."],
    ["Mutation", "Changement de service ou de direction d'un agent."],
    ["Net à payer", "Montant réellement versé à l'agent après toutes les retenues."],
    ["Rubrique", "Ligne du bulletin de paie (salaire de base, prime, cotisation…)."],
    ["Turnover", "Taux de renouvellement du personnel."],
    ["UGTT", "Union générale tunisienne du travail (syndicat)."],
]

DASHBOARD_QUESTIONS = {
    "synthese": "Vue d'ensemble mensuelle : effectif, entrées et sorties, turnover, absentéisme, masse salariale.",
    "effectif": "Qui sont nos agents ? Répartition par direction, sexe, âge, ancienneté, catégorie et grade.",
    "conges": "Combien de jours d'absence, de quel type, et qui est absent aujourd'hui ?",
    "formation": "Combien d'actions, d'heures et d'agents formés, pour quel coût ?",
    "departs": "Combien de départs et pourquoi ? Combien de retraites dans les années à venir ?",
    "prets": "Combien de prêts demandés et accordés ? Combien est remboursé chaque mois ?",
    "mobilite": "Qui change de service ou de direction ? Combien de promotions ?",
    "recrutement": "Combien de recrutements et de candidatures, par concours et par direction ?",
    "sante": "Quel est le poids de la maladie, de la maternité et des accidents de travail ?",
    "salaires": "Combien coûte le personnel ? Quel est le salaire moyen par catégorie et par grade ?",
    "presence": "Les agents arrivent-ils à l'heure ? Quand et où les retards sont-ils fréquents ?",
    "budget": "La masse salariale respecte-t-elle le budget voté ?",
    "rendement": "Quelles notes les agents obtiennent-ils, et mènent-elles à une promotion ?",
    "soins": "Combien de frais médicaux sont engagés et remboursés, et en combien de temps ?",
    "social": "Quelles aides, dons et primes de scolarité sont accordés ?",
    "endettement": "Combien est prélevé sur les salaires et quels agents sont trop endettés ?",
    "services": "Combien d'attestations, de demandes de service et d'intérims ?",
}


def dashboards_table() -> list:
    rows = []
    for i, (key, _, slug) in enumerate(SUITE, start=1):
        title = importlib.import_module(f"dashboards.{key}").TITLE
        rows.append([str(i), title, DASHBOARD_QUESTIONS.get(key, ""), f"/superset/dashboard/{slug}/"])
    return [
        ("p", "Chaque tableau de bord répond à une question métier. L'adresse est à ajouter derrière l'adresse "
              "du serveur Superset. Une barre de navigation en haut de chaque tableau permet de passer de l'un "
              "à l'autre."),
        ("table", ["N°", "Tableau de bord", "À quoi il sert", "Adresse"], rows, [0.8, 3.8, 7.6, 4.8]),
    ]


SECTIONS = [
    ("1. Introduction : à quoi sert ce guide", INTRO),
    ("2. Le personnel : les notions de base", PERSONNEL),
    ("3. Le parcours de l'agent", PARCOURS),
    ("4. La paie et la masse salariale", PAIE),
    ("5. Le temps de travail et les absences", TEMPS),
    ("6. Le social et les avantages", SOCIAL),
    ("7. Les indicateurs clés", KPIS),
    ("8. La carte des tableaux de bord", None),
    ("9. Bien lire un tableau de bord", READING),
    ("10. Glossaire", [("table", ["Terme", "Définition"], GLOSSARY, [4.2, 12.8])]),
]


# --------------------------------------------------------------------------- rendering


def make_table(headers: list[str], rows: list[list[str]], widths: list[float]) -> Table:
    data = [[Paragraph(f"<b>{h}</b>", STYLES["head"]) for h in headers]]
    data += [[Paragraph(str(v), STYLES["cell"]) for v in row] for row in rows]
    table = Table(data, colWidths=[w * cm for w in widths], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BLUE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#C7D2FE")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def make_note(text: str) -> Table:
    box = Table([[Paragraph(f"<b>À retenir.</b> {text}", STYLES["body"])]], colWidths=[17 * cm])
    box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NOTE_BG),
        ("LINEBEFORE", (0, 0), (0, -1), 3, colors.HexColor("#F59E0B")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
    ]))
    return box


def render_blocks(blocks: list) -> list:
    flow = []
    for block in blocks:
        kind = block[0]
        if kind == "p":
            flow.append(Paragraph(block[1], STYLES["body"]))
        elif kind == "h2":
            flow.append(Paragraph(block[1], STYLES["h2"]))
        elif kind == "ul":
            flow.append(ListFlowable(
                [ListItem(Paragraph(t, STYLES["body"]), leftIndent=12) for t in block[1]],
                bulletType="bullet", start="•", leftIndent=12, bulletFontName=FONT))
        elif kind == "note":
            flow += [Spacer(1, 4), make_note(block[1]), Spacer(1, 8)]
        elif kind == "table":
            flow += [make_table(*block[1:]), Spacer(1, 10)]
    return flow


def on_page(canvas, doc) -> None:
    if doc.page == 1:
        return
    canvas.saveState()
    canvas.setFont(FONT, 8)
    canvas.setFillColor(GREY)
    canvas.drawString(2 * cm, 1.2 * cm, "Guide métier GRH : les notions de base")
    canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Page {doc.page}")
    canvas.restoreState()


def build(out: Path) -> None:
    flow = [
        Spacer(1, 6 * cm),
        Paragraph("Guide métier GRH", STYLES["title"]),
        Paragraph("Les notions de base de la gestion des ressources humaines,<br/>"
                  "expliquées à partir des tableaux de bord Superset", STYLES["subtitle"]),
        Spacer(1, 1 * cm),
        Paragraph(f"Document d'accueil pour les nouveaux membres de l'équipe — {datetime.now():%d/%m/%Y}",
                  STYLES["subtitle"]),
        PageBreak(),
        Paragraph("Sommaire", STYLES["h1"]),
    ]
    flow += [Paragraph(title, STYLES["toc"]) for title, _ in SECTIONS]
    flow.append(PageBreak())
    for title, blocks in SECTIONS:
        content = render_blocks(dashboards_table() if blocks is None else blocks)
        flow.append(KeepTogether([Paragraph(title, STYLES["h1"]), *content[:1]]))
        flow += content[1:]
        flow.append(PageBreak())
    flow.pop()

    out.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(out), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm,
                            bottomMargin=2 * cm, title="Guide métier GRH", author="Équipe GRH")
    doc.build(flow, onFirstPage=on_page, onLaterPages=on_page)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    build(args.out)
    print(f"document: {args.out}")


if __name__ == "__main__":
    main()
