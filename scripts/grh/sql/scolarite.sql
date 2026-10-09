SELECT
    s.cod_soc,
    s.num_prime_s,
    s.mat_pers,
    e.sexe,
    e.pole,
    e.direction,
    e.categorie,
    TO_CHAR(s.annee_scolaire) AS annee,
    s.dat_dem_prime_s,
    CASE
        WHEN s.age_fam IS NULL THEN 'Non renseigné'
        WHEN s.age_fam < 6 THEN '1. Préscolaire (< 6 ans)'
        WHEN s.age_fam < 12 THEN '2. Primaire (6-11 ans)'
        WHEN s.age_fam < 15 THEN '3. Collège (12-14 ans)'
        WHEN s.age_fam < 19 THEN '4. Lycée (15-18 ans)'
        ELSE '5. Supérieur (19 ans et plus)'
    END AS niveau_estime,
    NVL(s.mnt_prime_s, 0) AS montant_prime
FROM prime_scolarite s
LEFT JOIN (
{personnel}
) e ON e.cod_soc = s.cod_soc AND e.mat_pers = s.mat_pers
WHERE s.val_prime_s = 'V'
  AND s.annul_prime IS NULL
