SELECT
    a.cod_soc,
    a.num_acc,
    a.mat_pers,
    e.nom_prenom,
    e.sexe,
    e.pole,
    e.direction,
    e.categorie,
    a.dat_acc,
    TO_CHAR(a.dat_acc, 'YYYY') AS annee,
    DECODE(TRIM(a.nature_acc), 'T', 'Accident de trajet', NULL, 'Non renseigné', 'Accident de travail') AS nature_accident,
    TRIM(a.lieu_acc) AS lieu_accident,
    TRIM(a.circ_acc) AS circonstances,
    a.dat_arret_trav,
    a.taux_ipp
FROM accident a
LEFT JOIN (
{personnel}
) e ON e.cod_soc = a.cod_soc AND e.mat_pers = a.mat_pers
