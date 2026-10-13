SELECT
    a.cod_soc,
    a.annee_action,
    TO_CHAR(a.annee_action) AS annee,
    CASE WHEN a.annee_action = MAX(a.annee_action) OVER () THEN 1 ELSE 0 END AS derniere_annee,
    a.num_action,
    NVL(TRIM(a.lib_action), NVL(TRIM(th.lib_theme), 'Action ' || a.num_action)) AS intitule,
    NVL(TRIM(tf.lib_tit), 'Non renseigné') AS categorie_formation,
    NVL(TRIM(ty.lib_typ), 'Non renseigné') AS domaine,
    NVL(TRIM(th.lib_theme), 'Non renseigné') AS theme,
    NVL(TRIM(na.lib_nat), 'Non renseigné') AS nature,
    CASE WHEN a.dat_deb_action >= DATE '2000-01-01' THEN a.dat_deb_action END AS dat_deb_action,
    CASE WHEN a.dat_fin_action >= DATE '2000-01-01' THEN a.dat_fin_action END AS dat_fin_action,
    NVL(a.durree_h, 0) AS heures,
    NVL(a.duree_action, 0) AS jours,
    TRIM(a.lieu_action) AS lieu,
    NVL(fr.cout, 0) AS cout,
    NVL(pa.participants, 0) AS participants
FROM action_formation a
LEFT JOIN titre_formation tf ON tf.cod_tit = a.cod_tit
LEFT JOIN type_formation ty ON ty.cod_tit = a.cod_tit AND ty.cod_typ = a.cod_typ
LEFT JOIN theme th ON th.cod_tit = a.cod_tit AND th.cod_typ = a.cod_typ AND th.cod_theme = a.cod_theme
LEFT JOIN nature_action na ON na.cod_nat = a.cod_nat
LEFT JOIN (
    SELECT cod_soc, annee_action, num_action, SUM(NVL(mnt_ttc, mnt_frais_action)) AS cout
    FROM frais_action
    GROUP BY cod_soc, annee_action, num_action
) fr ON fr.cod_soc = a.cod_soc AND fr.annee_action = a.annee_action AND fr.num_action = a.num_action
LEFT JOIN (
    SELECT cod_soc, annee_action, num_action, COUNT(DISTINCT mat_pers) AS participants
    FROM pers_action
    WHERE NVL(etat_pers_action, 'C') <> 'A'
    GROUP BY cod_soc, annee_action, num_action
) pa ON pa.cod_soc = a.cod_soc AND pa.annee_action = a.annee_action AND pa.num_action = a.num_action
