from grh_builder import (
    Dataset, Filter, Metric, bar, big_number, pie, simple_filter, sql_filter, table, timeseries,
)

KEY = "prets"
TITLE = "Prêts et avances"
SLUG = "prets-avances"

DATASETS = [
    Dataset("prt", "v_grh_prets", "prets.sql", [
        Metric("nb_demandes", "COUNT(*)", "Demandes"),
        Metric("mnt_demande", "SUM(MNT_DEM)", "Montant demandé (DT)", ",.0f"),
        Metric("mnt_accorde", "SUM(MNT_ACCORDE)", "Montant accordé (DT)", ",.0f"),
        Metric("taux_accord", "SUM(ACCORDE) / NULLIF(COUNT(*), 0)", "Taux d'accord", ".1%"),
        Metric("mnt_moyen", "AVG(MNT_ACCORDE)", "Montant moyen accordé (DT)", ",.0f"),
        Metric("prets_en_cours", "SUM(EN_COURS)", "Prêts en cours de remboursement"),
        Metric("mensualites", "SUM(CASE WHEN EN_COURS = 1 THEN REM_MEN END)", "Mensualités en cours (DT)", ",.0f"),
    ], main_dttm_col="DAT_DEM"),
]

ANNEE_COURANTE = sql_filter("ANNEE = TO_CHAR(SYSDATE, 'YYYY')")
EN_COURS = simple_filter("EN_COURS", "==", 1)
ACCORDE = simple_filter("ACCORDE", "==", 1)
DOUZE_MOIS = sql_filter("DAT_DEM >= ADD_MONTHS(TRUNC(SYSDATE), -12)")


def charts(ds):
    return {
        "kpi_demandes": big_number("prt", "Demandes de l'année", "nb_demandes", "année en cours",
                                   filters=[ANNEE_COURANTE]),
        "kpi_accorde": big_number("prt", "Montant accordé (12 mois)", "mnt_accorde", "DT, 12 derniers mois", ",.0f",
                                  [ACCORDE, DOUZE_MOIS]),
        "kpi_en_cours": big_number("prt", "Prêts en cours", "prets_en_cours", "en remboursement"),
        "kpi_mensualites": big_number("prt", "Mensualités en cours", "mensualites", "DT par mois", ",.0f"),
        "evolution": timeseries("prt", "Montant accordé par année et par groupe (DT)", "DAT_DEM", "mnt_accorde",
                                ["GROUPE_PRET"], filters=[ACCORDE], fmt=",.0f"),
        "groupes": pie("prt", "Répartition du montant accordé par groupe", "GROUPE_PRET", "mnt_accorde",
                       [ACCORDE], ",.0f"),
        "types": bar("prt", "Demandes par type de prêt", "TYPE_PRET", "nb_demandes", horizontal=True),
        "statut": pie("prt", "Demandes par statut", "STATUT", "nb_demandes"),
        "categorie": bar("prt", "Montant moyen accordé par catégorie (DT)", "CATEGORIE", "mnt_moyen",
                         filters=[ACCORDE], fmt=",.0f"),
        "direction": bar("prt", "Montant accordé par direction (DT)", "DIRECTION", "mnt_accorde",
                         horizontal=True, filters=[ACCORDE], fmt=",.0f"),
        "liste": table("prt", "Prêts en cours de remboursement", [
            "MAT_PERS", "NOM_PRENOM", "DIRECTION", "GROUPE_PRET", "TYPE_PRET", "MNT_ACCORDE", "NBR_ECH",
            "REM_MEN", "DAT_DEBUT", "DAT_FIN",
        ], "DAT_FIN", filters=[EN_COURS]),
    }


LAYOUT = [
    [("kpi_demandes", 3, 26), ("kpi_accorde", 3, 26), ("kpi_en_cours", 3, 26), ("kpi_mensualites", 3, 26)],
    [("evolution", 8, 60), ("groupes", 4, 60)],
    [("types", 6, 64), ("statut", 3, 64), ("categorie", 3, 64)],
    [("direction", 12, 64)],
    [("liste", 12, 70)],
]

FILTERS = [
    Filter("Année", "ANNEE", "prt", exclude=["kpi_demandes", "kpi_accorde", "kpi_en_cours", "kpi_mensualites",
                                              "liste"]),
    Filter("Groupe de prêt", "GROUPE_PRET", "prt"),
    Filter("Type de prêt", "TYPE_PRET", "prt"),
    Filter("Statut", "STATUT", "prt"),
    Filter("Direction", "DIRECTION", "prt"),
    Filter("Catégorie", "CATEGORIE", "prt"),
]
