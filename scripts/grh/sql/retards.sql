SELECT
    r.cod_soc,
    r.mat_pers,
    e.sexe,
    e.pole,
    e.direction,
    e.service,
    e.categorie,
    e.tranche_age,
    r.dat_point,
    TO_CHAR(r.dat_point, 'YYYY') AS annee,
    TO_CHAR(r.dat_point, 'YYYY-MM') AS mois,
    TO_CHAR(r.dat_point, 'D') || '. ' || TRIM(TO_CHAR(r.dat_point, 'Day', 'NLS_DATE_LANGUAGE=FRENCH')) AS jour_semaine,
    NVL(r.duree_h, 0) * 60 + NVL(r.duree_m, 0) AS minutes_retard,
    CASE
        WHEN NVL(r.duree_h, 0) * 60 + NVL(r.duree_m, 0) < 15 THEN '1. Moins de 15 min'
        WHEN NVL(r.duree_h, 0) * 60 + NVL(r.duree_m, 0) < 30 THEN '2. 15 à 29 min'
        WHEN NVL(r.duree_h, 0) * 60 + NVL(r.duree_m, 0) < 60 THEN '3. 30 à 59 min'
        WHEN NVL(r.duree_h, 0) * 60 + NVL(r.duree_m, 0) < 120 THEN '4. 1 à 2 h'
        ELSE '5. Plus de 2 h'
    END AS tranche_retard,
    LPAD(r.h_point, 2, '0') || 'h' AS heure_arrivee,
    CASE WHEN r.dat_point > ADD_MONTHS(mx.dernier_jour, -12) THEN 1 ELSE 0 END AS dernier_12_mois
FROM retard_journee r
CROSS JOIN (SELECT MAX(dat_point) AS dernier_jour FROM retard_journee) mx
LEFT JOIN (
{personnel}
) e ON e.cod_soc = r.cod_soc AND e.mat_pers = r.mat_pers
WHERE r.type = 'R'
  AND NVL(r.duree_h, 0) * 60 + NVL(r.duree_m, 0) > 0
