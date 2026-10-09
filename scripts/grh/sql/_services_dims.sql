WITH serv_tree AS (
    SELECT
        s.cod_soc,
        s.cod_serv,
        REGEXP_SUBSTR(SYS_CONNECT_BY_PATH(s.cod_serv, '/'), '[^/]+', 1, 2) AS cod_pole,
        REGEXP_SUBSTR(SYS_CONNECT_BY_PATH(s.cod_serv, '/'), '[^/]+', 1, 3) AS cod_dir
    FROM service s
    START WITH s.ser_cod_serv IS NULL OR s.ser_cod_serv = s.cod_serv
    CONNECT BY NOCYCLE PRIOR s.cod_serv = s.ser_cod_serv
        AND PRIOR s.cod_soc = s.cod_soc
        AND s.cod_serv <> s.ser_cod_serv
)
SELECT
    ss.cod_soc,
    ss.cod_serv,
    TRIM(ss.lib_serv) AS service,
    TRIM(COALESCE(sp.lib_serv, ss.lib_serv)) AS pole,
    TRIM(COALESCE(sd.lib_serv, sp.lib_serv, ss.lib_serv)) AS direction
FROM service ss
LEFT JOIN serv_tree t ON t.cod_soc = ss.cod_soc AND t.cod_serv = ss.cod_serv
LEFT JOIN service sp ON sp.cod_soc = t.cod_soc AND sp.cod_serv = t.cod_pole
LEFT JOIN service sd ON sd.cod_soc = t.cod_soc AND sd.cod_serv = t.cod_dir
