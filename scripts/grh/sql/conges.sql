SELECT
    d.cod_soc,
    d.mat_pers,
    e.nom_prenom,
    e.sexe,
    e.pole,
    e.direction,
    e.categorie,
    e.grade,
    e.region,
    e.tranche_age,
    e.est_actif,
    NVL(TRIM(t.lib_cng), 'Non renseigné') AS type_conge,
    NVL(TRIM(m.lib_mot), d.code_m) AS motif,
    DECODE(d.valid, 'O', 'Validé', 'A', 'Annulé', 'I', 'En instance', 'S', 'Saisi', 'Non renseigné') AS statut,
    d.dat_debut,
    d.dat_fin,
    TO_CHAR(d.dat_debut, 'YYYY') AS annee,
    d.nbr_jours,
    d.sold_cng,
    CASE WHEN TRUNC(SYSDATE) BETWEEN TRUNC(d.dat_debut) AND TRUNC(d.dat_fin) THEN 1 ELSE 0 END AS en_cours
FROM dem_cng d
LEFT JOIN motif_j m ON m.cod_m = d.code_m
LEFT JOIN typ_conge t ON t.typ_cng = m.typ_cng
LEFT JOIN (
{personnel}
) e ON e.cod_soc = d.cod_soc AND e.mat_pers = d.mat_pers
WHERE d.dat_debut >= DATE '2007-01-01'
  AND d.dat_debut < ADD_MONTHS(TRUNC(SYSDATE, 'YYYY'), 24)
