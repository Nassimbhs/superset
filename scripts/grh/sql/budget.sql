SELECT
    g.cod_soc,
    g.annee_budg AS annee,
    g.mois,
    TO_CHAR(g.mois, 'MM') AS num_mois,
    g.cod_rub_budg,
    g.cod_rub_budg || ' - ' || NVL(TRIM(r.lib_rub_budg), 'Rubrique ' || g.cod_rub_budg) AS rubrique,
    DECODE(r.typ_rub_budg,
           'S', 'Salaires et indemnités',
           'C', 'Charges sociales',
           'F', 'Frais',
           'D', 'Départs',
           'I', 'Avantages et social',
           'P', 'Promotions',
           'R', 'Recrutements',
           'A', 'Augmentations',
           'Autre') AS type_rubrique,
    CASE WHEN EXISTS (SELECT 1 FROM bult_budg bb WHERE bb.cod_rub_budg = g.cod_rub_budg)
              AND EXISTS (SELECT 1 FROM abrv_budg ab WHERE ab.cod_rub_budg = g.cod_rub_budg)
         THEN 1 ELSE 0 END AS rubrique_paie,
    NVL(g.mnt_budg_glob, 0) AS budget,
    NVL(re.montant, 0) AS realise,
    CASE WHEN TRUNC(g.mois, 'MM') <= mx.dernier_mois THEN 1 ELSE 0 END AS mois_paye,
    CASE WHEN g.annee_budg = mx.derniere_annee THEN 1 ELSE 0 END AS derniere_annee
FROM budget_global g
LEFT JOIN rubrique_budg r ON r.cod_rub_budg = g.cod_rub_budg
LEFT JOIN (
    SELECT v.cod_soc, ab.cod_rub_budg, TRUNC(v.dt_bul, 'MM') AS mois, SUM(v.montv) AS montant
    FROM possedevh v
    JOIN (SELECT DISTINCT cod_rub_budg, abrv_fixe FROM abrv_budg) ab ON ab.abrv_fixe = v.abrv_fixe
    WHERE v.dt_bul >= DATE '2014-01-01'
      AND EXISTS (SELECT 1 FROM bult_budg bb
                  WHERE bb.cod_rub_budg = ab.cod_rub_budg AND bb.cod_typ_bul = v.cod_typ_bul)
    GROUP BY v.cod_soc, ab.cod_rub_budg, TRUNC(v.dt_bul, 'MM')
) re ON re.cod_soc = g.cod_soc AND re.cod_rub_budg = g.cod_rub_budg AND re.mois = TRUNC(g.mois, 'MM')
CROSS JOIN (
    SELECT
        (SELECT TRUNC(MAX(dt_bul), 'MM') FROM bulletinh WHERE cod_typ_bul = 'BN') AS dernier_mois,
        (SELECT MAX(annee_budg) FROM budget_global) AS derniere_annee
    FROM dual
) mx
WHERE g.annee_budg >= 2015
