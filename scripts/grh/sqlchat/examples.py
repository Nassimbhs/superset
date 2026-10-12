"""Hand-written question -> SQL examples shown to the model (only those of the views
selected for a question) and questions suggested in the chat bubble per dashboard.
Every SQL must run as is on the flat views (checked by eval_sql.py --examples)."""

EXAMPLES: list[dict] = [
    # Effectif
    {"view": "v_effectif_grh", "question": "Combien d'agents actifs ?",
     "sql": "SELECT COUNT(DISTINCT MAT_PERS) AS EFFECTIF FROM v_effectif_grh WHERE EST_ACTIF = 1"},
    {"view": "v_effectif_grh", "question": "Effectif actif par direction",
     "sql": "SELECT DIRECTION, COUNT(DISTINCT MAT_PERS) AS EFFECTIF FROM v_effectif_grh WHERE EST_ACTIF = 1 "
            "GROUP BY DIRECTION ORDER BY EFFECTIF DESC"},
    {"view": "v_effectif_grh", "question": "Âge moyen des femmes du personnel d'encadrement",
     "sql": "SELECT ROUND(AVG(AGE), 1) AS AGE_MOYEN FROM v_effectif_grh WHERE EST_ACTIF = 1 AND SEXE = 'Femme' "
            "AND CATEGORIE = 'Personnel d''encadrement'"},
    {"view": "v_effectif_grh", "question": "Liste des agents actifs de plus de 60 ans",
     "sql": "SELECT MAT_PERS, NOM_PRENOM, AGE, DIRECTION FROM v_effectif_grh WHERE EST_ACTIF = 1 AND AGE > 60 "
            "ORDER BY AGE DESC"},
    {"view": "v_effectif_grh", "question": "Nombre d'agents actifs par région",
     "sql": "SELECT REGION, COUNT(DISTINCT MAT_PERS) AS EFFECTIF FROM v_effectif_grh WHERE EST_ACTIF = 1 "
            "GROUP BY REGION ORDER BY EFFECTIF DESC"},
    {"view": "v_grh_effectif_mensuel", "question": "Effectif payé par mois sur les 12 derniers mois",
     "sql": "SELECT TO_CHAR(DT_MOIS, 'YYYY-MM') AS MOIS, COUNT(DISTINCT MAT_PERS) AS EFFECTIF "
            "FROM v_grh_effectif_mensuel WHERE DOUZE_MOIS = 1 GROUP BY TO_CHAR(DT_MOIS, 'YYYY-MM') ORDER BY MOIS"},
    # Congés
    {"view": "v_grh_conges", "question": "Jours de congé par type en 2025",
     "sql": "SELECT TYPE_CONGE, SUM(NBR_JOURS) AS JOURS FROM v_grh_conges WHERE ANNEE = '2025' "
            "GROUP BY TYPE_CONGE ORDER BY JOURS DESC"},
    {"view": "v_grh_conges", "question": "Qui est en congé aujourd'hui ?",
     "sql": "SELECT MAT_PERS, NOM_PRENOM, TYPE_CONGE, DAT_DEBUT, DAT_FIN FROM v_grh_conges WHERE EN_COURS = 1 "
            "ORDER BY DAT_FIN"},
    {"view": "v_grh_soldes_conges", "question": "Solde de congé annuel du matricule 0153 en 2025",
     "sql": "SELECT MAT_PERS, NOM_PRENOM, ANNEE, REPORT_ANNEE_PRECEDENTE, JOURS_ACQUIS, JOURS_PRIS, SOLDE_JOURS "
            "FROM v_grh_soldes_conges WHERE MAT_PERS = '0153' AND ANNEE = '2025' AND TYPE_CONGE = 'Congé annuel'"},
    {"view": "v_grh_soldes_conges", "question": "Top 10 des agents avec le plus grand solde de congé",
     "sql": "SELECT MAT_PERS, NOM_PRENOM, SOLDE_JOURS FROM v_grh_soldes_conges WHERE DERNIER_SOLDE = 1 "
            "ORDER BY SOLDE_JOURS DESC FETCH FIRST 10 ROWS ONLY"},
    {"view": "v_grh_soldes_conges", "question": "Évolution du solde de congé du matricule 0153 par année",
     "sql": "SELECT ANNEE, SUM(JOURS_PRIS) AS JOURS_PRIS, SUM(SOLDE_JOURS) AS SOLDE_JOURS "
            "FROM v_grh_soldes_conges WHERE MAT_PERS = '0153' GROUP BY ANNEE ORDER BY ANNEE"},
    {"view": "v_grh_soldes_conges", "question": "Solde moyen de congé par direction",
     "sql": "SELECT DIRECTION, ROUND(AVG(SOLDE_JOURS), 2) AS SOLDE_MOYEN FROM v_grh_soldes_conges "
            "WHERE DERNIER_SOLDE = 1 GROUP BY DIRECTION ORDER BY SOLDE_MOYEN DESC"},
    # Présence
    {"view": "v_grh_retards", "question": "Top 5 des retardataires en 2026 avec matricule, nom et prénom",
     "sql": "SELECT MAT_PERS, NOM_PRENOM, COUNT(*) AS RETARDS FROM v_grh_retards WHERE ANNEE = '2026' "
            "GROUP BY MAT_PERS, NOM_PRENOM ORDER BY RETARDS DESC FETCH FIRST 5 ROWS ONLY"},
    {"view": "v_grh_retards", "question": "Minutes de retard par direction en janvier 2026",
     "sql": "SELECT DIRECTION, SUM(MINUTES_RETARD) AS MINUTES_RETARD FROM v_grh_retards WHERE MOIS = '2026-01' "
            "GROUP BY DIRECTION ORDER BY MINUTES_RETARD DESC"},
    {"view": "v_grh_retards", "question": "Retards de l'agent BEN CHAABENE par mois",
     "sql": "SELECT MOIS, COUNT(*) AS RETARDS FROM v_grh_retards WHERE UPPER(NOM_PRENOM) LIKE '%BEN CHAABENE%' "
            "GROUP BY MOIS ORDER BY MOIS"},
    {"view": "v_grh_pointages", "question": "Présence moyenne par jour et par direction",
     "sql": "SELECT DIRECTION, ROUND(AVG(HEURES_PRESENCE), 2) AS HEURES_PRESENCE FROM v_grh_pointages "
            "GROUP BY DIRECTION ORDER BY HEURES_PRESENCE DESC"},
    # Salaires et budget
    {"view": "v_grh_paie", "question": "Masse salariale brute par mois en 2025",
     "sql": "SELECT MOIS, SUM(BRUT) AS MASSE_BRUTE FROM v_grh_paie WHERE ANNEE = '2025' AND COD_TYP_BUL = 'BN' "
            "GROUP BY MOIS ORDER BY MOIS"},
    {"view": "v_grh_paie", "question": "Salaire net moyen par catégorie le dernier mois",
     "sql": "SELECT CATEGORIE, ROUND(AVG(NET_A_PAYER)) AS NET_MOYEN FROM v_grh_paie WHERE DERNIER_MOIS = 1 "
            "AND COD_TYP_BUL = 'BN' GROUP BY CATEGORIE ORDER BY NET_MOYEN DESC"},
    {"view": "v_grh_budget", "question": "Budget et réalisé par type de rubrique en 2025",
     "sql": "SELECT TYPE_RUBRIQUE, SUM(BUDGET) AS BUDGET, SUM(REALISE) AS REALISE FROM v_grh_budget "
            "WHERE ANNEE = 2025 GROUP BY TYPE_RUBRIQUE ORDER BY BUDGET DESC"},
    # Santé
    {"view": "v_grh_absenteisme_global", "question": "Jours d'absence par direction sur les 12 derniers mois",
     "sql": "SELECT DIRECTION, SUM(JOURS_ABSENCE) AS JOURS_ABSENCE FROM v_grh_absenteisme_global WHERE DOUZE_MOIS = 1 "
            "GROUP BY DIRECTION ORDER BY JOURS_ABSENCE DESC"},
    {"view": "v_grh_absenteisme_global", "question": "Taux d'absentéisme par année",
     "sql": "SELECT ANNEE, ROUND(SUM(JOURS_ABSENCE) / NULLIF(SUM(JOURS_THEORIQUES), 0) * 100, 2) AS TAUX_ABSENTEISME "
            "FROM v_grh_absenteisme_global GROUP BY ANNEE ORDER BY ANNEE"},
    {"view": "v_grh_absences_maladie", "question": "Top 10 des agents avec le plus de jours de maladie en 2025",
     "sql": "SELECT MAT_PERS, NOM_PRENOM, SUM(NBR_JOURS) AS JOURS_MALADIE FROM v_grh_absences_maladie "
            "WHERE ANNEE = '2025' GROUP BY MAT_PERS, NOM_PRENOM ORDER BY JOURS_MALADIE DESC FETCH FIRST 10 ROWS ONLY"},
    {"view": "v_grh_accidents", "question": "Nombre d'accidents par année",
     "sql": "SELECT ANNEE, COUNT(*) AS ACCIDENTS FROM v_grh_accidents GROUP BY ANNEE ORDER BY ANNEE"},
    # Formation
    {"view": "v_grh_formation_actions", "question": "Coût des formations par domaine en 2025",
     "sql": "SELECT DOMAINE, SUM(COUT) AS COUT FROM v_grh_formation_actions WHERE ANNEE = '2025' "
            "GROUP BY DOMAINE ORDER BY COUT DESC"},
    {"view": "v_grh_formation_participants", "question": "Agents ayant suivi le plus d'heures de formation",
     "sql": "SELECT MAT_PERS, NOM_PRENOM, SUM(HEURES) AS HEURES FROM v_grh_formation_participants "
            "GROUP BY MAT_PERS, NOM_PRENOM ORDER BY HEURES DESC FETCH FIRST 10 ROWS ONLY"},
    # Départs, mobilité, recrutement
    {"view": "v_grh_departs", "question": "Départs par type de départ et par année",
     "sql": "SELECT ANNEE, TYPE_DEPART, COUNT(DISTINCT MAT_PERS) AS DEPARTS FROM v_grh_departs "
            "GROUP BY ANNEE, TYPE_DEPART ORDER BY ANNEE, DEPARTS DESC"},
    {"view": "v_grh_retraites", "question": "Agents qui partent à la retraite en 2027",
     "sql": "SELECT MAT_PERS, NOM_PRENOM, DIRECTION, DATE_RETRAITE FROM v_grh_retraites WHERE ANNEE_RETRAITE = '2027' "
            "ORDER BY DATE_RETRAITE"},
    {"view": "v_grh_mutations", "question": "Mutations par direction d'origine en 2025",
     "sql": "SELECT DIRECTION_ORIGINE, COUNT(*) AS MUTATIONS FROM v_grh_mutations WHERE ANNEE = '2025' "
            "GROUP BY DIRECTION_ORIGINE ORDER BY MUTATIONS DESC"},
    {"view": "v_grh_recrutements", "question": "Recrutements par année",
     "sql": "SELECT ANNEE, COUNT(DISTINCT MAT_PERS) AS RECRUTEMENTS FROM v_grh_recrutements GROUP BY ANNEE ORDER BY ANNEE"},
    {"view": "v_grh_candidats", "question": "Nombre de candidats par statut",
     "sql": "SELECT STATUT, COUNT(*) AS CANDIDATS FROM v_grh_candidats GROUP BY STATUT ORDER BY CANDIDATS DESC"},
    # Prêts, endettement, social, soins
    {"view": "v_grh_prets", "question": "Montant accordé par type de prêt",
     "sql": "SELECT TYPE_PRET, SUM(MNT_ACCORDE) AS MONTANT_ACCORDE FROM v_grh_prets GROUP BY TYPE_PRET "
            "ORDER BY MONTANT_ACCORDE DESC"},
    {"view": "v_grh_prets", "question": "Nombre de demandes de prêt par statut",
     "sql": "SELECT STATUT, COUNT(*) AS DEMANDES FROM v_grh_prets GROUP BY STATUT ORDER BY DEMANDES DESC"},
    {"view": "v_grh_capacite", "question": "Agents dont l'endettement dépasse 40 %",
     "sql": "SELECT MAT_PERS, NOM_PRENOM, TAUX_APRES_PRET FROM v_grh_capacite WHERE DERNIERE_SIMULATION = 1 "
            "AND AU_DELA_SEUIL = 1 ORDER BY TAUX_APRES_PRET DESC"},
    {"view": "v_grh_cessions", "question": "Mensualités des cessions en cours par famille",
     "sql": "SELECT FAMILLE_CESSION, SUM(MENSUALITE) AS MENSUALITES FROM v_grh_cessions WHERE EN_COURS = 1 "
            "GROUP BY FAMILLE_CESSION ORDER BY MENSUALITES DESC"},
    {"view": "v_grh_dons", "question": "Montant des dons accordés par nature en 2025",
     "sql": "SELECT NATURE_DON, SUM(MONTANT_ACCORDE) AS MONTANT_ACCORDE FROM v_grh_dons WHERE ANNEE = '2025' "
            "GROUP BY NATURE_DON ORDER BY MONTANT_ACCORDE DESC"},
    {"view": "v_grh_soins", "question": "Taux de remboursement des soins par année",
     "sql": "SELECT ANNEE, ROUND(SUM(MONTANT_REMBOURSE) / NULLIF(SUM(FRAIS_ENGAGES), 0) * 100, 1) AS TAUX_REMBOURSEMENT "
            "FROM v_grh_soins GROUP BY ANNEE ORDER BY ANNEE"},
    # Rendement, services
    {"view": "v_grh_notes_rendement", "question": "Note moyenne par direction la dernière année",
     "sql": "SELECT DIRECTION, ROUND(AVG(NOTE_DEFINITIVE), 2) AS NOTE_MOYENNE FROM v_grh_notes_rendement "
            "WHERE DERNIERE_ANNEE = 1 GROUP BY DIRECTION ORDER BY NOTE_MOYENNE DESC"},
    {"view": "v_grh_demandes_service", "question": "Demandes en attente par type",
     "sql": "SELECT TYPE_DEMANDE, COUNT(*) AS DEMANDES FROM v_grh_demandes_service WHERE ETAT = 'En attente' "
            "GROUP BY TYPE_DEMANDE ORDER BY DEMANDES DESC"},
    {"view": "v_grh_demandes_service", "question": "Nombre de demandes de service par état",
     "sql": "SELECT ETAT, COUNT(*) AS DEMANDES FROM v_grh_demandes_service GROUP BY ETAT ORDER BY DEMANDES DESC"},
    {"view": "v_grh_demandes_service", "question": "Délai moyen de réponse par année",
     "sql": "SELECT ANNEE, ROUND(AVG(DELAI_REPONSE), 1) AS DELAI_MOYEN FROM v_grh_demandes_service "
            "GROUP BY ANNEE ORDER BY ANNEE"},
]

SUGGESTIONS: dict[str, list[str]] = {
    "synthese": ["Effectif payé par mois sur les 12 derniers mois", "Coût employeur par année",
                 "Jours d'absence par nature en 2025"],
    "effectif": ["Effectif actif par direction", "Âge moyen par catégorie", "Agents actifs de plus de 60 ans",
                 "Nombre de femmes actives par pôle"],
    "conges": ["Jours de congé par type en 2025", "Qui est en congé aujourd'hui ?",
               "Top 10 des agents avec le plus grand solde de congé"],
    "formation": ["Coût des formations par domaine en 2025", "Agents ayant suivi le plus d'heures de formation"],
    "departs": ["Départs par type de départ et par année", "Agents qui partent à la retraite en 2027"],
    "prets": ["Montant accordé par type de prêt", "Prêts en cours par direction"],
    "mobilite": ["Mutations par direction d'origine en 2025", "Promotions par grade obtenu"],
    "recrutement": ["Recrutements par année", "Candidats par concours"],
    "sante": ["Top 10 des agents avec le plus de jours de maladie en 2025", "Nombre d'accidents par année"],
    "salaires": ["Masse salariale brute par mois en 2025", "Salaire net moyen par catégorie le dernier mois"],
    "presence": ["Top 5 des retardataires en 2026 avec matricule, nom et prénom",
                 "Minutes de retard par direction en janvier 2026", "Présence moyenne par direction"],
    "budget": ["Budget et réalisé par type de rubrique en 2025"],
    "rendement": ["Note moyenne par direction la dernière année", "Top 10 des meilleures notes en 2025"],
    "soins": ["Taux de remboursement des soins par année", "Montant remboursé par type d'acte"],
    "social": ["Montant des dons accordés par nature en 2025", "Primes de scolarité par niveau"],
    "endettement": ["Agents dont l'endettement dépasse 40 %", "Mensualités des cessions en cours par famille"],
    "services": ["Demandes en attente par type", "Jours d'intérim par direction"],
}
