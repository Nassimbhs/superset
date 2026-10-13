from grh_builder import (
    Dataset, Filter, Metric, bar, big_number, pie, simple_filter, sql_filter, table, timeseries,
)

KEY = "sante"
TITLE = "Maladie et accidents"
SLUG = "maladie-accidents"

JOURS_OUVRES_AN = 230

DATASETS = [
    Dataset("abs", "v_grh_absences_maladie", "absences_maladie.sql", [
        Metric("jours_maladie", "SUM(NBR_JOURS)", "Jours d'absence"),
        Metric("arrets", "COUNT(*)", "Arrêts"),
        Metric("agents_absents", "COUNT(DISTINCT MAT_PERS)", "Agents concernés"),
        Metric("duree_moyenne", "AVG(NBR_JOURS)", "Durée moyenne d'un arrêt (jours)", ",.1f"),
        Metric("taux_absenteisme",
               f"SUM(NBR_JOURS) / NULLIF(MAX(EFFECTIF_ACTIF) * {JOURS_OUVRES_AN}, 0)",
               "Taux d'absentéisme maladie", ".2%"),
    ], main_dttm_col="DAT_DEBUT"),
    Dataset("ind", "v_grh_indemnites_maladie", "indemnites_maladie.sql", [
        Metric("demandes_ind", "COUNT(DISTINCT NUM_DEM)", "Demandes d'indemnités"),
        Metric("jours_ind", "SUM(NBR_JOURS)", "Jours indemnisés"),
    ], main_dttm_col="DAT_ARRET"),
    Dataset("acc", "v_grh_accidents", "accidents.sql", [
        Metric("accidents", "COUNT(*)", "Accidents"),
    ], main_dttm_col="DAT_ACC"),
]

DOUZE_MOIS = simple_filter("DERNIER_12_MOIS", "==", 1)
CINQ_ANS = sql_filter("DAT_DEBUT >= ADD_MONTHS(TRUNC(SYSDATE, 'YYYY'), -48)")
DIX_ANS = sql_filter("DAT_DEBUT >= ADD_MONTHS(TRUNC(SYSDATE, 'YYYY'), -108)")


def charts(ds):
    return {
        "kpi_jours": big_number("abs", "Jours d'absence maladie", "jours_maladie", "12 derniers mois",
                                filters=[DOUZE_MOIS]),
        "kpi_taux": big_number("abs", "Taux d'absentéisme maladie", "taux_absenteisme",
                               f"12 mois / (effectif actif × {JOURS_OUVRES_AN} j)", ".2%", filters=[DOUZE_MOIS]),
        "kpi_agents": big_number("abs", "Agents en arrêt maladie", "agents_absents", "12 derniers mois",
                                 filters=[DOUZE_MOIS]),
        "kpi_acc": big_number("acc", "Accidents déclarés", "accidents", "depuis l'origine"),
        "evolution": timeseries("abs", "Jours d'absence par année et par nature (10 ans)", "DAT_DEBUT",
                                "jours_maladie", ["NATURE_ABSENCE"], filters=[DIX_ANS]),
        "nature": pie("abs", "Jours d'absence par nature (12 mois)", "NATURE_ABSENCE", "jours_maladie",
                      filters=[DOUZE_MOIS]),
        "taux_annee": timeseries("abs", "Taux d'absentéisme maladie par année (10 ans)", "DAT_DEBUT",
                                 "taux_absenteisme", kind="line", fmt=".2%", filters=[DIX_ANS]),
        "saison": bar("abs", "Arrêts par mois de début (5 ans)", "MOIS", "arrets", sort_by_metric=False,
                      filters=[CINQ_ANS]),
        "direction": bar("abs", "Jours d'absence par direction (12 mois)", "DIRECTION", "jours_maladie",
                         horizontal=True, filters=[DOUZE_MOIS]),
        "age": bar("abs", "Jours d'absence par tranche d'âge et sexe (12 mois)", "TRANCHE_AGE", "jours_maladie",
                   ["SEXE"], sort_by_metric=False, stack=True, filters=[DOUZE_MOIS]),
        "indemnites": bar("ind", "Demandes d'indemnités maladie (CNAM) par année", "ANNEE", "demandes_ind",
                          ["SITUATION"], sort_by_metric=False, stack=True),
        "duree": bar("abs", "Durée moyenne d'un arrêt par nature", "NATURE_ABSENCE", "duree_moyenne",
                     fmt=",.1f"),
        "liste_acc": table("acc", "Liste des accidents", [
            "DAT_ACC", "MAT_PERS", "NOM_PRENOM", "DIRECTION", "CATEGORIE", "NATURE_ACCIDENT",
            "LIEU_ACCIDENT", "CIRCONSTANCES", "DAT_ARRET_TRAV", "TAUX_IPP",
        ], "DAT_ACC", ascending=False),
    }


LAYOUT = [
    [("kpi_jours", 3, 26), ("kpi_taux", 3, 26), ("kpi_agents", 3, 26), ("kpi_acc", 3, 26)],
    [("evolution", 8, 60), ("nature", 4, 60)],
    [("taux_annee", 6, 56), ("saison", 6, 56)],
    [("direction", 7, 64), ("age", 5, 64)],
    [("indemnites", 7, 56), ("duree", 5, 56)],
    [("liste_acc", 12, 40)],
]

FILTERS = [
    Filter("Année", "ANNEE", "abs", exclude=["kpi_jours", "kpi_taux", "kpi_agents", "nature", "direction", "age"]),
    Filter("Nature d'absence", "NATURE_ABSENCE", "abs"),
    Filter("Pôle", "POLE", "abs"),
    Filter("Direction", "DIRECTION", "abs"),
    Filter("Catégorie", "CATEGORIE", "abs"),
    Filter("Sexe", "SEXE", "abs"),
    Filter("Tranche d'âge", "TRANCHE_AGE", "abs"),
]
