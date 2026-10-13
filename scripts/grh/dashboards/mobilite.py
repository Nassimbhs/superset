from grh_builder import (
    Dataset, Filter, Metric, TimeFilter, bar, big_number, pie, sankey, simple_filter, sql_filter, table,
    timeseries,
)

KEY = "mobilite"
TITLE = "Mobilité et carrière"
SLUG = "mobilite-carriere"

DATASETS = [
    Dataset("mut", "v_grh_mutations", "mutations.sql", [
        Metric("mutations", "COUNT(*)", "Mutations"),
        Metric("agents_mutes", "COUNT(DISTINCT MAT_PERS)", "Agents mutés"),
        Metric("pct_inter_direction", "SUM(CHANGE_DIRECTION) / NULLIF(COUNT(*), 0)", "% inter-directions", ".1%"),
    ], main_dttm_col="DAT_MUT"),
    Dataset("dem", "v_grh_demandes_mutation", "demandes_mutation.sql", [
        Metric("demandes", "COUNT(*)", "Demandes de mutation"),
    ], main_dttm_col="DAT_DEM_MUT"),
    Dataset("pro", "v_grh_promotions", "promotions.sql", [
        Metric("promotions", "COUNT(*)", "Promotions de grade"),
    ], main_dttm_col="DAT_GRAD"),
]

ANNEE_COURANTE = sql_filter("ANNEE = TO_CHAR(SYSDATE, 'YYYY')")
INTER_DIRECTION = simple_filter("CHANGE_DIRECTION", "==", 1)
EN_ATTENTE = simple_filter("STATUT", "==", "En attente")


def charts(ds):
    return {
        "kpi_mutations": big_number("mut", "Mutations de l'année", "mutations", "année en cours",
                                    filters=[ANNEE_COURANTE]),
        "kpi_inter": big_number("mut", "Mutations inter-directions", "pct_inter_direction",
                                "part des mutations (année en cours)", ".1%", [ANNEE_COURANTE]),
        "kpi_attente": big_number("dem", "Demandes en attente", "demandes", "demandes de mutation",
                                  filters=[EN_ATTENTE]),
        "kpi_promotions": big_number("pro", "Promotions de l'année", "promotions", "année en cours",
                                     filters=[ANNEE_COURANTE]),
        "evolution": timeseries("mut", "Mutations par année", "DAT_MUT", "mutations"),
        "raisons": pie("mut", "Mutations par raison", "RAISON", "mutations"),
        "flux": sankey("mut", "Principaux flux de mutations entre directions", "FLUX_ORIGINE", "FLUX_DESTINATION",
                       "mutations", [INTER_DIRECTION]),
        "destination": bar("mut", "Mutations par direction d'accueil", "DIRECTION_DESTINATION", "mutations",
                           horizontal=True),
        "promotions": timeseries("pro", "Promotions par année et par catégorie", "DAT_GRAD", "promotions",
                                 ["CATEGORIE"]),
        "grades": bar("pro", "Grades obtenus", "GRADE_OBTENU", "promotions", horizontal=True),
        "demandes": pie("dem", "Demandes de mutation par statut", "STATUT", "demandes"),
        "liste": table("mut", "Dernières mutations", [
            "DAT_MUT", "MAT_PERS", "NOM_PRENOM", "SERVICE_ORIGINE", "SERVICE_DESTINATION", "RAISON",
            "NUM_DECISION",
        ], "DAT_MUT", ascending=False, limit=200),
    }


LAYOUT = [
    [("kpi_mutations", 3, 26), ("kpi_inter", 3, 26), ("kpi_attente", 3, 26), ("kpi_promotions", 3, 26)],
    [("evolution", 8, 56), ("raisons", 4, 56)],
    [("flux", 12, 90)],
    [("destination", 6, 64), ("demandes", 6, 64)],
    [("promotions", 6, 60), ("grades", 6, 60)],
    [("liste", 12, 64)],
]

KPIS = ["kpi_mutations", "kpi_inter", "kpi_attente", "kpi_promotions"]

FILTERS = [
    Filter("Année", "ANNEE", "mut", exclude=KPIS),
    Filter("Raison", "RAISON", "mut"),
    Filter("Pôle", "POLE", "mut"),
    Filter("Direction", "DIRECTION", "mut"),
    Filter("Catégorie", "CATEGORIE", "mut"),
    Filter("Sexe", "SEXE", "mut"),
]
