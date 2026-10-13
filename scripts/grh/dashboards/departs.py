from grh_builder import (
    Dataset, Filter, Metric, bar, big_number, pie, simple_filter, sql_filter, table, timeseries,
)

KEY = "departs"
TITLE = "Départs et retraites"
SLUG = "departs-retraites"

DATASETS = [
    Dataset("dep", "v_grh_departs", "departs.sql", [
        Metric("departs", "COUNT(DISTINCT MAT_PERS)", "Départs"),
        Metric("taux_rotation",
               "SUM(DERNIER_12_MOIS) / NULLIF(MAX(EFFECTIF_ACTIF), 0)",
               "Taux de départ (12 mois)", ".1%"),
        Metric("age_moyen_depart", "AVG(AGE_DEPART)", "Âge moyen au départ", ",.1f"),
    ], main_dttm_col="DAT_DEPART"),
    Dataset("ret", "v_grh_retraites", "retraites.sql", [
        Metric("retraites", "COUNT(DISTINCT MAT_PERS)", "Départs à la retraite prévus"),
    ], main_dttm_col="DATE_RETRAITE"),
]

ANNEE_COURANTE = sql_filter("ANNEE = TO_CHAR(SYSDATE, 'YYYY')")
DOUZE_MOIS = sql_filter("MOIS_RESTANTS BETWEEN 0 AND 12")
CINQ_ANS = sql_filter("MOIS_RESTANTS BETWEEN 0 AND 60")
DIX_ANS = sql_filter("MOIS_RESTANTS BETWEEN 0 AND 120")
VINGT_QUATRE_MOIS = sql_filter("MOIS_RESTANTS <= 24")


def charts(ds):
    return {
        "kpi_departs": big_number("dep", "Départs de l'année", "departs", "année en cours", filters=[ANNEE_COURANTE]),
        "kpi_taux": big_number("dep", "Taux de départ", "taux_rotation", "12 derniers mois / effectif actif", ".1%"),
        "kpi_ret12": big_number("ret", "Retraites dans 12 mois", "retraites", "agents actifs", filters=[DOUZE_MOIS]),
        "kpi_ret5": big_number("ret", "Retraites dans 5 ans", "retraites", "agents actifs", filters=[CINQ_ANS]),
        "evolution": timeseries("dep", "Départs par année et par motif", "DAT_DEPART", "departs", ["TYPE_DEPART"]),
        "motifs": pie("dep", "Répartition des départs par motif", "TYPE_DEPART", "departs"),
        "direction": bar("dep", "Départs par direction", "DIRECTION", "departs", horizontal=True),
        "categorie": bar("dep", "Départs par catégorie", "CATEGORIE", "departs"),
        "projection": bar("ret", "Retraites prévues par année (10 ans)", "ANNEE_RETRAITE", "retraites",
                          ["CATEGORIE"], sort_by_metric=False, stack=True, filters=[DIX_ANS]),
        "ret_direction": bar("ret", "Retraites prévues dans 5 ans par direction", "DIRECTION", "retraites",
                             horizontal=True, filters=[CINQ_ANS]),
        "liste": table("ret", "Agents partant à la retraite dans 24 mois", [
            "MAT_PERS", "NOM_PRENOM", "DIRECTION", "CATEGORIE", "GRADE", "FONCTION", "AGE", "ANCIENNETE",
            "DATE_RETRAITE", "MOIS_RESTANTS", "STATUT_RETRAITE",
        ], "DATE_RETRAITE", filters=[VINGT_QUATRE_MOIS]),
    }


LAYOUT = [
    [("kpi_departs", 3, 26), ("kpi_taux", 3, 26), ("kpi_ret12", 3, 26), ("kpi_ret5", 3, 26)],
    [("evolution", 8, 60), ("motifs", 4, 60)],
    [("direction", 8, 64), ("categorie", 4, 64)],
    [("projection", 7, 64), ("ret_direction", 5, 64)],
    [("liste", 12, 64)],
]

FILTERS = [
    Filter("Motif de départ", "TYPE_DEPART", "dep"),
    Filter("Année de départ", "ANNEE", "dep", exclude=["kpi_departs", "kpi_taux"]),
    Filter("Pôle", "POLE", "dep"),
    Filter("Direction", "DIRECTION", "dep"),
    Filter("Catégorie", "CATEGORIE", "dep"),
    Filter("Sexe", "SEXE", "dep"),
]
