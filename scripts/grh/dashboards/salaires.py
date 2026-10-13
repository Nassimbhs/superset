from grh_builder import (
    Dataset, Filter, Metric, bar, big_number, pie, simple_filter, sql_filter, timeseries,
)

KEY = "salaires"
TITLE = "Salaires et masse salariale"
SLUG = "salaires"

MONTANT = ",.0f"

DATASETS = [
    Dataset("paie", "v_grh_paie", "paie.sql", [
        Metric("masse_brute", "SUM(BRUT)", "Masse salariale brute", MONTANT),
        Metric("cout_employeur", "SUM(COUT_EMPLOYEUR)", "Coût employeur (brut + charges)", MONTANT),
        Metric("charges_patronales", "SUM(CHARGES_PATRONALES)", "Charges patronales", MONTANT),
        Metric("net_a_payer", "SUM(NET_A_PAYER)", "Net à payer", MONTANT),
        Metric("salaire_base", "SUM(SALAIRE_BASE)", "Salaire de base", MONTANT),
        Metric("indemnites_mensuelles", "SUM(INDEMNITES_MENSUELLES)", "Primes et indemnités mensuelles", MONTANT),
        Metric("retenues_salariales", "SUM(COTISATIONS_SALARIALES)", "Cotisations salariales", MONTANT),
        Metric("impot", "SUM(IMPOT)", "Impôt et CSS", MONTANT),
        Metric("salaire_moyen", "SUM(BRUT) / NULLIF(COUNT(DISTINCT MAT_PERS || TO_CHAR(DT_BUL, 'YYYYMM')), 0)",
               "Salaire brut mensuel moyen", MONTANT),
        Metric("net_moyen", "SUM(NET_A_PAYER) / NULLIF(COUNT(DISTINCT MAT_PERS || TO_CHAR(DT_BUL, 'YYYYMM')), 0)",
               "Net à payer mensuel moyen", MONTANT),
        Metric("taux_charges", "SUM(CHARGES_PATRONALES) / NULLIF(SUM(BRUT), 0)", "Taux de charges patronales", ".1%"),
        Metric("agents_payes", "COUNT(DISTINCT MAT_PERS)", "Agents payés"),
    ], main_dttm_col="DT_BUL"),
]

PAIE_MENSUELLE = simple_filter("COD_TYP_BUL", "==", "BN")
DOUZE_MOIS = simple_filter("DERNIER_12_MOIS", "==", 1)
DERNIER_MOIS = simple_filter("DERNIER_MOIS", "==", 1)
TROIS_ANS = sql_filter("DT_BUL >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -36)")


def charts(ds):
    return {
        "kpi_masse": big_number("paie", "Masse salariale brute", "masse_brute", "12 derniers mois (DT)", MONTANT,
                                filters=[DOUZE_MOIS]),
        "kpi_cout": big_number("paie", "Coût employeur total", "cout_employeur",
                               "12 derniers mois, brut + charges (DT)", MONTANT, filters=[DOUZE_MOIS]),
        "kpi_moyen": big_number("paie", "Salaire brut mensuel moyen", "salaire_moyen",
                                "dernier mois de paie (DT)", MONTANT, filters=[PAIE_MENSUELLE, DERNIER_MOIS]),
        "kpi_net": big_number("paie", "Net mensuel moyen", "net_moyen", "dernier mois de paie (DT)", MONTANT,
                              filters=[PAIE_MENSUELLE, DERNIER_MOIS]),
        "evolution": timeseries("paie", "Masse salariale brute par année et famille", "DT_BUL", "masse_brute",
                                ["FAMILLE_REMUNERATION"], fmt=MONTANT),
        "familles": pie("paie", "Répartition de la masse brute (12 mois)", "FAMILLE_REMUNERATION", "masse_brute",
                        filters=[DOUZE_MOIS], fmt=MONTANT),
        "mensuel": timeseries("paie", "Paie mensuelle : base et indemnités (36 mois)", "DT_BUL",
                              ["salaire_base", "indemnites_mensuelles"], grain="P1M",
                              filters=[PAIE_MENSUELLE, TROIS_ANS], fmt=MONTANT),
        "partage": timeseries("paie", "Partage du coût employeur par année", "DT_BUL",
                              ["net_a_payer", "retenues_salariales", "impot", "charges_patronales"],
                              fmt=MONTANT),
        "direction": bar("paie", "Masse salariale brute par direction (12 mois)", "DIRECTION", "masse_brute",
                         horizontal=True, filters=[DOUZE_MOIS], fmt=MONTANT),
        "categorie": bar("paie", "Salaire brut mensuel moyen par catégorie et sexe", "CATEGORIE", "salaire_moyen",
                         ["SEXE"], filters=[PAIE_MENSUELLE, DERNIER_MOIS], fmt=MONTANT),
        "grade": bar("paie", "Salaire brut mensuel moyen par grade", "GRADE", "salaire_moyen",
                     horizontal=True, filters=[PAIE_MENSUELLE, DERNIER_MOIS], fmt=MONTANT),
        "anciennete": bar("paie", "Salaire brut mensuel moyen par ancienneté", "TRANCHE_ANCIENNETE", "salaire_moyen",
                          sort_by_metric=False, filters=[PAIE_MENSUELLE, DERNIER_MOIS], fmt=MONTANT),
        "moyen_annee": timeseries("paie", "Évolution du salaire brut mensuel moyen", "DT_BUL", "salaire_moyen",
                                  kind="line", filters=[PAIE_MENSUELLE], fmt=MONTANT),
    }


LAYOUT = [
    [("kpi_masse", 3, 26), ("kpi_cout", 3, 26), ("kpi_moyen", 3, 26), ("kpi_net", 3, 26)],
    [("evolution", 8, 60), ("familles", 4, 60)],
    [("mensuel", 6, 56), ("partage", 6, 56)],
    [("direction", 7, 64), ("categorie", 5, 64)],
    [("grade", 7, 70), ("anciennete", 5, 70)],
    [("moyen_annee", 12, 50)],
]

FILTERS = [
    Filter("Année", "ANNEE", "paie", exclude=["kpi_masse", "kpi_cout", "kpi_moyen", "kpi_net", "familles",
                                               "direction", "categorie", "grade", "anciennete"]),
    Filter("Famille de rémunération", "FAMILLE_REMUNERATION", "paie"),
    Filter("Type de bulletin", "TYPE_BULLETIN", "paie"),
    Filter("Pôle", "POLE", "paie"),
    Filter("Direction", "DIRECTION", "paie"),
    Filter("Catégorie", "CATEGORIE", "paie"),
    Filter("Sexe", "SEXE", "paie"),
]
