SELECT
    p.cod_soc,
    p.mat_pers,
    e.sexe,
    e.pole,
    e.direction,
    e.service,
    e.categorie,
    p.jour,
    TO_CHAR(p.jour, 'YYYY') AS annee,
    TO_CHAR(p.jour, 'YYYY-MM') AS mois,
    p.arrivee_min,
    p.depart_min,
    CASE WHEN p.depart_min > p.arrivee_min THEN (p.depart_min - p.arrivee_min) / 60 END AS heures_presence,
    p.nb_pointages
FROM (
    SELECT
        cod_soc,
        mat_pers,
        TRUNC(date_point) AS jour,
        MIN(h_point * 60 + min_point) AS arrivee_min,
        MAX(h_point * 60 + min_point) AS depart_min,
        COUNT(*) AS nb_pointages
    FROM pointer
    WHERE date_point IS NOT NULL
    GROUP BY cod_soc, mat_pers, TRUNC(date_point)
) p
LEFT JOIN (
{personnel}
) e ON e.cod_soc = p.cod_soc AND e.mat_pers = p.mat_pers
