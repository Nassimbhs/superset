from grh_builder import Dataset, Filter, Metric, bar, big_number, pie, simple_filter, sql_filter

KEY = "social"
TITLE = "Œuvres sociales"
SLUG = "oeuvres-sociales"

MONTANT = ",.0f"

DATASETS = [
    Dataset("don", "v_grh_dons", "dons.sql", [
        Metric("demandes", "COUNT(*)", "Demandes"),
        Metric("montant_accorde", "SUM(MONTANT_ACCORDE)", "Montant accordé", MONTANT),
        Metric("montant_demande", "SUM(MONTANT_DEMANDE)", "Montant demandé", MONTANT),
        Metric("taux_acceptation", "SUM(ACCORDEE) / NULLIF(COUNT(*), 0)", "Taux d'acceptation", ".1%"),
        Metric("beneficiaires", "COUNT(DISTINCT MAT_PERS)", "Agents bénéficiaires"),
        Metric("don_moyen", "SUM(MONTANT_ACCORDE) / NULLIF(COUNT(DISTINCT MAT_PERS), 0)",
               "Montant moyen par agent", MONTANT),
    ], main_dttm_col="DAT_DEM_DON"),
    Dataset("sco", "v_grh_scolarite", "scolarite.sql", [
        Metric("primes", "COUNT(*)", "Primes de scolarité (enfants)"),
        Metric("montant_scolarite", "SUM(MONTANT_PRIME)", "Montant des primes de scolarité", MONTANT),
        Metric("agents_scolarite", "COUNT(DISTINCT MAT_PERS)", "Agents bénéficiaires"),
    ], main_dttm_col="DAT_DEM_PRIME_S"),
]

ANNEE_COURANTE = sql_filter("ANNEE = TO_CHAR(SYSDATE, 'YYYY')")


def charts(ds):
    return {
        "kpi_dons": big_number("don", "Aides et dons accordés", "montant_accorde", "année en cours (DT)", MONTANT,
                               filters=[ANNEE_COURANTE]),
        "kpi_benef": big_number("don", "Agents bénéficiaires", "beneficiaires", "dons, année en cours",
                                filters=[ANNEE_COURANTE]),
        "kpi_sco": big_number("sco", "Primes de scolarité", "montant_scolarite", "année scolaire en cours (DT)",
                              MONTANT, filters=[ANNEE_COURANTE]),
        "kpi_enfants": big_number("sco", "Enfants bénéficiaires", "primes", "année scolaire en cours",
                                  filters=[ANNEE_COURANTE]),
        "dons_annee": bar("don", "Montant accordé par année et par nature", "ANNEE", "montant_accorde",
                          ["NATURE_DON"], sort_by_metric=False, stack=True, fmt=MONTANT),
        "dons_nature": pie("don", "Répartition des dons par nature", "NATURE_DON", "montant_accorde", fmt=MONTANT),
        "dons_etat": bar("don", "Demandes par année et par état", "ANNEE", "demandes", ["ETAT"],
                         sort_by_metric=False, stack=True),
        "dons_categorie": bar("don", "Montant moyen par agent et par catégorie", "CATEGORIE", "don_moyen",
                              fmt=MONTANT),
        "sco_annee": bar("sco", "Primes de scolarité par année scolaire", "ANNEE", "montant_scolarite",
                         sort_by_metric=False, fmt=MONTANT),
        "sco_niveau": bar("sco", "Enfants bénéficiaires par niveau estimé (âge)", "NIVEAU_ESTIME", "primes",
                          ["ANNEE"], sort_by_metric=False, stack=True),
        "sco_direction": bar("sco", "Primes de scolarité par direction", "DIRECTION", "montant_scolarite",
                             horizontal=True, fmt=MONTANT),
    }


LAYOUT = [
    [("kpi_dons", 3, 26), ("kpi_benef", 3, 26), ("kpi_sco", 3, 26), ("kpi_enfants", 3, 26)],
    [("dons_annee", 8, 60), ("dons_nature", 4, 60)],
    [("dons_etat", 7, 56), ("dons_categorie", 5, 56)],
    [("sco_annee", 6, 56), ("sco_niveau", 6, 56)],
    [("sco_direction", 12, 64)],
]

FILTERS = [
    Filter("Année", "ANNEE", "don", exclude=["kpi_dons", "kpi_benef", "kpi_sco", "kpi_enfants"]),
    Filter("Nature du don", "NATURE_DON", "don"),
    Filter("Pôle", "POLE", "don"),
    Filter("Direction", "DIRECTION", "don"),
    Filter("Catégorie", "CATEGORIE", "don"),
    Filter("Sexe", "SEXE", "don"),
]
