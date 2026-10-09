WITH dernier AS (
    SELECT TRUNC(MAX(dt_bul), 'MM') AS mx FROM bulletinh WHERE cod_typ_bul = 'BN'
),
lignes AS (
    SELECT
        d.cod_soc,
        d.mat_pers,
        TRUNC(d.dat_debut, 'MM') AS mois,
        CASE
            WHEN d.code_m = '2000' THEN 'Maladie ordinaire'
            WHEN d.code_m IN ('2020', '2021', '2022', '2050') THEN 'Maternité'
            WHEN d.code_m IN ('2030', '2040') THEN 'Hospitalisation / chirurgie'
            WHEN d.code_m IN ('0025', '0026') THEN 'Accident / maladie professionnelle'
            WHEN m.typ_cng = '03' THEN 'Congé exceptionnel'
            WHEN m.typ_cng = '05' THEN 'Sanction (mise à pied)'
            ELSE NVL(TRIM(m.lib_mot), d.code_m)
        END AS nature_absence,
        d.nbr_jours AS jours_absence,
        0 AS jours_theoriques
    FROM dem_cng d
    JOIN motif_j m ON m.cod_m = d.code_m
    CROSS JOIN dernier x
    WHERE (m.typ_cng IN ('02', '03', '05') OR d.code_m IN ('0025', '0026'))
      AND NVL(d.valid, 'X') <> 'A'
      AND d.dat_debut >= ADD_MONTHS(x.mx, -36)
      AND d.dat_debut < ADD_MONTHS(x.mx, 1)
    UNION ALL
    SELECT DISTINCT
        b.cod_soc,
        b.mat_pers,
        TRUNC(b.dt_bul, 'MM') AS mois,
        'Jours théoriques' AS nature_absence,
        0 AS jours_absence,
        230 / 12 AS jours_theoriques
    FROM bulletinh b
    CROSS JOIN dernier x
    WHERE b.cod_typ_bul = 'BN'
      AND b.dt_bul >= ADD_MONTHS(x.mx, -36)
)
SELECT
    l.cod_soc,
    l.mat_pers,
    e.nom_prenom,
    e.sexe,
    e.pole,
    e.direction,
    e.service,
    e.categorie,
    e.grade,
    e.tranche_age,
    l.mois AS dt_mois,
    TO_CHAR(l.mois, 'YYYY') AS annee,
    l.nature_absence,
    l.jours_absence,
    l.jours_theoriques,
    CASE WHEN l.mois > ADD_MONTHS(x.mx, -12) THEN 1 ELSE 0 END AS douze_mois
FROM lignes l
CROSS JOIN dernier x
LEFT JOIN (
{personnel}
) e ON e.cod_soc = l.cod_soc AND e.mat_pers = l.mat_pers
