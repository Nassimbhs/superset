SELECT
    p.cod_soc,
    p.mat_pers,
    e.nom_prenom,
    e.sexe,
    e.pole,
    e.direction,
    e.categorie,
    e.grade,
    e.tranche_age,
    e.est_actif,
    TO_CHAR(a.annee_action) AS annee,
    a.annee_action,
    CASE WHEN a.annee_action = (SELECT MAX(annee_action) FROM action_formation) THEN 1 ELSE 0 END AS derniere_annee,
    NVL(TRIM(a.lib_action), NVL(TRIM(th.lib_theme), 'Action ' || a.num_action)) AS intitule,
    NVL(TRIM(tf.lib_tit), 'Non renseigné') AS categorie_formation,
    NVL(TRIM(ty.lib_typ), 'Non renseigné') AS domaine,
    CASE WHEN a.dat_deb_action >= DATE '2000-01-01' THEN a.dat_deb_action END AS dat_deb_action,
    NVL(a.durree_h, 0) AS heures
FROM pers_action p
JOIN action_formation a
    ON a.cod_soc = p.cod_soc AND a.annee_action = p.annee_action AND a.num_action = p.num_action
LEFT JOIN titre_formation tf ON tf.cod_tit = a.cod_tit
LEFT JOIN type_formation ty ON ty.cod_tit = a.cod_tit AND ty.cod_typ = a.cod_typ
LEFT JOIN theme th ON th.cod_tit = a.cod_tit AND th.cod_typ = a.cod_typ AND th.cod_theme = a.cod_theme
LEFT JOIN (
{personnel}
) e ON e.cod_soc = p.cod_soc AND e.mat_pers = p.mat_pers
WHERE NVL(p.etat_pers_action, 'C') <> 'A'
