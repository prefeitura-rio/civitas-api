
-- GET HOW MANY TIMES EACH PLATE CROSS DIFERENTS RADARS IN A DAY
WITH tb AS (
SELECT 
    placa,
    DATE_TRUNC(DATETIME(datahora,"America/Sao_Paulo"), DAY) AS data,
    COUNT(DISTINCT CONCAT(camera_latitude,camera_longitude)) AS quantidade_pontos_distintos,
    MIN(DATETIME(datahora,"America/Sao_Paulo")) start_date,
    MAX(DATETIME(datahora,"America/Sao_Paulo")) end_date,
FROM `rj-cetrio.ocr_radar.readings_*` 
WHERE datahora > '2024-06-03'
GROUP BY 1, 2
ORDER BY 3 DESC
)

SELECT 
  *
FROM tb
WHERE  quantidade_pontos_distintos >= 5
    AND quantidade_pontos_distintos <= 10
