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
    e.tranche_anciennete,
    e.est_actif,
    p.dt_bul,
    TO_CHAR(p.dt_bul, 'YYYY') AS annee,
    TO_CHAR(p.dt_bul, 'MM') AS mois,
    p.cod_typ_bul,
    NVL(TRIM(t.lib_bull), p.cod_typ_bul) AS type_bulletin,
    CASE
        WHEN p.cod_typ_bul = 'BN' THEN '1. Paie mensuelle'
        WHEN p.cod_typ_bul IN ('BB', 'R1', 'R2', 'PE', 'PF', 'PT', 'PV', 'CB') THEN '2. Primes de performance'
        WHEN p.cod_typ_bul IN ('CF', 'AD', 'AE', 'CE', 'SC', 'BA') THEN '3. Primes sociales et fêtes'
        WHEN p.cod_typ_bul IN ('TR', 'RC') THEN '4. Avantages (tickets, retraite compl.)'
        WHEN p.cod_typ_bul IN ('ST', 'PR', 'DN', 'PI') THEN '5. Départs'
        ELSE '6. Rappels et divers'
    END AS famille_remuneration,
    CASE WHEN p.cod_typ_bul = 'BN' THEN p.salaire_base END AS salaire_base,
    CASE WHEN p.cod_typ_bul = 'BN' THEN NVL(p.brut, 0) - NVL(p.salaire_base, 0) END AS indemnites_mensuelles,
    p.brut,
    p.imposable,
    p.cotisations_salariales,
    p.impot,
    p.net,
    p.net_a_payer,
    p.charges_patronales,
    NVL(p.brut, 0) + NVL(p.charges_patronales, 0) AS cout_employeur,
    CASE WHEN p.dt_bul > ADD_MONTHS(mx.dernier_bul, -12) THEN 1 ELSE 0 END AS dernier_12_mois,
    CASE WHEN p.dt_bul = mx.dernier_bul THEN 1 ELSE 0 END AS dernier_mois
FROM (
    SELECT
        v.cod_soc,
        v.mat_pers,
        v.dt_bul,
        v.cod_typ_bul,
        SUM(CASE WHEN v.abrv_fixe = '05011' THEN v.montv END) AS salaire_base,
        SUM(CASE WHEN v.abrv_fixe = '50000' THEN v.montv END) AS brut,
        SUM(CASE WHEN v.abrv_fixe = '55000' THEN v.montv END) AS imposable,
        SUM(CASE WHEN v.abrv_fixe IN ('50011', '50031', '50082', '50083', '74051') THEN v.montv END) AS cotisations_salariales,
        SUM(CASE WHEN v.abrv_fixe IN ('55011', '55051') THEN v.montv END) AS impot,
        SUM(CASE WHEN v.abrv_fixe = '70011' THEN v.montv END) AS net,
        SUM(CASE WHEN v.abrv_fixe = '10000' THEN v.montv END) AS net_a_payer,
        SUM(CASE WHEN v.abrv_fixe LIKE '81%' THEN v.montv END) AS charges_patronales
    FROM possedevh v
    WHERE v.dt_bul >= ADD_MONTHS(TRUNC(SYSDATE, 'YYYY'), -108)
      AND (v.abrv_fixe IN ('05011', '50000', '55000', '50011', '50031', '50082', '50083', '74051',
                           '55011', '55051', '70011', '10000')
           OR v.abrv_fixe LIKE '81%')
    GROUP BY v.cod_soc, v.mat_pers, v.dt_bul, v.cod_typ_bul
) p
CROSS JOIN (SELECT MAX(dt_bul) AS dernier_bul FROM bulletinh WHERE cod_typ_bul = 'BN') mx
LEFT JOIN typ_bulletin t ON t.cod_typ_bul = p.cod_typ_bul
LEFT JOIN (
{personnel}
) e ON e.cod_soc = p.cod_soc AND e.mat_pers = p.mat_pers
