SELECT
    s.cod_soc,
    s.mat_pers,
    e.nom_prenom,
    e.sexe,
    e.pole,
    e.direction,
    e.categorie,
    e.grade,
    e.tranche_age,
    e.est_actif,
    TO_CHAR(s.annee_cng) AS annee,
    NVL(TRIM(t.lib_cng), 'Non renseigné') AS type_conge,
    s.init_cng AS report_annee_precedente,
    s.cum_cng AS jours_acquis,
    s.pris_cng AS jours_pris,
    s.sold_cng AS solde_jours,
    CASE WHEN s.annee_cng = EXTRACT(YEAR FROM SYSDATE) THEN 1 ELSE 0 END AS dernier_solde
FROM sold_cng s
LEFT JOIN typ_conge t ON t.typ_cng = s.typ_cng
LEFT JOIN (
{personnel}
) e ON e.cod_soc = s.cod_soc AND e.mat_pers = s.mat_pers
