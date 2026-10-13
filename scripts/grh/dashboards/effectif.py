from grh_builder import (
    ACTIF, Dataset, Filter, Metric, TimeFilter, bar, big_number, pie, table, timeseries,
)

KEY = "effectif"
TITLE = "Effectif GRH"
SLUG = "effectif-grh"

DATASETS = [
    Dataset("eff", "v_effectif_grh", "effectif.sql", [
        Metric("effectif", "COUNT(DISTINCT MAT_PERS)", "Effectif"),
        Metric("pct_femmes", "SUM(CASE WHEN SEXE = 'Femme' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0)", "% Femmes", ".1%"),
        Metric("age_moyen", "AVG(AGE)", "Âge moyen", ",.1f"),
        Metric("anciennete_moy", "AVG(ANCIENNETE)", "Ancienneté moyenne", ",.1f"),
        Metric("recrut_annee",
               "COUNT(DISTINCT CASE WHEN EXTRACT(YEAR FROM DAT_EMB) = EXTRACT(YEAR FROM SYSDATE) THEN MAT_PERS END)",
               "Recrutements année en cours"),
        Metric("departs_annee",
               "COUNT(DISTINCT CASE WHEN EXTRACT(YEAR FROM DAT_DEPART) = EXTRACT(YEAR FROM SYSDATE) THEN MAT_PERS END)",
               "Départs année en cours"),
    ]),
    Dataset("mvt", "v_mouvements_grh", "mouvements.sql", [
        Metric("nb_mouvements", "COUNT(*)", "Mouvements"),
    ], main_dttm_col="DATE_MVT"),
]


def charts(ds):
    return {
        "kpi_effectif": big_number("eff", "Effectif actif", "effectif", "agents en activité", filters=[ACTIF]),
        "kpi_femmes": big_number("eff", "Taux de féminisation", "pct_femmes", "des agents actifs", ".1%", [ACTIF]),
        "kpi_age": big_number("eff", "Âge moyen", "age_moyen", "ans (agents actifs)", ",.1f", [ACTIF]),
        "kpi_anciennete": big_number("eff", "Ancienneté moyenne", "anciennete_moy", "ans (agents actifs)", ",.1f", [ACTIF]),
        "kpi_recrut": big_number("eff", "Recrutements de l'année", "recrut_annee", "année en cours"),
        "kpi_departs": big_number("eff", "Départs de l'année", "departs_annee", "année en cours"),
        "direction": bar("eff", "Effectif par direction", "DIRECTION", "effectif", horizontal=True, filters=[ACTIF]),
        "sexe": pie("eff", "Répartition par sexe", "SEXE", "effectif", [ACTIF]),
        "pyramide": bar("eff", "Pyramide des âges", "TRANCHE_AGE", "effectif", ["SEXE"], horizontal=True,
                        sort_by_metric=False, stack=True, filters=[ACTIF]),
        "anciennete": bar("eff", "Effectif par tranche d'ancienneté", "TRANCHE_ANCIENNETE", "effectif",
                          sort_by_metric=False, filters=[ACTIF]),
        "categorie": pie("eff", "Répartition par catégorie", "CATEGORIE", "effectif", [ACTIF]),
        "grade": bar("eff", "Effectif par grade", "GRADE", "effectif", horizontal=True, filters=[ACTIF]),
        "mouvements": timeseries("mvt", "Recrutements et départs par année", "DATE_MVT", "nb_mouvements",
                                 ["TYPE_MVT"], stack=False),
        "region": bar("eff", "Effectif par région", "REGION", "effectif", filters=[ACTIF]),
        "fonction": pie("eff", "Agents par fonction", "FONCTION", "effectif", [ACTIF]),
        "liste": table("eff", "Liste du personnel actif", [
            "MAT_PERS", "NOM_PRENOM", "SEXE", "AGE", "DIRECTION", "SERVICE", "CATEGORIE", "GRADE",
            "FONCTION", "REGION", "POSITION_ADMINISTRATIVE", "DAT_EMB", "ANCIENNETE",
        ], "NOM_PRENOM", filters=[ACTIF]),
    }


LAYOUT = [
    [("kpi_effectif", 2, 26), ("kpi_femmes", 2, 26), ("kpi_age", 2, 26),
     ("kpi_anciennete", 2, 26), ("kpi_recrut", 2, 26), ("kpi_departs", 2, 26)],
    [("direction", 8, 64), ("sexe", 4, 64)],
    [("pyramide", 6, 60), ("anciennete", 6, 60)],
    [("categorie", 4, 64), ("grade", 8, 64)],
    [("mouvements", 8, 60), ("region", 4, 60)],
    [("fonction", 4, 70), ("liste", 8, 70)],
]

FILTERS = [
    Filter("Pôle", "POLE", "eff"),
    Filter("Direction", "DIRECTION", "eff"),
    Filter("Catégorie", "CATEGORIE", "eff"),
    Filter("Grade", "GRADE", "eff"),
    Filter("Sexe", "SEXE", "eff"),
    Filter("Région", "REGION", "eff"),
    Filter("Position administrative", "POSITION_ADMINISTRATIVE", "eff",
           exclude=["kpi_recrut", "kpi_departs", "mouvements"]),
    TimeFilter("Période (recrutements / départs)", ["mouvements"]),
]
