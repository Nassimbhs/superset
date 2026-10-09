from grh_builder import Dataset, Filter, Metric, bar, big_number, pie, simple_filter, timeseries

KEY = "endettement"
TITLE = "Endettement et cessions sur salaire"
SLUG = "endettement-cessions"

MONTANT = ",.0f"
TAUX = ",.1f"

DATASETS = [
    Dataset("ces", "v_grh_cessions", "cessions.sql", [
        Metric("cessions", "COUNT(*)", "Cessions"),
        Metric("cessions_en_cours", "SUM(EN_COURS)", "Cessions en cours"),
        Metric("mensualites_en_cours", "SUM(CASE WHEN EN_COURS = 1 THEN MENSUALITE END)",
               "Retenues mensuelles en cours", MONTANT),
        Metric("agents_cession", "COUNT(DISTINCT CASE WHEN EN_COURS = 1 THEN MAT_PERS END)",
               "Agents avec une cession en cours"),
    ], main_dttm_col="PRT_DAT_DEM"),
    Dataset("cap", "v_grh_capacite", "capacite.sql", [
        Metric("simulations", "COUNT(*)", "Simulations"),
        Metric("agents", "COUNT(DISTINCT MAT_PERS)", "Agents"),
        Metric("taux_moyen", "AVG(TAUX_APRES_PRET)", "Taux d'endettement moyen après prêt (%)", TAUX),
        Metric("taux_actuel_moyen", "AVG(TAUX_ACTUEL)", "Taux d'endettement moyen avant prêt (%)", TAUX),
        Metric("agents_seuil", "COUNT(DISTINCT CASE WHEN AU_DELA_SEUIL = 1 THEN MAT_PERS END)",
               "Agents à 40 % ou plus"),
    ], main_dttm_col="DAT_SAISIE"),
]

EN_COURS = simple_filter("EN_COURS", "==", 1)
DERNIERE = simple_filter("DERNIERE_SIMULATION", "==", 1)
ACTIF = simple_filter("EST_ACTIF", "==", 1)


def charts(ds):
    return {
        "kpi_cessions": big_number("ces", "Cessions en cours", "cessions_en_cours", "retenues actives sur salaire"),
        "kpi_mensualites": big_number("ces", "Retenues mensuelles", "mensualites_en_cours",
                                      "cessions en cours (DT / mois)", MONTANT),
        "kpi_taux": big_number("cap", "Taux d'endettement moyen", "taux_moyen",
                               "après prêt, dernière simulation des agents actifs (%)", TAUX,
                               filters=[DERNIERE, ACTIF]),
        "kpi_seuil": big_number("cap", "Agents à 40 % ou plus", "agents_seuil",
                                "dernière simulation, agents actifs", filters=[DERNIERE, ACTIF]),
        "ces_famille": pie("ces", "Retenues mensuelles en cours par famille", "FAMILLE_CESSION",
                           "mensualites_en_cours", filters=[EN_COURS], fmt=MONTANT),
        "ces_objet": bar("ces", "Cessions en cours par objet", "OBJET_CESSION", "cessions_en_cours",
                         horizontal=True, filters=[EN_COURS]),
        "ces_annee": bar("ces", "Nouvelles cessions par année et famille", "ANNEE", "cessions",
                         ["FAMILLE_CESSION"], sort_by_metric=False, stack=True),
        "cap_tranche": bar("cap", "Agents actifs par tranche d'endettement (dernière simulation)",
                           "TRANCHE_ENDETTEMENT", "agents", sort_by_metric=False, filters=[DERNIERE, ACTIF]),
        "cap_categorie": bar("cap", "Taux d'endettement moyen par catégorie (dernière simulation)", "CATEGORIE",
                             ["taux_actuel_moyen", "taux_moyen"], filters=[DERNIERE, ACTIF], fmt=TAUX),
        "cap_evolution": timeseries("cap", "Taux d'endettement moyen des simulations par année", "DAT_SAISIE",
                                    ["taux_actuel_moyen", "taux_moyen"], kind="line", stack=False, fmt=TAUX),
        "cap_direction": bar("cap", "Agents à 40 % ou plus par direction", "DIRECTION", "agents_seuil",
                             horizontal=True, filters=[DERNIERE, ACTIF]),
    }


LAYOUT = [
    [("kpi_cessions", 3, 26), ("kpi_mensualites", 3, 26), ("kpi_taux", 3, 26), ("kpi_seuil", 3, 26)],
    [("ces_famille", 5, 60), ("ces_objet", 7, 60)],
    [("ces_annee", 12, 56)],
    [("cap_tranche", 6, 56), ("cap_categorie", 6, 56)],
    [("cap_evolution", 6, 60), ("cap_direction", 6, 60)],
]

FILTERS = [
    Filter("Année", "ANNEE", "ces", exclude=["kpi_cessions", "kpi_mensualites", "kpi_taux", "kpi_seuil",
                                              "ces_famille", "ces_objet", "cap_tranche", "cap_categorie",
                                              "cap_direction"]),
    Filter("Famille de cession", "FAMILLE_CESSION", "ces"),
    Filter("Pôle", "POLE", "ces"),
    Filter("Direction", "DIRECTION", "ces"),
    Filter("Catégorie", "CATEGORIE", "ces"),
    Filter("Sexe", "SEXE", "ces"),
]
