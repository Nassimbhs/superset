WITH dernier AS (
    SELECT TRUNC(MAX(dt_bul), 'MM') AS mx FROM bulletinh WHERE cod_typ_bul = 'BN'
),
payes AS (
    SELECT DISTINCT b.cod_soc, b.mat_pers, TRUNC(b.dt_bul, 'MM') AS mois
    FROM bulletinh b
    CROSS JOIN dernier d
    WHERE b.cod_typ_bul = 'BN'
      AND b.dt_bul >= ADD_MONTHS(d.mx, -37)
),
flux AS (
    SELECT
        p.cod_soc,
        p.mat_pers,
        p.mois,
        d.mx,
        LAG(p.mois) OVER (PARTITION BY p.cod_soc, p.mat_pers ORDER BY p.mois) AS mois_prec,
        LEAD(p.mois) OVER (PARTITION BY p.cod_soc, p.mat_pers ORDER BY p.mois) AS mois_suiv,
        MAX(CASE WHEN p.mois = d.mx THEN 1 ELSE 0 END)
            OVER (PARTITION BY p.cod_soc, p.mat_pers) AS paye_dernier_mois
    FROM payes p
    CROSS JOIN dernier d
),
cout AS (
    SELECT
        v.cod_soc,
        v.mat_pers,
        TRUNC(v.dt_bul, 'MM') AS mois,
        SUM(CASE WHEN v.abrv_fixe = '50000' THEN v.montv END) AS brut,
        SUM(CASE WHEN v.abrv_fixe LIKE '81%' THEN v.montv END) AS charges_patronales
    FROM possedevh v
    CROSS JOIN dernier d
    WHERE v.cod_typ_bul = 'BN'
      AND v.dt_bul >= ADD_MONTHS(d.mx, -36)
      AND (v.abrv_fixe = '50000' OR v.abrv_fixe LIKE '81%')
    GROUP BY v.cod_soc, v.mat_pers, TRUNC(v.dt_bul, 'MM')
)
SELECT
    f.cod_soc,
    f.mat_pers,
    e.nom_prenom,
    e.sexe,
    e.pole,
    e.direction,
    e.service,
    e.categorie,
    e.grade,
    e.fonction,
    e.region,
    e.tranche_age,
    e.tranche_anciennete,
    f.mois AS dt_mois,
    TO_CHAR(f.mois, 'YYYY') AS annee,
    CASE WHEN f.mois_prec IS NULL OR f.mois_prec <> ADD_MONTHS(f.mois, -1) THEN 1 ELSE 0 END AS entree,
    CASE WHEN f.mois < f.mx AND (f.mois_suiv IS NULL OR f.mois_suiv <> ADD_MONTHS(f.mois, 1))
         THEN 1 ELSE 0 END AS sortie,
    CASE WHEN f.mois = f.mx THEN 1 ELSE 0 END AS dernier_mois,
    CASE WHEN f.mois > ADD_MONTHS(f.mx, -12) THEN 1 ELSE 0 END AS douze_mois,
    CASE WHEN f.mois = ADD_MONTHS(f.mx, -12) THEN 1 ELSE 0 END AS ref_m12,
    CASE WHEN f.mois = ADD_MONTHS(f.mx, -12) AND f.paye_dernier_mois = 1 THEN 1 ELSE 0 END AS retenu,
    CASE WHEN NVL(e.fonction, 'Sans fonction') <> 'Sans fonction' THEN 1 ELSE 0 END AS est_responsable,
    CASE WHEN NVL(e.fonction, 'Sans fonction') <> 'Sans fonction' AND e.sexe = 'Femme'
         THEN 1 ELSE 0 END AS responsable_femme,
    NVL(c.brut, 0) AS brut,
    NVL(c.brut, 0) + NVL(c.charges_patronales, 0) AS cout_employeur
FROM flux f
LEFT JOIN cout c ON c.cod_soc = f.cod_soc AND c.mat_pers = f.mat_pers AND c.mois = f.mois
LEFT JOIN (
{personnel}
) e ON e.cod_soc = f.cod_soc AND e.mat_pers = f.mat_pers
WHERE f.mois >= ADD_MONTHS(f.mx, -36)
