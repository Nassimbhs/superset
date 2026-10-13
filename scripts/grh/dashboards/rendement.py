from grh_builder import Dataset, Filter, Metric, bar, big_number, pie, simple_filter, timeseries

KEY = "rendement"
TITLE = "Évaluation et rendement"
SLUG = "evaluation-rendement"

NOTE = ",.2f"

DATASETS = [
    Dataset("note", "v_grh_notes_rendement", "notes_rendement.sql", [
        Metric("note_moyenne", "AVG(NOTE_DEFINITIVE)", "Note moyenne (/20)", NOTE),
        Metric("agents_notes", "COUNT(DISTINCT MAT_PERS)", "Agents notés"),
        Metric("notes", "COUNT(*)", "Notes"),
        Metric("part_excellence", "SUM(CASE WHEN NOTE_DEFINITIVE >= 19 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0)",
               "Part des notes ≥ 19", ".1%"),
        Metric("taux_promotion",
               "SUM(CASE WHEN PROMOTION_SUIVANTE LIKE 'Promu%' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0)",
               "Taux de promotion l'année suivante", ".1%"),
        Metric("note_assiduite", "AVG(NOTE_ASSIDUITE)", "Note d'assiduité moyenne", NOTE),
        Metric("note_maladie", "AVG(NOTE_MALADIE)", "Note congé de maladie moyenne", NOTE),
    ], main_dttm_col="DAT_NOTE"),
]

DERNIERE = simple_filter("DERNIERE_ANNEE", "==", 1)
PRECEDENTE = simple_filter("ANNEE_PRECEDENTE", "==", 1)


def charts(ds):
    return {
        "kpi_moyenne": big_number("note", "Note moyenne", "note_moyenne", "dernière campagne (/20)", NOTE,
                                  filters=[DERNIERE]),
        "kpi_precedente": big_number("note", "Note moyenne N-1", "note_moyenne", "campagne précédente (/20)", NOTE,
                                     filters=[PRECEDENTE]),
        "kpi_agents": big_number("note", "Agents notés", "agents_notes", "dernière campagne", filters=[DERNIERE]),
        "kpi_excellence": big_number("note", "Notes ≥ 19", "part_excellence", "dernière campagne", ".1%",
                                     filters=[DERNIERE]),
        "distribution": bar("note", "Distribution des notes par campagne", "ANNEE", "notes", ["TRANCHE_NOTE"],
                            sort_by_metric=False, stack=True),
        "tranches": pie("note", "Répartition des notes (dernière campagne)", "TRANCHE_NOTE", "notes",
                        filters=[DERNIERE]),
        "evolution": timeseries("note", "Évolution de la note moyenne", "DAT_NOTE",
                                "note_moyenne", kind="line", fmt=NOTE),
        "criteres": timeseries("note", "Notes d'assiduité et de congé maladie (/4)", "DAT_NOTE",
                               ["note_assiduite", "note_maladie"], kind="line", stack=False, fmt=NOTE),
        "direction": bar("note", "Note moyenne par direction (dernière campagne)", "DIRECTION", "note_moyenne",
                         horizontal=True, filters=[DERNIERE], fmt=NOTE),
        "categorie": bar("note", "Note moyenne par catégorie et sexe (dernière campagne)", "CATEGORIE",
                         "note_moyenne", ["SEXE"], filters=[DERNIERE], fmt=NOTE),
        "promotion": bar("note", "Taux de promotion l'année suivante selon la note", "TRANCHE_NOTE",
                         "taux_promotion", sort_by_metric=False, fmt=".1%"),
        "anciennete": bar("note", "Note moyenne par ancienneté (dernière campagne)", "TRANCHE_ANCIENNETE",
                          "note_moyenne", sort_by_metric=False, filters=[DERNIERE], fmt=NOTE),
    }


LAYOUT = [
    [("kpi_moyenne", 3, 26), ("kpi_precedente", 3, 26), ("kpi_agents", 3, 26), ("kpi_excellence", 3, 26)],
    [("distribution", 8, 60), ("tranches", 4, 60)],
    [("evolution", 6, 50), ("criteres", 6, 50)],
    [("direction", 7, 70), ("categorie", 5, 70)],
    [("promotion", 6, 50), ("anciennete", 6, 50)],
]

FILTERS = [
    Filter("Campagne", "ANNEE", "note", exclude=["kpi_moyenne", "kpi_precedente", "kpi_agents", "kpi_excellence",
                                                  "tranches", "direction", "categorie", "anciennete"]),
    Filter("Pôle", "POLE", "note"),
    Filter("Direction", "DIRECTION", "note"),
    Filter("Catégorie", "CATEGORIE", "note"),
    Filter("Sexe", "SEXE", "note"),
    Filter("Tranche d'âge", "TRANCHE_AGE", "note"),
]
