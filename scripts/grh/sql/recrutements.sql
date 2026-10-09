SELECT
    e.cod_soc,
    e.mat_pers,
    e.nom_prenom,
    e.sexe,
    e.pole,
    e.direction,
    e.categorie,
    e.grade,
    e.etat,
    e.nature_recrutement,
    e.dat_emb,
    TO_CHAR(e.dat_emb, 'YYYY') AS annee,
    TRUNC(MONTHS_BETWEEN(e.dat_emb, e.dat_nais) / 12) AS age_recrutement
FROM (
{personnel}
) e
WHERE e.dat_emb IS NOT NULL
