from grh_builder import Dataset, Filter, Metric, bar, big_number, pie, simple_filter, timeseries

KEY = "presence"
TITLE = "Présence et ponctualité"
SLUG = "presence-ponctualite"

DATASETS = [
    Dataset("ret", "v_grh_retards", "retards.sql", [
        Metric("retards", "COUNT(*)", "Retards"),
        Metric("minutes_retard", "SUM(MINUTES_RETARD)", "Minutes de retard", ",.0f"),
        Metric("retard_moyen", "AVG(MINUTES_RETARD)", "Durée moyenne d'un retard (min)", ",.0f"),
        Metric("agents_retard", "COUNT(DISTINCT MAT_PERS)", "Agents concernés"),
    ], main_dttm_col="DAT_POINT"),
    Dataset("aut", "v_grh_autorisations_sortie", "autorisations_sortie.sql", [
        Metric("autorisations", "COUNT(*)", "Autorisations de sortie"),
        Metric("heures_sortie", "SUM(MINUTES_SORTIE) / 60", "Heures de sortie", ",.0f"),
    ], main_dttm_col="DAT_DEBUT_AUT"),
    Dataset("pt", "v_grh_pointages", "pointages.sql", [
        Metric("agents_pointes", "COUNT(DISTINCT MAT_PERS)", "Agents ayant pointé"),
        Metric("presence_moyenne", "AVG(HEURES_PRESENCE)", "Présence moyenne par jour (h)", ",.2f"),
        Metric("arrivee_moyenne", "AVG(ARRIVEE_MIN) / 60", "Heure moyenne d'arrivée", ",.2f"),
    ], main_dttm_col="JOUR"),
]

DOUZE_MOIS = simple_filter("DERNIER_12_MOIS", "==", 1)
VALIDEES = simple_filter("ETAT", "==", "Validée")


def charts(ds):
    return {
        "kpi_retards": big_number("ret", "Retards", "retards", "12 derniers mois de pointage", filters=[DOUZE_MOIS]),
        "kpi_moyen": big_number("ret", "Durée moyenne d'un retard", "retard_moyen", "minutes, 12 mois", ",.0f",
                                filters=[DOUZE_MOIS]),
        "kpi_agents": big_number("ret", "Agents en retard", "agents_retard", "au moins une fois en 12 mois",
                                 filters=[DOUZE_MOIS]),
        "kpi_aut": big_number("aut", "Autorisations de sortie", "autorisations", "validées, 12 derniers mois",
                              filters=[DOUZE_MOIS, VALIDEES]),
        "ret_mois": bar("ret", "Retards par mois et par durée", "MOIS", "retards", ["TRANCHE_RETARD"],
                        sort_by_metric=False, stack=True),
        "ret_tranche": pie("ret", "Retards par durée", "TRANCHE_RETARD", "retards"),
        "ret_jour": bar("ret", "Retards par jour de la semaine", "JOUR_SEMAINE", "retards", sort_by_metric=False),
        "ret_heure": bar("ret", "Retards par heure d'arrivée", "HEURE_ARRIVEE", "retards", sort_by_metric=False),
        "ret_direction": bar("ret", "Minutes de retard par direction", "DIRECTION", "minutes_retard",
                             horizontal=True, fmt=",.0f"),
        "ret_service": bar("ret", "Top 15 des services par minutes de retard", "SERVICE", "minutes_retard",
                           horizontal=True, fmt=",.0f", limit=15),
        "pt_jour": timeseries("pt", "Agents ayant pointé par jour", "JOUR", "agents_pointes", grain="P1D",
                              kind="line"),
        "pt_presence": bar("pt", "Présence moyenne par jour, par mois (h)", "MOIS", "presence_moyenne",
                           sort_by_metric=False, fmt=",.2f"),
        "aut_annee": timeseries("aut", "Autorisations de sortie par année et état", "DAT_DEBUT_AUT",
                                "autorisations", ["ETAT"]),
        "aut_heure": bar("aut", "Autorisations par heure de sortie", "HEURE_SORTIE", "autorisations",
                         sort_by_metric=False, filters=[VALIDEES]),
    }


LAYOUT = [
    [("kpi_retards", 3, 26), ("kpi_moyen", 3, 26), ("kpi_agents", 3, 26), ("kpi_aut", 3, 26)],
    [("ret_mois", 8, 60), ("ret_tranche", 4, 60)],
    [("ret_jour", 6, 50), ("ret_heure", 6, 50)],
    [("ret_direction", 6, 70), ("ret_service", 6, 70)],
    [("pt_jour", 7, 56), ("pt_presence", 5, 56)],
    [("aut_annee", 7, 56), ("aut_heure", 5, 56)],
]

FILTERS = [
    Filter("Année", "ANNEE", "ret", exclude=["kpi_retards", "kpi_moyen", "kpi_agents", "kpi_aut"]),
    Filter("Pôle", "POLE", "ret"),
    Filter("Direction", "DIRECTION", "ret"),
    Filter("Service", "SERVICE", "ret"),
    Filter("Catégorie", "CATEGORIE", "ret"),
    Filter("Sexe", "SEXE", "ret"),
]
