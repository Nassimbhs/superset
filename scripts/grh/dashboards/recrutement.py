from grh_builder import (
    Dataset, Filter, Metric, bar, big_number, pie, sql_filter, table, timeseries,
)

KEY = "recrutement"
TITLE = "Recrutement"
SLUG = "recrutement"

DATASETS = [
    Dataset("cand", "v_grh_candidats", "candidats.sql", [
        Metric("candidats", "COUNT(DISTINCT NUM_FICHE)", "Candidatures"),
        Metric("taux_recrutement", "SUM(RECRUTE) / NULLIF(COUNT(*), 0)", "Taux de recrutement", ".1%"),
        Metric("part_femmes", "SUM(CASE WHEN SEXE = 'Femme' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0)",
               "Part des femmes", ".1%"),
    ], main_dttm_col="DAT_CREAT_FICHE"),
    Dataset("rec", "v_grh_recrutements", "recrutements.sql", [
        Metric("recrutements", "COUNT(DISTINCT MAT_PERS)", "Recrutements"),
        Metric("age_moyen_recrutement", "AVG(AGE_RECRUTEMENT)", "Âge moyen au recrutement", ",.1f"),
    ], main_dttm_col="DAT_EMB"),
]

ANNEE_COURANTE = sql_filter("ANNEE = TO_CHAR(SYSDATE, 'YYYY')")
CINQ_ANS = sql_filter("DAT_EMB >= ADD_MONTHS(TRUNC(SYSDATE, 'YYYY'), -48)")
VINGT_ANS = sql_filter("DAT_EMB >= ADD_MONTHS(TRUNC(SYSDATE, 'YYYY'), -228)")


def charts(ds):
    return {
        "kpi_rec": big_number("rec", "Recrutements de l'année", "recrutements", "année en cours",
                              filters=[ANNEE_COURANTE]),
        "kpi_rec5": big_number("rec", "Recrutements sur 5 ans", "recrutements", "depuis le début de l'année N-4",
                               filters=[CINQ_ANS]),
        "kpi_cand": big_number("cand", "Candidatures", "candidats", "fiches candidats"),
        "kpi_taux": big_number("cand", "Taux de recrutement", "taux_recrutement", "candidats recrutés", ".1%"),
        "evolution": timeseries("rec", "Recrutements par année et par nature", "DAT_EMB", "recrutements",
                                ["NATURE_RECRUTEMENT"], filters=[VINGT_ANS]),
        "nature": pie("rec", "Recrutements par nature (5 ans)", "NATURE_RECRUTEMENT", "recrutements",
                      filters=[CINQ_ANS]),
        "direction": bar("rec", "Recrutements par direction (5 ans)", "DIRECTION", "recrutements",
                         horizontal=True, filters=[CINQ_ANS]),
        "categorie": bar("rec", "Recrutements par catégorie (5 ans)", "CATEGORIE", "recrutements",
                         ["SEXE"], stack=True, filters=[CINQ_ANS]),
        "cand_annee": bar("cand", "Candidatures par année et statut", "ANNEE", "candidats", ["STATUT"],
                          sort_by_metric=False, stack=True),
        "cand_statut": pie("cand", "Candidatures par statut", "STATUT", "candidats"),
        "cand_concours": bar("cand", "Candidatures par concours", "CONCOURS", "candidats", ["MODE_RECRUTEMENT"],
                             horizontal=True, stack=True),
        "cand_age": bar("cand", "Candidatures par tranche d'âge et sexe", "TRANCHE_AGE", "candidats", ["SEXE"],
                        sort_by_metric=False, stack=True),
        "liste": table("rec", "Derniers recrutements", [
            "MAT_PERS", "NOM_PRENOM", "DAT_EMB", "NATURE_RECRUTEMENT", "DIRECTION", "CATEGORIE", "GRADE",
            "SEXE", "AGE_RECRUTEMENT", "ETAT",
        ], "DAT_EMB", ascending=False, limit=200),
    }


LAYOUT = [
    [("kpi_rec", 3, 26), ("kpi_rec5", 3, 26), ("kpi_cand", 3, 26), ("kpi_taux", 3, 26)],
    [("evolution", 8, 60), ("nature", 4, 60)],
    [("direction", 7, 64), ("categorie", 5, 64)],
    [("cand_annee", 7, 60), ("cand_statut", 5, 60)],
    [("cand_concours", 7, 60), ("cand_age", 5, 60)],
    [("liste", 12, 64)],
]

FILTERS = [
    Filter("Année", "ANNEE", "rec", exclude=["kpi_rec", "kpi_rec5"]),
    Filter("Nature de recrutement", "NATURE_RECRUTEMENT", "rec"),
    Filter("Pôle", "POLE", "rec"),
    Filter("Direction", "DIRECTION", "rec"),
    Filter("Catégorie", "CATEGORIE", "rec"),
    Filter("Sexe", "SEXE", "rec"),
    Filter("Concours", "CONCOURS", "cand"),
    Filter("Statut candidature", "STATUT", "cand"),
]
