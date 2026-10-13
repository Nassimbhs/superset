SELECT
    d.cod_soc,
    d.mat_pers,
    e.nom_prenom,
    e.sexe,
    e.pole,
    e.direction,
    e.categorie,
    NVL(TRIM(r.lib_rais), 'Non renseigné') AS raison,
    DECODE(d.valider, 'V', 'Validée', 'C', 'Annulée', 'N', 'En attente', 'Non renseigné') AS statut,
    d.dat_dem_mut,
    TO_CHAR(d.dat_dem_mut, 'YYYY') AS annee
FROM dem_mutation d
LEFT JOIN raison_mutation r ON r.cod_rais = d.cod_rais
LEFT JOIN (
{personnel}
) e ON e.cod_soc = d.cod_soc AND e.mat_pers = d.mat_pers
WHERE d.dat_dem_mut IS NOT NULL
