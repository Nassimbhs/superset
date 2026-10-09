from grh_builder import Dataset, Filter, Metric, bar, big_number, simple_filter, summary_table

KEY = "budget"
TITLE = "Budget et réalisé de la masse salariale"
SLUG = "budget-masse-salariale"

MONTANT = ",.0f"

DATASETS = [
    Dataset("bud", "v_grh_budget", "budget.sql", [
        Metric("budget", "SUM(BUDGET)", "Budget", MONTANT),
        Metric("realise", "SUM(REALISE)", "Réalisé (paie)", MONTANT),
        Metric("ecart", "SUM(REALISE) - SUM(BUDGET)", "Écart réalisé - budget", MONTANT),
        Metric("taux_realisation", "SUM(REALISE) / NULLIF(SUM(BUDGET), 0)", "Taux de réalisation", ".1%"),
    ]),
]

DERNIERE_ANNEE = simple_filter("DERNIERE_ANNEE", "==", 1)
RUBRIQUES_PAIE = simple_filter("RUBRIQUE_PAIE", "==", 1)


def charts(ds):
    return {
        "kpi_budget": big_number("bud", "Budget de la masse salariale", "budget", "dernier exercice budgété",
                                 MONTANT, filters=[DERNIERE_ANNEE]),
        "kpi_realise": big_number("bud", "Réalisé", "realise", "dernier exercice, d'après la paie", MONTANT,
                                  filters=[DERNIERE_ANNEE]),
        "kpi_ecart": big_number("bud", "Écart sur rubriques de paie", "ecart", "réalisé - budget", MONTANT,
                                filters=[DERNIERE_ANNEE, RUBRIQUES_PAIE]),
        "kpi_taux": big_number("bud", "Taux de réalisation", "taux_realisation", "rubriques rattachées à la paie",
                               ".1%", filters=[DERNIERE_ANNEE, RUBRIQUES_PAIE]),
        "annees": bar("bud", "Budget et réalisé par exercice", "ANNEE", ["budget", "realise"],
                      sort_by_metric=False, fmt=MONTANT),
        "mois": bar("bud", "Budget et réalisé par mois (dernier exercice)", "NUM_MOIS", ["budget", "realise"],
                    sort_by_metric=False, filters=[DERNIERE_ANNEE], fmt=MONTANT),
        "types": bar("bud", "Budget et réalisé par type de rubrique (dernier exercice)", "TYPE_RUBRIQUE",
                     ["budget", "realise"], horizontal=True, filters=[DERNIERE_ANNEE], fmt=MONTANT),
        "ecarts": bar("bud", "Plus forts dépassements par rubrique (dernier exercice)", "RUBRIQUE", "ecart",
                      horizontal=True, filters=[DERNIERE_ANNEE, RUBRIQUES_PAIE], fmt=MONTANT, limit=15),
        "taux_annee": bar("bud", "Taux de réalisation par exercice", "ANNEE", "taux_realisation",
                          sort_by_metric=False, filters=[RUBRIQUES_PAIE], fmt=".1%"),
        "detail": summary_table("bud", "Détail par rubrique budgétaire", ["RUBRIQUE", "TYPE_RUBRIQUE"],
                                ["budget", "realise", "ecart", "taux_realisation"]),
    }


LAYOUT = [
    [("kpi_budget", 3, 26), ("kpi_realise", 3, 26), ("kpi_ecart", 3, 26), ("kpi_taux", 3, 26)],
    [("annees", 7, 60), ("taux_annee", 5, 60)],
    [("mois", 7, 60), ("types", 5, 60)],
    [("ecarts", 12, 64)],
    [("detail", 12, 80)],
]

FILTERS = [
    Filter("Exercice", "ANNEE", "bud", exclude=["kpi_budget", "kpi_realise", "kpi_ecart", "kpi_taux"]),
    Filter("Type de rubrique", "TYPE_RUBRIQUE", "bud"),
    Filter("Rubrique budgétaire", "RUBRIQUE", "bud"),
]
