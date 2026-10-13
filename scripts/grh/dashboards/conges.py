from grh_builder import (
    Dataset, Filter, Metric, bar, big_number, pie, simple_filter, sql_filter, table, timeseries,
)

KEY = "conges"
TITLE = "Congés et absences"
SLUG = "conges-absences"

DATASETS = [
    Dataset("cng", "v_grh_conges", "conges.sql", [
        Metric("nb_demandes", "COUNT(*)", "Demandes"),
        Metric("jours", "SUM(NBR_JOURS)", "Jours d'absence", ",.1f"),
        Metric("duree_moy", "AVG(NBR_JOURS)", "Durée moyenne (jours)", ",.1f"),
        Metric("solde_moy", "AVG(SOLD_CNG)", "Solde moyen (jours)", ",.1f"),
        Metric("absents_jour", "COUNT(DISTINCT CASE WHEN EN_COURS = 1 THEN MAT_PERS END)", "Absents aujourd'hui"),
        Metric("agents", "COUNT(DISTINCT MAT_PERS)", "Agents concernés"),
    ], main_dttm_col="DAT_DEBUT"),
]

NON_ANNULE = simple_filter("STATUT", "!=", "Annulé")
ANNEE_COURANTE = sql_filter("ANNEE = TO_CHAR(SYSDATE, 'YYYY')")
DOUZE_MOIS = sql_filter("DAT_DEBUT >= ADD_MONTHS(TRUNC(SYSDATE), -12) AND DAT_DEBUT <= TRUNC(SYSDATE)")
VINGT_QUATRE_MOIS = sql_filter("DAT_DEBUT >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -24)")
EN_COURS = simple_filter("EN_COURS", "==", 1)


def charts(ds):
    return {
        "kpi_demandes": big_number("cng", "Demandes de l'année", "nb_demandes", "année en cours",
                                   filters=[NON_ANNULE, ANNEE_COURANTE]),
        "kpi_jours": big_number("cng", "Jours d'absence de l'année", "jours", "année en cours", ",.0f",
                                [NON_ANNULE, ANNEE_COURANTE]),
        "kpi_duree": big_number("cng", "Durée moyenne", "duree_moy", "jours par absence (année en cours)", ",.1f",
                                [NON_ANNULE, ANNEE_COURANTE]),
        "kpi_absents": big_number("cng", "Absents aujourd'hui", "absents_jour", "agents en congé ce jour",
                                  filters=[NON_ANNULE, EN_COURS]),
        "mensuel": timeseries("cng", "Jours d'absence par mois (24 derniers mois)", "DAT_DEBUT", "jours",
                              ["TYPE_CONGE"], grain="P1M", filters=[NON_ANNULE, VINGT_QUATRE_MOIS], fmt=",.0f"),
        "annuel": timeseries("cng", "Jours d'absence par année", "DAT_DEBUT", "jours", ["TYPE_CONGE"],
                             filters=[NON_ANNULE], fmt=",.0f"),
        "types": pie("cng", "Répartition par type (12 derniers mois)", "TYPE_CONGE", "jours",
                     [NON_ANNULE, DOUZE_MOIS], ",.0f"),
        "direction": bar("cng", "Jours d'absence par direction (12 derniers mois)", "DIRECTION", "jours",
                         horizontal=True, filters=[NON_ANNULE, DOUZE_MOIS], fmt=",.0f"),
        "motifs": bar("cng", "Absences par motif (12 derniers mois)", "MOTIF", "jours", horizontal=True,
                      filters=[NON_ANNULE, DOUZE_MOIS], fmt=",.0f", limit=15),
        "statut": pie("cng", "Demandes par statut", "STATUT", "nb_demandes"),
        "en_cours": table("cng", "Agents en congé aujourd'hui", [
            "MAT_PERS", "NOM_PRENOM", "DIRECTION", "TYPE_CONGE", "MOTIF", "DAT_DEBUT", "DAT_FIN", "NBR_JOURS",
        ], "DAT_FIN", filters=[NON_ANNULE, EN_COURS]),
    }


LAYOUT = [
    [("kpi_demandes", 3, 26), ("kpi_jours", 3, 26), ("kpi_duree", 3, 26), ("kpi_absents", 3, 26)],
    [("mensuel", 8, 64), ("types", 4, 64)],
    [("annuel", 12, 60)],
    [("direction", 6, 70), ("motifs", 6, 70)],
    [("statut", 4, 60), ("en_cours", 8, 60)],
]

ROLLING = ["kpi_demandes", "kpi_jours", "kpi_duree", "kpi_absents", "mensuel", "types", "direction",
           "motifs", "en_cours"]

FILTERS = [
    Filter("Année", "ANNEE", "cng", exclude=ROLLING),
    Filter("Type de congé", "TYPE_CONGE", "cng"),
    Filter("Statut", "STATUT", "cng"),
    Filter("Pôle", "POLE", "cng"),
    Filter("Direction", "DIRECTION", "cng"),
    Filter("Catégorie", "CATEGORIE", "cng"),
    Filter("Sexe", "SEXE", "cng"),
]
