from grh_builder import Dataset, Filter, Metric, bar, big_number, pie, simple_filter, table, timeseries

KEY = "formation"
TITLE = "Formation"
SLUG = "formation"

DATASETS = [
    Dataset("act", "v_grh_formation_actions", "formation_actions.sql", [
        Metric("nb_actions", "COUNT(*)", "Actions de formation"),
        Metric("heures", "SUM(HEURES)", "Heures de formation", ",.0f"),
        Metric("cout", "SUM(COUT)", "Coût TTC (DT)", ",.0f"),
        Metric("cout_moyen", "SUM(COUT) / NULLIF(COUNT(*), 0)", "Coût moyen par action (DT)", ",.0f"),
        Metric("participants", "SUM(PARTICIPANTS)", "Participations"),
    ], main_dttm_col="DAT_DEB_ACTION"),
    Dataset("part", "v_grh_formation_participants", "formation_participants.sql", [
        Metric("participations", "COUNT(*)", "Participations"),
        Metric("agents_formes", "COUNT(DISTINCT MAT_PERS)", "Agents formés"),
        Metric("heures_stagiaire", "SUM(HEURES)", "Heures stagiaires", ",.0f"),
    ], main_dttm_col="DAT_DEB_ACTION"),
]

DERNIERE_ANNEE = simple_filter("DERNIERE_ANNEE", "==", 1)


def charts(ds):
    return {
        "kpi_actions": big_number("act", "Actions (dernière année)", "nb_actions", "dernière année de formation",
                                  filters=[DERNIERE_ANNEE]),
        "kpi_heures": big_number("act", "Heures (dernière année)", "heures", "heures de formation", ",.0f",
                                 [DERNIERE_ANNEE]),
        "kpi_agents": big_number("part", "Agents formés (dernière année)", "agents_formes", "agents distincts",
                                 filters=[DERNIERE_ANNEE]),
        "kpi_cout": big_number("act", "Coût (dernière année)", "cout", "DT TTC", ",.0f", [DERNIERE_ANNEE]),
        "evolution": timeseries("act", "Actions de formation par année", "DAT_DEB_ACTION", "nb_actions",
                                ["CATEGORIE_FORMATION"]),
        "cout_annuel": timeseries("act", "Coût de la formation par année (DT)", "DAT_DEB_ACTION", "cout",
                                  kind="line", fmt=",.0f"),
        "domaines": bar("act", "Heures par domaine", "DOMAINE", "heures", horizontal=True, fmt=",.0f", limit=20),
        "nature": pie("act", "Actions par nature", "NATURE", "nb_actions"),
        "categorie": pie("act", "Actions par catégorie de formation", "CATEGORIE_FORMATION", "nb_actions"),
        "direction": bar("part", "Agents formés par direction", "DIRECTION", "agents_formes", horizontal=True),
        "sexe": pie("part", "Participations par sexe", "SEXE", "participations"),
        "cat_pers": bar("part", "Heures stagiaires par catégorie de personnel", "CATEGORIE", "heures_stagiaire",
                        fmt=",.0f"),
        "liste": table("act", "Liste des actions de formation", [
            "ANNEE", "INTITULE", "DOMAINE", "CATEGORIE_FORMATION", "DAT_DEB_ACTION", "DAT_FIN_ACTION",
            "HEURES", "PARTICIPANTS", "LIEU", "COUT",
        ], "DAT_DEB_ACTION", ascending=False),
    }


LAYOUT = [
    [("kpi_actions", 3, 26), ("kpi_heures", 3, 26), ("kpi_agents", 3, 26), ("kpi_cout", 3, 26)],
    [("evolution", 8, 60), ("cout_annuel", 4, 60)],
    [("domaines", 6, 70), ("nature", 3, 70), ("categorie", 3, 70)],
    [("direction", 6, 64), ("sexe", 3, 64), ("cat_pers", 3, 64)],
    [("liste", 12, 70)],
]

KPIS = ["kpi_actions", "kpi_heures", "kpi_agents", "kpi_cout"]

FILTERS = [
    Filter("Année", "ANNEE", "act", exclude=KPIS),
    Filter("Catégorie de formation", "CATEGORIE_FORMATION", "act"),
    Filter("Domaine", "DOMAINE", "act"),
    Filter("Nature", "NATURE", "act"),
    Filter("Direction", "DIRECTION", "part"),
    Filter("Sexe", "SEXE", "part"),
]
