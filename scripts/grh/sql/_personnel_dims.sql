SELECT
    p.cod_soc,
    p.mat_pers,
    TRIM(p.nom_pers) || ' ' || TRIM(p.pren_pers) AS nom_prenom,
    DECODE(p.sexe, 'M', 'Homme', 'F', 'Femme', 'Non renseigné') AS sexe,
    DECODE(p.cod_sit, 'M', 'Marié(e)', 'C', 'Célibataire', 'D', 'Divorcé(e)', 'V', 'Veuf(ve)', 'Non renseigné') AS situation_familiale,
    p.nbre_enf,
    DECODE(p.etat_act, '0', 'Actif', '1', 'En position spéciale', '5', 'Sorti', '7', 'Autre', p.etat_act) AS etat,
    CASE WHEN p.etat_act = '0' THEN 1 ELSE 0 END AS est_actif,
    NVL(TRIM(ms.lib_motif), 'Non renseigné') AS position_administrative,
    NVL(TRIM(srv.lib_serv), 'Non affecté') AS service,
    NVL(sd.pole, NVL(TRIM(srv.lib_serv), 'Non affecté')) AS pole,
    NVL(sd.direction, NVL(TRIM(srv.lib_serv), 'Non affecté')) AS direction,
    NVL(TRIM(c.lib_cat), 'Non renseigné') AS categorie,
    NVL(TRIM(g.lib_grad), 'Non renseigné') AS grade,
    NVL(TRIM(f.lib_fonct), 'Sans fonction') AS fonction,
    NVL(TRIM(lg.lib_lieu), 'Non renseigné') AS region,
    NVL(TRIM(nr.lib_nat_recr), 'Non renseigné') AS nature_recrutement,
    TRIM(td.lib_typ_depart) AS type_depart,
    p.dat_nais,
    p.dat_emb,
    p.dat_depart,
    TRUNC(MONTHS_BETWEEN(SYSDATE, p.dat_nais) / 12) AS age,
    CASE
        WHEN p.dat_nais IS NULL THEN 'Non renseigné'
        WHEN MONTHS_BETWEEN(SYSDATE, p.dat_nais) / 12 < 30 THEN '1. Moins de 30 ans'
        WHEN MONTHS_BETWEEN(SYSDATE, p.dat_nais) / 12 < 40 THEN '2. 30-39 ans'
        WHEN MONTHS_BETWEEN(SYSDATE, p.dat_nais) / 12 < 50 THEN '3. 40-49 ans'
        WHEN MONTHS_BETWEEN(SYSDATE, p.dat_nais) / 12 < 60 THEN '4. 50-59 ans'
        ELSE '5. 60 ans et plus'
    END AS tranche_age,
    TRUNC(MONTHS_BETWEEN(SYSDATE, p.dat_emb) / 12) AS anciennete,
    CASE
        WHEN p.dat_emb IS NULL THEN 'Non renseigné'
        WHEN MONTHS_BETWEEN(SYSDATE, p.dat_emb) / 12 < 5 THEN '1. Moins de 5 ans'
        WHEN MONTHS_BETWEEN(SYSDATE, p.dat_emb) / 12 < 10 THEN '2. 5-9 ans'
        WHEN MONTHS_BETWEEN(SYSDATE, p.dat_emb) / 12 < 20 THEN '3. 10-19 ans'
        WHEN MONTHS_BETWEEN(SYSDATE, p.dat_emb) / 12 < 30 THEN '4. 20-29 ans'
        ELSE '5. 30 ans et plus'
    END AS tranche_anciennete
FROM personnel p
LEFT JOIN service srv ON srv.cod_soc = p.cod_soc AND srv.cod_serv = p.cod_serv
LEFT JOIN (
{services}
) sd ON sd.cod_soc = p.cod_soc AND sd.cod_serv = p.cod_serv
LEFT JOIN categorie c ON c.cod_categ = p.cod_categ AND c.cod_cat = p.cod_cat
LEFT JOIN grade g ON g.cod_categ = p.cod_categ AND g.cod_cat = p.cod_cat AND g.cod_grad = p.cod_grad
LEFT JOIN fonctions f ON f.cod_fonct = p.cod_fonct
LEFT JOIN prm_lieu_geographique lg ON lg.cod_lieu_geog = p.cod_lieu_geog
LEFT JOIN nature_recrut nr ON nr.cod_nat_recr = p.cod_nat_recr
LEFT JOIN type_depart td ON td.cod_typ_depart = p.cod_typ_depart
LEFT JOIN motif_sort ms ON ms.cod_motif = p.cod_motif
