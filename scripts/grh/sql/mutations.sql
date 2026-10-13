SELECT
    m.cod_soc,
    m.mat_pers,
    e.nom_prenom,
    e.sexe,
    e.categorie,
    e.grade,
    e.est_actif,
    NVL(TRIM(r.lib_rais), 'Non renseigné') AS raison,
    NVL(so.direction, 'Non renseigné') AS direction_origine,
    NVL(sn.direction, 'Non renseigné') AS direction_destination,
    'De : ' || NVL(so.direction, 'Non renseigné') AS flux_origine,
    'Vers : ' || NVL(sn.direction, 'Non renseigné') AS flux_destination,
    NVL(so.service, 'Non renseigné') AS service_origine,
    NVL(sn.service, 'Non renseigné') AS service_destination,
    NVL(sn.pole, 'Non renseigné') AS pole,
    NVL(sn.direction, 'Non renseigné') AS direction,
    CASE WHEN NVL(so.direction, '-') <> NVL(sn.direction, '-') THEN 1 ELSE 0 END AS change_direction,
    m.dat_mut,
    TO_CHAR(m.dat_mut, 'YYYY') AS annee,
    m.num_decision
FROM mutation m
LEFT JOIN raison_mutation r ON r.cod_rais = m.cod_rais
LEFT JOIN (
{services}
) so ON so.cod_soc = m.cod_soc AND so.cod_serv = m.cod_serv
LEFT JOIN (
{services}
) sn ON sn.cod_soc = m.cod_soc AND sn.cod_serv = m.ncod_serv
LEFT JOIN (
{personnel}
) e ON e.cod_soc = m.cod_soc AND e.mat_pers = m.mat_pers
WHERE m.dat_mut IS NOT NULL
