from grh_builder import Dataset, Filter, Metric, bar, big_number, pie, simple_filter

KEY = "services"
TITLE = "Services RH"
SLUG = "services-rh"

DATASETS = [
    Dataset("att", "v_grh_attestations", "attestations.sql", [
        Metric("attestations", "COUNT(*)", "Attestations éditées"),
        Metric("agents_attestation", "COUNT(DISTINCT MAT_PERS)", "Agents demandeurs"),
    ], main_dttm_col="DATE_EDITION"),
    Dataset("dem", "v_grh_demandes_service", "demandes_service.sql", [
        Metric("demandes", "COUNT(*)", "Demandes de service"),
        Metric("delai_moyen", "AVG(DELAI_REPONSE)", "Délai moyen de réponse (jours)", ",.1f"),
        Metric("en_attente", "SUM(CASE WHEN ETAT = 'En attente' THEN 1 ELSE 0 END)", "Demandes en attente"),
    ], main_dttm_col="DAT_SAISIE"),
    Dataset("int", "v_grh_interims", "interims.sql", [
        Metric("interims", "COUNT(*)", "Intérims"),
        Metric("jours_interim", "SUM(JOURS_INTERIM)", "Jours d'intérim", ",.0f"),
        Metric("remplacants", "COUNT(DISTINCT MAT_PERS_INT)", "Agents remplaçants"),
    ], main_dttm_col="DAT_DEBUT_INT"),
]

DOUZE_MOIS = simple_filter("DERNIER_12_MOIS", "==", 1)


def charts(ds):
    return {
        "kpi_att": big_number("att", "Attestations éditées", "attestations", "12 derniers mois de données",
                              filters=[DOUZE_MOIS]),
        "kpi_dem": big_number("dem", "Demandes de service", "demandes", "12 derniers mois de données",
                              filters=[DOUZE_MOIS]),
        "kpi_attente": big_number("dem", "Demandes en attente", "en_attente", "toutes périodes"),
        "kpi_int": big_number("int", "Intérims de congé", "interims", "12 derniers mois de données",
                              filters=[DOUZE_MOIS]),
        "att_annee": bar("att", "Attestations éditées par année et modèle", "ANNEE", "attestations",
                         ["MODELE_ATTESTATION"], sort_by_metric=False, stack=True),
        "att_direction": bar("att", "Attestations par direction (12 mois)", "DIRECTION", "attestations",
                             horizontal=True, filters=[DOUZE_MOIS]),
        "dem_annee": bar("dem", "Demandes de service par année et état", "ANNEE", "demandes", ["ETAT"],
                         sort_by_metric=False, stack=True),
        "dem_type": pie("dem", "Demandes par type", "TYPE_DEMANDE", "demandes"),
        "dem_delai": bar("dem", "Délai moyen de réponse par année et type (jours)", "ANNEE", "delai_moyen",
                         ["TYPE_DEMANDE"], sort_by_metric=False, fmt=",.1f"),
        "int_mois": bar("int", "Intérims par mois", "MOIS", "interims", sort_by_metric=False),
        "int_direction": bar("int", "Jours d'intérim par direction (12 mois)", "DIRECTION", "jours_interim",
                             horizontal=True, filters=[DOUZE_MOIS], fmt=",.0f"),
    }


LAYOUT = [
    [("kpi_att", 3, 26), ("kpi_dem", 3, 26), ("kpi_attente", 3, 26), ("kpi_int", 3, 26)],
    [("att_annee", 7, 60), ("att_direction", 5, 60)],
    [("dem_annee", 5, 56), ("dem_type", 3, 56), ("dem_delai", 4, 56)],
    [("int_mois", 7, 60), ("int_direction", 5, 60)],
]

FILTERS = [
    Filter("Année", "ANNEE", "att", exclude=["kpi_att", "kpi_dem", "kpi_attente", "kpi_int",
                                              "att_direction", "int_direction"]),
    Filter("Type de demande", "TYPE_DEMANDE", "dem"),
    Filter("Pôle", "POLE", "att"),
    Filter("Direction", "DIRECTION", "att"),
    Filter("Catégorie", "CATEGORIE", "att"),
    Filter("Sexe", "SEXE", "att"),
]
