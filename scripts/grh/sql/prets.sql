SELECT
    d.cod_soc,
    d.mat_pers,
    e.nom_prenom,
    e.sexe,
    e.pole,
    e.direction,
    e.categorie,
    e.grade,
    e.est_actif,
    d.num_dem_pret,
    NVL(TRIM(gp.lib_grp_pret), 'Non renseigné') AS groupe_pret,
    NVL(TRIM(tp.lib_pret), 'Non renseigné') AS type_pret,
    NVL(TRIM(TRANSLATE(ep.lib_etat_pret, CHR(13) || CHR(10), '  ')), NVL(d.cod_etat_pret, 'Non renseigné')) AS statut,
    d.dat_dem,
    TO_CHAR(d.dat_dem, 'YYYY') AS annee,
    d.dat_debut,
    d.dat_fin,
    d.mnt_dem,
    CASE WHEN g.accorde = 1 THEN d.mnt_acc END AS mnt_accorde,
    g.accorde,
    d.nbr_ech,
    d.taux_int,
    d.rem_men,
    TRIM(d.objet_pret) AS objet_pret,
    CASE
        WHEN g.accorde = 1 AND TRUNC(SYSDATE) BETWEEN d.dat_debut AND d.dat_fin THEN 1 ELSE 0
    END AS en_cours
FROM demande_pret d
CROSS JOIN LATERAL (
    -- Since 2025 granted loans stay in status 'S' but carry an amount and a repayment start date.
    SELECT CASE
        WHEN d.cod_etat_pret = 'A' OR (d.mnt_acc > 0 AND d.dat_debut IS NOT NULL) THEN 1 ELSE 0
    END AS accorde
    FROM dual
) g
LEFT JOIN groupe_pret gp ON gp.cod_soc = d.cod_soc AND gp.cod_grp_pret = d.cod_grp_pret
LEFT JOIN type_pret tp ON tp.cod_soc = d.cod_soc AND tp.cod_grp_pret = d.cod_grp_pret AND tp.typ_pret = d.typ_pret
LEFT JOIN etat_pret ep ON ep.typ_etat = NVL(d.typ_etat, 'D') AND ep.cod_etat_pret = d.cod_etat_pret
LEFT JOIN (
{personnel}
) e ON e.cod_soc = d.cod_soc AND e.mat_pers = d.mat_pers
WHERE d.dat_dem IS NOT NULL
