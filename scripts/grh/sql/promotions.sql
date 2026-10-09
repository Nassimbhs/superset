SELECT
    pg.cod_soc,
    pg.mat_pers,
    e.nom_prenom,
    e.sexe,
    e.pole,
    e.direction,
    NVL(TRIM(c.lib_cat), 'Non renseigné') AS categorie,
    NVL(TRIM(g.lib_grad), 'Non renseigné') AS grade_obtenu,
    pg.dat_grad,
    TO_CHAR(pg.dat_grad, 'YYYY') AS annee
FROM pers_grade pg
LEFT JOIN categorie c ON c.cod_categ = pg.cod_categ AND c.cod_cat = pg.cod_cat
LEFT JOIN grade g ON g.cod_categ = pg.cod_categ AND g.cod_cat = pg.cod_cat AND g.cod_grad = pg.cod_grad
LEFT JOIN (
{personnel}
) e ON e.cod_soc = pg.cod_soc AND e.mat_pers = pg.mat_pers
WHERE pg.dat_grad >= DATE '2000-01-01'
