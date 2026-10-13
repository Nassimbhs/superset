SELECT
    i.cod_soc,
    i.mat_pers,
    i.mat_pers_int,
    e.sexe,
    e.pole,
    e.direction,
    e.categorie,
    i.dat_debut_int,
    TO_CHAR(i.dat_debut_int, 'YYYY') AS annee,
    TO_CHAR(i.dat_debut_int, 'YYYY-MM') AS mois,
    CASE WHEN i.dat_fin_int >= i.dat_debut_int THEN i.dat_fin_int - i.dat_debut_int + 1 END AS jours_interim,
    CASE WHEN i.dat_debut_int > ADD_MONTHS(mx.dernier_jour, -12) THEN 1 ELSE 0 END AS dernier_12_mois
FROM interim_cng i
CROSS JOIN (SELECT MAX(dat_debut_int) AS dernier_jour FROM interim_cng WHERE dat_debut_int <= SYSDATE) mx
LEFT JOIN (
{personnel}
) e ON e.cod_soc = i.cod_soc AND e.mat_pers = i.mat_pers
WHERE i.dat_debut_int BETWEEN DATE '2022-01-01' AND ADD_MONTHS(SYSDATE, 6)
