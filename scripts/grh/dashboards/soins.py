from grh_builder import Dataset, Filter, Metric, bar, big_number, pie, simple_filter, timeseries

KEY = "soins"
TITLE = "Couverture médicale"
SLUG = "couverture-medicale"

MONTANT = ",.0f"

DATASETS = [
    Dataset("bs", "v_grh_soins", "soins.sql", [
        Metric("bulletins", "COUNT(*)", "Bulletins de soins"),
        Metric("frais_engages", "SUM(FRAIS_ENGAGES)", "Frais engagés", MONTANT),
        Metric("montant_rembourse", "SUM(MONTANT_REMBOURSE)", "Montant remboursé", MONTANT),
        Metric("taux_remboursement", "SUM(MONTANT_REMBOURSE) / NULLIF(SUM(FRAIS_ENGAGES), 0)",
               "Taux de remboursement", ".1%"),
        Metric("delai_moyen", "AVG(DELAI_RECEPTION)", "Délai moyen soins → réception (jours)", ",.1f"),
        Metric("agents_beneficiaires", "COUNT(DISTINCT MAT_PERS)", "Agents bénéficiaires"),
    ], main_dttm_col="DAT_SOINS"),
    Dataset("acte", "v_grh_soins_actes", "soins_actes.sql", [
        Metric("actes", "COUNT(*)", "Actes"),
        Metric("rembourse_actes", "SUM(MONTANT_REMBOURSE)", "Montant remboursé", MONTANT),
        Metric("frais_actes", "SUM(FRAIS_ENGAGES)", "Frais engagés", MONTANT),
    ], main_dttm_col="DAT_ACTE"),
]

DOUZE_MOIS = simple_filter("DERNIER_12_MOIS", "==", 1)


def charts(ds):
    return {
        "kpi_bulletins": big_number("bs", "Bulletins de soins", "bulletins", "12 derniers mois de données",
                                    filters=[DOUZE_MOIS]),
        "kpi_frais": big_number("bs", "Frais engagés", "frais_engages", "12 derniers mois (DT)", MONTANT,
                                filters=[DOUZE_MOIS]),
        "kpi_rembourse": big_number("bs", "Montant remboursé", "montant_rembourse", "12 derniers mois (DT)",
                                    MONTANT, filters=[DOUZE_MOIS]),
        "kpi_taux": big_number("bs", "Taux de remboursement", "taux_remboursement", "12 derniers mois", ".1%",
                               filters=[DOUZE_MOIS]),
        "evolution": timeseries("bs", "Frais engagés et remboursés par année", "DAT_SOINS",
                                ["frais_engages", "montant_rembourse"], stack=False, fmt=MONTANT),
        "beneficiaire": pie("bs", "Remboursements par bénéficiaire (12 mois)", "BENEFICIAIRE", "montant_rembourse",
                            filters=[DOUZE_MOIS], fmt=MONTANT),
        "actes": bar("acte", "Montant remboursé par type d'acte (12 mois)", "TYPE_ACTE", "rembourse_actes",
                     horizontal=True, filters=[DOUZE_MOIS], fmt=MONTANT),
        "actes_annee": timeseries("acte", "Remboursements par type d'acte et par année", "DAT_ACTE",
                                  "rembourse_actes", ["TYPE_ACTE"], fmt=MONTANT),
        "direction": bar("bs", "Montant remboursé par direction (12 mois)", "DIRECTION", "montant_rembourse",
                         horizontal=True, filters=[DOUZE_MOIS], fmt=MONTANT),
        "etat": pie("bs", "Bulletins par état (12 mois)", "ETAT", "bulletins", filters=[DOUZE_MOIS]),
        "delai": timeseries("bs", "Délai moyen entre soins et réception (jours)", "DAT_SOINS", "delai_moyen",
                            kind="line", fmt=",.1f"),
        "age": bar("bs", "Montant remboursé par tranche d'âge de l'agent (12 mois)", "TRANCHE_AGE",
                   "montant_rembourse", sort_by_metric=False, filters=[DOUZE_MOIS], fmt=MONTANT),
    }


LAYOUT = [
    [("kpi_bulletins", 3, 26), ("kpi_frais", 3, 26), ("kpi_rembourse", 3, 26), ("kpi_taux", 3, 26)],
    [("evolution", 8, 60), ("beneficiaire", 4, 60)],
    [("actes", 5, 64), ("actes_annee", 7, 64)],
    [("direction", 7, 64), ("etat", 5, 64)],
    [("delai", 6, 50), ("age", 6, 50)],
]

FILTERS = [
    Filter("Année", "ANNEE", "bs", exclude=["kpi_bulletins", "kpi_frais", "kpi_rembourse", "kpi_taux",
                                             "beneficiaire", "actes", "direction", "etat", "age"]),
    Filter("Bénéficiaire", "BENEFICIAIRE", "bs"),
    Filter("Type d'acte", "TYPE_ACTE", "acte"),
    Filter("Pôle", "POLE", "bs"),
    Filter("Direction", "DIRECTION", "bs"),
    Filter("Catégorie", "CATEGORIE", "bs"),
    Filter("Sexe", "SEXE", "bs"),
]
