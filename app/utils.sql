
-- GET HOW MANY TIMES EACH PLATE CROSS DIFERENTS RADARS IN A DAY

-- "RIP7E05", "RKE4D04", "KRY6H45", "LML7J28", "RHI1J07", "RIX8F58", "RHL1C74", "RJD4B47",
-- "KRY6683", "LTC7698", "RKE4D04", "RJT4I01", "RJM4F03", "RJN4186", "RKS4E69", "RIU4B25",
-- "KRY6705", "RKV8A21", "LTC7652", "KRY6711", "RHH2197", "RHL6A91", "RJZ4C33", "LTC7633",
-- "LML7913", "LML7935", "KRY6675", "KRY6H25", "RKS4G81", "RKQ8C98", "KYY5E76", "LTC7G68",
-- "LTC7G28", "LTC7G99", "KRY6G88", "KRY6G81", "RJD3J92", "RIX8E70", "RHL0G19", "RHP5G73",
-- "KXS6G36", "KXS6G41", "RKT4F48", "RKK4E45", "KYC6228", "RHL6A93", "RKH4H45", "RJD3J90",
-- "KRY6G73", "RKP4F95", "RIQ4C55", "RJO4D52", "RHH2J01", "RJL5C03", "LTC7G63", "KRY6H18",
-- "LTC7G39", "RJK8F42", "RHL6A89", "RKQ4J45", "RJN4J66", "RJP4H88", "RJA4E13", "LML7J28",
-- "LML7J43", "KRY6H42", "LTC7G40", "KRY6G93", "KXS6627", "RKD7G53", "RHL6A86", "RKI4F49",
-- "LTC7703", "KPT2F27"

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
