SELECT
    d.cod_soc,
    d.mat_pers,
    e.nom_prenom,
    e.sexe,
    e.pole,
    e.direction,
    e.categorie,
    e.grade,
    e.tranche_age,
    e.est_actif,
    CASE
        WHEN d.code_m = '2000' THEN 'Maladie ordinaire'
        WHEN d.code_m IN ('2020', '2021', '2022', '2050') THEN 'Maternité'
        WHEN d.code_m IN ('2030', '2040') THEN 'Hospitalisation / chirurgie'
        WHEN d.code_m = '0025' THEN 'Accident de travail'
        WHEN d.code_m = '0026' THEN 'Maladie professionnelle'
        ELSE NVL(TRIM(m.lib_mot), d.code_m)
    END AS nature_absence,
    NVL(TRIM(m.lib_mot), d.code_m) AS motif,
    d.dat_debut,
    d.dat_fin,
    TO_CHAR(d.dat_debut, 'YYYY') AS annee,
    TO_CHAR(d.dat_debut, 'MM') AS mois,
    d.nbr_jours,
    CASE WHEN d.dat_debut BETWEEN ADD_MONTHS(TRUNC(SYSDATE), -12) AND SYSDATE THEN 1 ELSE 0 END AS dernier_12_mois,
    (SELECT COUNT(*) FROM personnel WHERE etat_act = '0') AS effectif_actif
FROM dem_cng d
JOIN motif_j m ON m.cod_m = d.code_m
LEFT JOIN (
{personnel}
) e ON e.cod_soc = d.cod_soc AND e.mat_pers = d.mat_pers
WHERE (m.typ_cng = '02' OR d.code_m IN ('0025', '0026'))
  AND NVL(d.valid, 'X') <> 'A'
  AND d.dat_debut >= DATE '2007-01-01'
  AND d.dat_debut < ADD_MONTHS(TRUNC(SYSDATE, 'YYYY'), 24)
