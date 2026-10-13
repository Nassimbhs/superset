SELECT
    d.cod_soc,
    d.mat_pers,
    e.sexe,
    e.pole,
    e.direction,
    e.categorie,
    d.dat_saisie,
    TO_CHAR(d.dat_saisie, 'YYYY') AS annee,
    NVL(TRIM(t.lib_typ_dem), 'Type ' || d.typ_dem) AS type_demande,
    DECODE(d.etat_dem, 'V', 'Traitée', 'S', 'En attente', 'Non renseigné') AS etat,
    CASE WHEN d.dat_reponse - d.dat_saisie BETWEEN 0 AND 365 THEN d.dat_reponse - d.dat_saisie END AS delai_reponse,
    CASE WHEN d.dat_saisie > ADD_MONTHS(mx.dernier_jour, -12) THEN 1 ELSE 0 END AS dernier_12_mois
FROM demande_service d
CROSS JOIN (SELECT MAX(dat_saisie) AS dernier_jour FROM demande_service WHERE dat_saisie <= SYSDATE) mx
LEFT JOIN type_demande t ON t.typ_dem = d.typ_dem
LEFT JOIN (
{personnel}
) e ON e.cod_soc = d.cod_soc AND e.mat_pers = d.mat_pers
WHERE d.dat_saisie <= SYSDATE
  AND d.typ_dem IN ('01', '02', '03', '04')
