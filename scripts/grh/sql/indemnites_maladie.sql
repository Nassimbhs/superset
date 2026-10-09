SELECT
    i.cod_soc,
    i.num_dem,
    i.mat_pers,
    e.nom_prenom,
    e.sexe,
    e.pole,
    e.direction,
    e.categorie,
    e.tranche_age,
    i.dat_saisie,
    i.dat_arret,
    NVL(TO_CHAR(i.annee), TO_CHAR(i.dat_arret, 'YYYY')) AS annee,
    i.nbr_jours,
    DECODE(i.sit_dem, 'T', 'Traitée', 'A', 'Annulée', 'En cours') AS situation
FROM dem_ind_mal i
LEFT JOIN (
{personnel}
) e ON e.cod_soc = i.cod_soc AND e.mat_pers = i.mat_pers
