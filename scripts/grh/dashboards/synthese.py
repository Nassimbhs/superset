from grh_builder import (
    Dataset, Filter, Metric, TimeFilter, bar, big_number, pie, simple_filter, sql_filter, timeseries,
)

KEY = "synthese"
TITLE = "Tableau de bord RH"
SLUG = "tableau-de-bord-rh"

MONTANT = ",.0f"
EFFECTIF_MOYEN = "NULLIF(COUNT(*) / NULLIF(COUNT(DISTINCT DT_MOIS), 0), 0)"

DATASETS = [
    Dataset("mens", "v_grh_effectif_mensuel", "effectif_mensuel.sql", [
        Metric("effectif", "COUNT(DISTINCT MAT_PERS)", "Effectif payé"),
        Metric("entrees", "SUM(ENTREE)", "Entrées"),
        Metric("sorties", "SUM(SORTIE)", "Sorties"),
        Metric("turnover", f"(SUM(ENTREE) + SUM(SORTIE)) / 2 / {EFFECTIF_MOYEN}", "Taux de turnover", ".1%"),
        Metric("retention", "SUM(RETENU) / NULLIF(SUM(REF_M12), 0)", "Taux de rétention (12 mois)", ".1%"),
        Metric("taux_encadrement", "SUM(EST_RESPONSABLE) / NULLIF(COUNT(*), 0)", "Taux d'encadrement", ".1%"),
        Metric("responsables", "SUM(EST_RESPONSABLE)", "Responsables"),
        Metric("pct_femmes_resp", "SUM(RESPONSABLE_FEMME) / NULLIF(SUM(EST_RESPONSABLE), 0)",
               "% de femmes parmi les responsables", ".1%"),
        Metric("masse_brute", "SUM(BRUT)", "Masse salariale brute", MONTANT),
        Metric("cout_employeur", "SUM(COUT_EMPLOYEUR)", "Coût employeur (brut + charges)", MONTANT),
        Metric("cout_moyen", "SUM(COUT_EMPLOYEUR) / NULLIF(COUNT(*), 0)", "Coût employeur moyen par agent", MONTANT),
    ], main_dttm_col="DT_MOIS"),
    Dataset("absg", "v_grh_absenteisme_global", "absenteisme_global.sql", [
        Metric("jours_absence", "SUM(JOURS_ABSENCE)", "Jours d'absence", ",.0f"),
        Metric("taux_absenteisme", "SUM(JOURS_ABSENCE) / NULLIF(SUM(JOURS_THEORIQUES), 0)",
               "Taux d'absentéisme global", ".2%"),
    ], main_dttm_col="DT_MOIS"),
]

DERNIER_MOIS = simple_filter("DERNIER_MOIS", "==", 1)
DOUZE_MOIS = simple_filter("DOUZE_MOIS", "==", 1)
HORS_THEORIQUE = sql_filter("NATURE_ABSENCE <> 'Jours théoriques'")


def charts(ds):
    return {
        "kpi_effectif": big_number("mens", "Effectif payé", "effectif", "dernier mois de paie",
                                   filters=[DERNIER_MOIS]),
        "kpi_entrees": big_number("mens", "Entrées", "entrees", "12 derniers mois de paie", filters=[DOUZE_MOIS]),
        "kpi_sorties": big_number("mens", "Sorties", "sorties", "12 derniers mois de paie", filters=[DOUZE_MOIS]),
        "kpi_turnover": big_number("mens", "Taux de turnover", "turnover",
                                   "(entrées + sorties) / 2 / effectif moyen, 12 mois", ".1%", [DOUZE_MOIS]),
        "kpi_retention": big_number("mens", "Taux de rétention", "retention",
                                    "agents payés il y a 12 mois et encore payés", ".1%"),
        "kpi_encadrement": big_number("mens", "Taux d'encadrement", "taux_encadrement",
                                      "agents avec fonction / effectif payé", ".1%", [DERNIER_MOIS]),
        "kpi_masse": big_number("mens", "Masse salariale brute", "masse_brute", "paie mensuelle, 12 mois (DT)",
                                MONTANT, [DOUZE_MOIS]),
        "kpi_cout_moyen": big_number("mens", "Coût employeur moyen", "cout_moyen",
                                     "par agent, dernier mois (DT)", MONTANT, [DERNIER_MOIS]),
        "kpi_absenteisme": big_number("absg", "Taux d'absentéisme global", "taux_absenteisme",
                                      "maladie, maternité, exceptionnels, sanctions — 12 mois", ".2%", [DOUZE_MOIS]),
        "kpi_femmes_resp": big_number("mens", "Femmes parmi les responsables", "pct_femmes_resp",
                                      "dernier mois de paie", ".1%", [DERNIER_MOIS]),
        "effectif_mois": timeseries("mens", "Évolution mensuelle de l'effectif payé", "DT_MOIS", "effectif",
                                    grain="P1M", kind="line"),
        "flux_mois": timeseries("mens", "Entrées et sorties par mois", "DT_MOIS", ["entrees", "sorties"],
                                grain="P1M", stack=False),
        "masse_mois": timeseries("mens", "Masse brute et coût employeur par mois (DT)", "DT_MOIS",
                                 ["masse_brute", "cout_employeur"], grain="P1M", kind="line", fmt=MONTANT),
        "cout_moyen_mois": timeseries("mens", "Coût employeur moyen par agent et par mois (DT)", "DT_MOIS",
                                      "cout_moyen", grain="P1M", kind="line", fmt=MONTANT),
        "absenteisme_mois": timeseries("absg", "Taux d'absentéisme global par mois", "DT_MOIS",
                                       "taux_absenteisme", grain="P1M", kind="line", fmt=".2%"),
        "absences_nature": timeseries("absg", "Jours d'absence par nature et par mois", "DT_MOIS",
                                      "jours_absence", ["NATURE_ABSENCE"], grain="P1M",
                                      filters=[HORS_THEORIQUE], fmt=",.0f"),
        "encadrement_direction": bar("mens", "Taux d'encadrement par direction", "DIRECTION",
                                     "taux_encadrement", horizontal=True, filters=[DERNIER_MOIS], fmt=".1%"),
        "responsables_sexe": pie("mens", "Responsables par sexe", "SEXE", "responsables", [DERNIER_MOIS]),
        "turnover_direction": bar("mens", "Taux de turnover par direction (12 mois)", "DIRECTION", "turnover",
                                  horizontal=True, filters=[DOUZE_MOIS], fmt=".1%"),
    }


LAYOUT = [
    [("kpi_effectif", 2, 26), ("kpi_entrees", 2, 26), ("kpi_sorties", 2, 26),
     ("kpi_turnover", 2, 26), ("kpi_retention", 2, 26), ("kpi_encadrement", 2, 26)],
    [("kpi_masse", 3, 26), ("kpi_cout_moyen", 3, 26), ("kpi_absenteisme", 3, 26), ("kpi_femmes_resp", 3, 26)],
    [("effectif_mois", 6, 56), ("flux_mois", 6, 56)],
    [("masse_mois", 6, 56), ("cout_moyen_mois", 6, 56)],
    [("absenteisme_mois", 6, 56), ("absences_nature", 6, 56)],
    [("encadrement_direction", 5, 70), ("responsables_sexe", 3, 70), ("turnover_direction", 4, 70)],
]

MENSUELS = ["effectif_mois", "flux_mois", "masse_mois", "cout_moyen_mois", "absenteisme_mois", "absences_nature"]

FILTERS = [
    Filter("Pôle", "POLE", "mens"),
    Filter("Direction", "DIRECTION", "mens"),
    Filter("Catégorie", "CATEGORIE", "mens"),
    Filter("Sexe", "SEXE", "mens"),
    TimeFilter("Période (graphiques mensuels)", MENSUELS),
]
