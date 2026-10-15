"""Business vocabulary of the Portail RH (search, labels, presets).

Every chart of the dashboard specs already becomes a portal question; this
module only adds what the specs cannot express: synonyms, readable labels and
extra questions phrased the way HR users ask them.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

DEFAULT_COMPANY = "01"


@dataclass
class Preset:
    domain: str
    label: str
    keywords: list[str]
    dataset: str
    metrics: list[str]
    groupby: str | None = None
    series: str | None = None
    grain: str | None = None
    filters: dict[str, list[Any]] = field(default_factory=dict)
    view: str = "bar"
    # Names of filter constants of the domain spec (e.g. "DOUZE_MOIS"), kept as fixed conditions.
    conditions: list[str] = field(default_factory=list)


# Words users type for each domain (accents and case are ignored by the search).
DOMAIN_SYNONYMS = {
    "synthese": ["synthèse", "vue d'ensemble", "mensuel", "turnover", "rétention", "encadrement", "indicateurs"],
    "effectif": ["effectif", "agents", "personnel", "salariés", "employés", "headcount", "pyramide", "âge",
                 "ancienneté", "féminisation"],
    "conges": ["congé", "congés", "absence", "absents", "vacances", "solde", "repos"],
    "formation": ["formation", "stage", "stagiaires", "heures", "apprentissage", "cours"],
    "departs": ["départ", "départs", "retraite", "sortie", "démission", "fin de contrat"],
    "prets": ["prêt", "prêts", "avance", "crédit", "remboursement", "mensualité"],
    "mobilite": ["mobilité", "mutation", "carrière", "promotion", "avancement", "grade"],
    "recrutement": ["recrutement", "embauche", "candidat", "candidature", "concours", "entrées"],
    "sante": ["maladie", "accident", "arrêt", "absentéisme", "maternité", "CNAM", "santé"],
    "salaires": ["salaire", "paie", "rémunération", "masse salariale", "brut", "net", "coût", "charges", "prime"],
    "presence": ["présence", "retard", "ponctualité", "pointage", "autorisation de sortie", "horaire"],
    "budget": ["budget", "réalisé", "écart", "exercice", "dépassement", "prévision"],
    "rendement": ["rendement", "évaluation", "note", "notation", "performance", "campagne"],
    "soins": ["soins", "couverture médicale", "remboursement", "frais médicaux", "bulletin de soins", "mutuelle"],
    "social": ["œuvres sociales", "don", "aide", "scolarité", "amicale", "social"],
    "endettement": ["endettement", "cession", "dette", "retenue", "capacité", "seuil"],
    "services": ["attestation", "demande de service", "intérim", "remplacement", "services RH"],
}

# Query words expanded before matching ("salarié" also finds "agent").
WORD_SYNONYMS = {
    "salarie": ["agent", "effectif", "personnel"],
    "salaries": ["agent", "effectif", "personnel"],
    "employe": ["agent", "effectif", "personnel"],
    "employes": ["agent", "effectif", "personnel"],
    "collaborateur": ["agent", "effectif"],
    "nombre": ["effectif", "nb"],
    "combien": ["effectif", "nombre"],
    "femme": ["sexe", "feminisation"],
    "femmes": ["sexe", "feminisation"],
    "homme": ["sexe"],
    "hommes": ["sexe"],
    "genre": ["sexe"],
    "paye": ["paie", "salaire"],
    "remuneration": ["salaire", "paie"],
    "embauche": ["recrutement"],
    "embauches": ["recrutement"],
    "entree": ["recrutement", "entrees"],
    "sortie": ["depart", "sorties"],
    "absenteisme": ["absence", "maladie"],
    "vacances": ["conge"],
    "direction": ["direction"],
    "departement": ["direction", "service"],
    "division": ["direction", "pole"],
    "mois": ["mensuel", "mois"],
    "annee": ["annee", "annuel"],
    "evolution": ["annee", "mois", "evolution"],
    "liste": ["liste", "detail"],
    "actif": ["actif", "activite"],
    "actifs": ["actif", "activite"],
}

COLUMN_LABELS = {
    "COD_SOC": "Société",
    "MAT_PERS": "Matricule",
    "NOM_PRENOM": "Nom et prénom",
    "ETAT": "Statut",
    "EST_ACTIF": "Actif",
    "POLE": "Pôle",
    "DIRECTION": "Direction",
    "SERVICE": "Service",
    "CATEGORIE": "Catégorie",
    "GRADE": "Grade",
    "FONCTION": "Fonction",
    "SEXE": "Sexe",
    "REGION": "Région",
    "AGE": "Âge",
    "TRANCHE_AGE": "Tranche d'âge",
    "ANCIENNETE": "Ancienneté (ans)",
    "TRANCHE_ANCIENNETE": "Tranche d'ancienneté",
    "POSITION_ADMINISTRATIVE": "Position administrative",
    "NATURE_RECRUTEMENT": "Nature de recrutement",
    "TYPE_DEPART": "Motif de départ",
    "SITUATION_FAMILIALE": "Situation familiale",
    "NBRE_ENF": "Nombre d'enfants",
    "DAT_NAIS": "Date de naissance",
    "DAT_EMB": "Date d'embauche",
    "DAT_DEPART": "Date de départ",
    "DAT_DEBUT": "Date de début",
    "DAT_FIN": "Date de fin",
    "ANNEE": "Année",
    "MOIS": "Mois",
    "NUM_MOIS": "Mois",
    "DT_MOIS": "Mois",
    "DT_BUL": "Mois de paie",
    "TYPE_CONGE": "Type de congé",
    "MOTIF": "Motif",
    "STATUT": "Statut",
    "NBR_JOURS": "Nombre de jours",
    "TYPE_MVT": "Type de mouvement",
    "DATE_MVT": "Date du mouvement",
    "DATE_RETRAITE": "Date de retraite",
    "ANNEE_RETRAITE": "Année de retraite",
    "MOIS_RESTANTS": "Mois restants",
    "STATUT_RETRAITE": "Statut retraite",
    "GROUPE_PRET": "Groupe de prêt",
    "TYPE_PRET": "Type de prêt",
    "MNT_ACCORDE": "Montant accordé",
    "NBR_ECH": "Nombre d'échéances",
    "REM_MEN": "Mensualité",
    "DIRECTION_DESTINATION": "Direction d'accueil",
    "SERVICE_ORIGINE": "Service d'origine",
    "SERVICE_DESTINATION": "Service d'accueil",
    "FLUX_ORIGINE": "Direction d'origine",
    "FLUX_DESTINATION": "Direction d'accueil",
    "RAISON": "Raison",
    "NUM_DECISION": "N° de décision",
    "GRADE_OBTENU": "Grade obtenu",
    "FAMILLE_REMUNERATION": "Famille de rémunération",
    "TYPE_BULLETIN": "Type de bulletin",
    "NATURE_ABSENCE": "Nature d'absence",
    "TRANCHE_RETARD": "Durée du retard",
    "JOUR_SEMAINE": "Jour de la semaine",
    "HEURE_ARRIVEE": "Heure d'arrivée",
    "HEURE_SORTIE": "Heure de sortie",
    "CATEGORIE_FORMATION": "Catégorie de formation",
    "DOMAINE": "Domaine",
    "NATURE": "Nature",
    "INTITULE": "Intitulé",
    "HEURES": "Heures",
    "PARTICIPANTS": "Participants",
    "LIEU": "Lieu",
    "COUT": "Coût (DT)",
    "TYPE_RUBRIQUE": "Type de rubrique",
    "RUBRIQUE": "Rubrique",
    "CONCOURS": "Concours",
    "MODE_RECRUTEMENT": "Mode de recrutement",
    "SITUATION": "Situation",
    "NATURE_DON": "Nature du don",
    "FAMILLE_CESSION": "Famille de cession",
    "BENEFICIAIRE": "Bénéficiaire",
    "TYPE_ACTE": "Type d'acte",
    "TYPE_DEMANDE": "Type de demande",
    "AGE_RECRUTEMENT": "Âge au recrutement",
}

# Labels of the fixed conditions carried by dashboard charts, by constant name.
# "<domain>.<NAME>" wins over "<NAME>" when the same name means different things.
CONDITION_LABELS = {
    "ACTIF": "Agents actifs",
    "DERNIER_MOIS": "Dernier mois de paie",
    "DOUZE_MOIS": "12 derniers mois",
    "VINGT_QUATRE_MOIS": "24 derniers mois",
    "ANNEE_COURANTE": "Année en cours",
    "DERNIERE_ANNEE": "Dernière année",
    "CINQ_ANS": "5 dernières années",
    "DIX_ANS": "10 dernières années",
    "VINGT_ANS": "20 dernières années",
    "TROIS_ANS": "36 derniers mois",
    "NON_ANNULE": "Hors demandes annulées",
    "EN_COURS": "En cours",
    "ACCORDE": "Demandes accordées",
    "EN_ATTENTE": "En attente",
    "INTER_DIRECTION": "Mutations inter-directions",
    "PAIE_MENSUELLE": "Paie mensuelle (bulletins BN)",
    "VALIDEES": "Autorisations validées",
    "RUBRIQUES_PAIE": "Rubriques rattachées à la paie",
    "HORS_THEORIQUE": "Hors jours théoriques",
    "departs.DOUZE_MOIS": "Retraite dans les 12 prochains mois",
    "departs.CINQ_ANS": "Retraite dans les 5 prochaines années",
    "departs.DIX_ANS": "Retraite dans les 10 prochaines années",
    "departs.VINGT_QUATRE_MOIS": "Retraite dans les 24 prochains mois",
}

# Questions phrased the way HR users ask them, on top of the dashboard charts.
EXTRA_PRESETS = [
    Preset("effectif", "Effectif actif par direction", ["effectif", "agents", "direction", "actif"],
           "eff", ["effectif"], "DIRECTION", filters={"ETAT": ["Actif"]}),
    Preset("effectif", "Effectif actif par pôle et par sexe", ["effectif", "pôle", "sexe", "hommes", "femmes"],
           "eff", ["effectif"], "POLE", series="SEXE", filters={"ETAT": ["Actif"]}),
    Preset("effectif", "Effectif actif par service", ["effectif", "service", "agents"],
           "eff", ["effectif"], "SERVICE", filters={"ETAT": ["Actif"]}),
    Preset("effectif", "Effectif par statut", ["statut", "état", "position", "sorti", "actif"],
           "eff", ["effectif"], "ETAT", view="pie"),
    Preset("effectif", "Âge et ancienneté moyens par direction", ["âge", "ancienneté", "moyenne", "direction"],
           "eff", ["age_moyen", "anciennete_moy"], "DIRECTION", filters={"ETAT": ["Actif"]}, view="table"),
    Preset("synthese", "Effectif payé par mois", ["effectif payé", "évolution", "mensuel", "paie"],
           "mens", ["effectif"], grain="P1M", view="line"),
    Preset("conges", "Jours de congé par direction et par type (12 mois)", ["congés", "jours", "direction", "type"],
           "cng", ["jours", "nb_demandes"], "DIRECTION", series="TYPE_CONGE",
           conditions=["NON_ANNULE", "DOUZE_MOIS"]),
    Preset("formation", "Agents formés par catégorie de personnel", ["formés", "catégorie", "agents"],
           "part", ["agents_formes", "heures_stagiaire"], "CATEGORIE"),
    Preset("departs", "Départs par année", ["départs", "année", "évolution"],
           "dep", ["departs"], grain="P1Y"),
    Preset("salaires", "Masse salariale et coût employeur par direction (12 mois)",
           ["masse salariale", "coût", "direction"], "paie", ["masse_brute", "cout_employeur"], "DIRECTION",
           conditions=["DOUZE_MOIS"]),
    Preset("salaires", "Salaire moyen par grade", ["salaire moyen", "grade"],
           "paie", ["salaire_moyen", "net_moyen", "agents_payes"], "GRADE", view="table",
           conditions=["PAIE_MENSUELLE", "DERNIER_MOIS"]),
    Preset("recrutement", "Recrutements par direction", ["recrutements", "embauches", "direction"],
           "rec", ["recrutements", "age_moyen_recrutement"], "DIRECTION"),
    Preset("recrutement", "Recrutements par année", ["recrutements", "embauches", "année", "évolution"],
           "rec", ["recrutements"], grain="P1Y"),
    Preset("sante", "Taux d'absentéisme maladie par direction (12 mois)",
           ["absentéisme", "maladie", "direction", "taux"], "abs", ["taux_absenteisme", "jours_maladie"],
           "DIRECTION", conditions=["DOUZE_MOIS"]),
    Preset("presence", "Retards par direction (12 mois)", ["retards", "direction", "ponctualité"],
           "ret", ["retards", "minutes_retard", "agents_retard"], "DIRECTION", conditions=["DOUZE_MOIS"]),
    Preset("rendement", "Note moyenne par direction", ["note", "moyenne", "direction", "évaluation"],
           "note", ["note_moyenne", "agents_notes"], "DIRECTION"),
    Preset("prets", "Prêts accordés par direction", ["prêts", "direction", "accordés"],
           "prt", ["mnt_accorde", "nb_demandes"], "DIRECTION", conditions=["ACCORDE"]),
    Preset("endettement", "Agents au-delà du seuil d'endettement par direction",
           ["endettement", "seuil", "direction"], "cap", ["agents_seuil", "taux_moyen"], "DIRECTION"),
]

# Business KPIs of the guide (export_guide.KPIS) -> "<domain>.<dataset>", metric.
KPI_METRICS = {
    "Effectif actif": ("effectif.eff", "effectif"),
    "Effectif payé": ("synthese.mens", "effectif"),
    "Turnover": ("synthese.mens", "turnover"),
    "Taux de rétention": ("synthese.mens", "retention"),
    "Taux d'encadrement": ("synthese.mens", "taux_encadrement"),
    "Taux d'absentéisme global": ("synthese.absg", "taux_absenteisme"),
    "Taux d'absentéisme maladie": ("sante.abs", "taux_absenteisme"),
    "Masse salariale brute": ("salaires.paie", "masse_brute"),
    "Coût employeur": ("salaires.paie", "cout_employeur"),
    "Taux de charges patronales": ("salaires.paie", "taux_charges"),
    "Taux de réalisation": ("budget.bud", "taux_realisation"),
    "Taux de départ": ("departs.dep", "taux_rotation"),
    "Taux de recrutement": ("recrutement.cand", "taux_recrutement"),
    "Note moyenne": ("rendement.note", "note_moyenne"),
    "Taux de remboursement": ("soins.bs", "taux_remboursement"),
    "Taux d'accord": ("prets.prt", "taux_accord"),
    "Taux d'endettement": ("endettement.cap", "taux_moyen"),
}

# Data source labels shown in the bubble; other datasets are labelled from their name.
DATASET_LABELS = {
    "synthese.mens": "Effectif et paie mensuels",
    "synthese.absg": "Absentéisme global",
    "effectif.eff": "Personnel",
    "effectif.mvt": "Recrutements et départs",
    "conges.cng": "Congés",
    "formation.act": "Actions de formation",
    "formation.part": "Participants aux formations",
    "departs.dep": "Départs",
    "departs.ret": "Retraites prévues",
    "mobilite.dem": "Demandes de mutation",
    "recrutement.cand": "Candidatures",
    "sante.abs": "Absences maladie",
    "sante.ind": "Indemnités maladie (CNAM)",
    "salaires.paie": "Bulletins de paie",
    "presence.ret": "Retards",
    "presence.aut": "Autorisations de sortie",
    "presence.pt": "Pointages",
    "budget.bud": "Budget et réalisé",
    "rendement.note": "Notes de rendement",
    "soins.bs": "Bulletins de soins",
    "soins.acte": "Actes médicaux",
    "social.don": "Dons et aides",
    "social.sco": "Primes de scolarité",
    "endettement.ces": "Cessions sur salaire",
    "endettement.cap": "Capacité d'endettement",
    "services.dem": "Demandes de service",
    "services.int": "Intérims",
    "prets.prt": "Prêts et avances",
}

# Employee dimensions offered in "Analyser par" whenever the dataset has them.
STANDARD_DIMENSIONS = [
    "POLE", "DIRECTION", "SERVICE", "CATEGORIE", "GRADE", "FONCTION", "SEXE", "TRANCHE_AGE",
    "TRANCHE_ANCIENNETE", "REGION", "POSITION_ADMINISTRATIVE", "ANNEE",
]

# Employee filters always offered in the filter bar when the dataset has them.
STANDARD_FILTERS = ["POLE", "DIRECTION", "CATEGORIE", "SEXE"]

# Columns shown in "Détail" when the domain has no list chart on that dataset.
DEFAULT_DETAIL_COLUMNS = ["MAT_PERS", "NOM_PRENOM", "DIRECTION", "SERVICE", "CATEGORIE", "GRADE", "SEXE", "ETAT"]
