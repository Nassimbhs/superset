SELECT
    n.cod_soc,
    n.mat_pers,
    e.sexe,
    e.pole,
    e.direction,
    e.categorie,
    e.grade,
    e.tranche_age,
    e.tranche_anciennete,
    n.dat_note,
    TO_CHAR(n.dat_note, 'YYYY') AS annee,
    n.note_definitive,
    NVL(n.note_max, 20) AS note_max,
    n.note_definitive / NULLIF(NVL(n.note_max, 20), 0) AS note_pct,
    CASE
        WHEN n.note_definitive >= 19 THEN '1. 19 à 20'
        WHEN n.note_definitive >= 17 THEN '2. 17 à 18,99'
        WHEN n.note_definitive >= 15 THEN '3. 15 à 16,99'
        WHEN n.note_definitive >= 12 THEN '4. 12 à 14,99'
        ELSE '5. Moins de 12'
    END AS tranche_note,
    d.note_assiduite,
    d.note_maladie,
    CASE WHEN EXISTS (
        SELECT 1 FROM pers_grade pg
        WHERE pg.cod_soc = n.cod_soc AND pg.mat_pers = n.mat_pers
          AND EXTRACT(YEAR FROM pg.dat_grad) = EXTRACT(YEAR FROM n.dat_note) + 1
    ) THEN 'Promu l''année suivante' ELSE 'Non promu' END AS promotion_suivante,
    CASE WHEN EXTRACT(YEAR FROM n.dat_note) = mx.derniere_annee THEN 1 ELSE 0 END AS derniere_annee,
    CASE WHEN EXTRACT(YEAR FROM n.dat_note) = mx.derniere_annee - 1 THEN 1 ELSE 0 END AS annee_precedente
FROM note_rendement n
CROSS JOIN (SELECT MAX(EXTRACT(YEAR FROM dat_note)) AS derniere_annee FROM note_rendement) mx
LEFT JOIN (
    SELECT cod_soc, mat_pers, dat_note,
           MAX(CASE WHEN cod_type = '02' THEN note_definitive_det END) AS note_assiduite,
           MAX(CASE WHEN cod_type = '01' THEN note_definitive_det END) AS note_maladie
    FROM lig_note_rendement
    GROUP BY cod_soc, mat_pers, dat_note
) d ON d.cod_soc = n.cod_soc AND d.mat_pers = n.mat_pers AND d.dat_note = n.dat_note
LEFT JOIN (
{personnel}
) e ON e.cod_soc = n.cod_soc AND e.mat_pers = n.mat_pers
WHERE n.note_definitive IS NOT NULL
  AND NOT (n.valid = 'S' AND EXTRACT(YEAR FROM n.dat_note) IN (
      SELECT EXTRACT(YEAR FROM dat_note) FROM note_rendement
      GROUP BY EXTRACT(YEAR FROM dat_note)
      HAVING SUM(CASE WHEN valid = 'V' THEN 1 ELSE 0 END) > COUNT(*) / 2
  ))
