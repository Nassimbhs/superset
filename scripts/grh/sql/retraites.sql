SELECT
    r.*,
    TO_CHAR(r.date_retraite, 'YYYY') AS annee_retraite,
    TRUNC(MONTHS_BETWEEN(r.date_retraite, TRUNC(SYSDATE))) AS mois_restants,
    CASE WHEN r.date_retraite < TRUNC(SYSDATE) THEN 'Âge légal dépassé' ELSE 'À venir' END AS statut_retraite
FROM (
    SELECT
        e.cod_soc,
        e.mat_pers,
        e.nom_prenom,
        e.sexe,
        e.pole,
        e.direction,
        e.categorie,
        e.grade,
        e.fonction,
        e.age,
        e.anciennete,
        e.dat_nais,
        CASE
            WHEN rn.date_ret > TRUNC(SYSDATE) THEN rn.date_ret
            ELSE ADD_MONTHS(e.dat_nais, NVL(s.max_age, 720))
        END AS date_retraite
    FROM (
{personnel}
    ) e
    LEFT JOIN societe s ON s.cod_soc = e.cod_soc
    LEFT JOIN (
        SELECT cod_soc, mat_pers, MAX(date_ret) AS date_ret FROM retraite_normal GROUP BY cod_soc, mat_pers
    ) rn ON rn.cod_soc = e.cod_soc AND rn.mat_pers = e.mat_pers
    WHERE e.est_actif = 1
      AND e.dat_nais IS NOT NULL
) r
