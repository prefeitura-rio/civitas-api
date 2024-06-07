
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
-- RHL6A86 | 0, 4, 5, 7, 8  *
-- RJN4J66 | 5, 6, 8, 9, 12 *
-- RIU4B25 | 0, 3, 13
-- RHL6A91 | 0, 1, 3, 
-- RJD3J90 | 0, 1, 7, 8, 
-- RKP4F95 | 0, 1, 2, 3
-- RJA4E13 | 1, 3, 4, 7, 9, 
-- RKS4G81 | 
-- RKK4E45 | 
-- RJZ4C33 | 
-- RJL5C03 | 
-- RKQ4J45 | 
-- RKI4F49 | 

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



-- RADARS ORVER TIME

WITH tb AS (
  SELECT 
    empresa,
    placa,
    camera_numero,
    CONCAT(camera_latitude, camera_longitude) AS position,
    DATETIME(datahora, "America/Sao_Paulo") AS datahora,
    TIMESTAMP_DIFF(datahora_captura, datahora, SECOND) / 60.0 AS datahora_diff_minutes,
  FROM `rj-cetrio.ocr_radar.readings_*`
  
),

radars_hour AS (
  SELECT 
    empresa,
    camera_numero,
    position,
    DATE_TRUNC(datahora, HOUR) AS datahora,
    COUNT(placa) quantidade_placas,
    COUNT(DISTINCT placa) quantidade_placas_unicas,
    AVG(datahora_diff_minutes) AS media_tempo_minutos,
    APPROX_QUANTILES(datahora_diff_minutes, 2)[OFFSET(1)] AS mediana_tempo_minutos,
  FROM tb
  GROUP BY 
    empresa,
    camera_numero,
    position,
    datahora
),

duplicates AS (
  SELECT 
    placa,
    camera_numero,
    empresa,
    position,
    datahora,
    COUNT(*) as occurrences
  FROM tb
  GROUP BY 
    placa,
    camera_numero,
    datahora,
    empresa,
    position
),

duplicates_hour AS (
  SELECT
    camera_numero,
    empresa,
    position,
    DATE_TRUNC(datahora, HOUR) AS datahora,
    SUM(occurrences) AS duplicate_occurrences_hour,
  FROM duplicates
  GROUP BY 1, 2, 3, 4
)

SELECT 
  t1.empresa,
  t1.camera_numero,
  t1.position,
  t1.datahora,
  t1.quantidade_placas,
  t1.quantidade_placas_unicas,
  t1.media_tempo_minutos,
  t1.mediana_tempo_minutos,
  t2.duplicate_occurrences_hour,
FROM radars_hour t1
JOIN duplicates_hour t2
  ON  t1.camera_numero = t2.camera_numero 
  AND t1.empresa = t2.empresa 
  AND t1.position = t2.position 
  AND t1.datahora = t2.datahora 
ORDER BY duplicate_occurrences_hour DESC



-- PLATES OVER TIME

SELECT 
  empresa,
  SUBSTR(SHA256(
        CONCAT(
            '',
            SAFE_CAST(REGEXP_REPLACE(placa, r'\.0$', '')  AS STRING)
        )
    ), 2,17) as  id,
  tipoveiculo,
  velocidade,
  camera_numero,
  CONCAT(camera_latitude, camera_longitude) AS position,
  DATETIME(datahora, "America/Sao_Paulo") AS datahora,
  COUNT(*) AS duplicates,
FROM `rj-cetrio.ocr_radar.readings_*`
GROUP BY 1,2,3,4,5,6,7




-- PLATES OVER TIME
WITH sample AS (
    SELECT 
      placa,
      tipoveiculo,
      velocidade,
      DATETIME(datahora, "America/Sao_Paulo") AS datahora,
      camera_numero,
      camera_latitude,
      camera_longitude,
      empresa,
      DATETIME(datahora_captura, "America/Sao_Paulo") AS datahora_captura,
      CASE
          WHEN camera_longitude BETWEEN -43.74818 AND -43.09615
            AND camera_latitude BETWEEN -23.06016 AND -22.74337
          THEN 1
          ELSE 0
      END AS inside_rio,
      ROW_NUMBER() OVER(PARTITION BY placa ORDER BY  DATETIME(datahora, "America/Sao_Paulo")) AS seq_num
    FROM `rj-cetrio.ocr_radar.readings_*`
    WHERE placa != ""
),

placas_duplicadas AS (
  SELECT 
    a.placa AS id,
    a.inside_rio AS inside_rio_a,
    b.inside_rio AS inside_rio_b,
    a.datahora AS datahora_a,
    b.datahora AS datahora_b,
    a.camera_numero AS camera_a,
    b.camera_numero AS camera_b,
    a.datahora_captura AS datahora_captura_a,
    b.datahora_captura AS datahora_captura_b,
    ST_GEOGPOINT(a.camera_longitude, a.camera_latitude) AS ponto_a,
    ST_GEOGPOINT(b.camera_longitude, b.camera_latitude) AS ponto_b,
    CONCAT(a.camera_latitude,a.camera_longitude) AS position_a,
    CONCAT(b.camera_latitude, b.camera_longitude) AS position_b,
    1.4 * ST_DISTANCE(ST_GEOGPOINT(a.camera_longitude, a.camera_latitude), ST_GEOGPOINT(b.camera_longitude, b.camera_latitude)) AS distancia,
    TIMESTAMP_DIFF(b.datahora, a.datahora, SECOND) AS diferenca_tempo_segundos,
    a.empresa AS empresa_a,
    b.empresa AS empresa_b
  FROM sample a
  JOIN sample b
  ON a.placa = b.placa
     # get only sequential detections
     AND a.seq_num + 1 = b.seq_num
     # must occur in a interval less then 1 hour
     AND TIMESTAMP_DIFF(b.datahora, a.datahora, SECOND) < 60 * 60
     # only dates that are in the same day
     AND TIMESTAMP_TRUNC(a.datahora, DAY) = TIMESTAMP_TRUNC(b.datahora, DAY) 
)

SELECT 
    id, 
    inside_rio_a,
    inside_rio_b,
    CASE
        WHEN inside_rio_a = 1 AND inside_rio_b = 1 THEN 1
        ELSE 0
    END AS inside_rio_ab,
    empresa_a,
    camera_a, 
    empresa_b,
    camera_b, 
    CONCAT(camera_a, " | ", camera_b) AS camera_ab,
    CONCAT(empresa_a, " | ", empresa_b) AS empresa_ab,
    datahora_a, 
    datahora_b,
    diferenca_tempo_segundos,
    datahora_captura_a,
    datahora_captura_b,
    TIMESTAMP_DIFF(datahora_captura_a, datahora_a, SECOND) AS time_diff_a,
    TIMESTAMP_DIFF(datahora_captura_b, datahora_b, SECOND) AS time_diff_b,
    distancia,
    3.6 * SAFE_DIVIDE(distancia, diferenca_tempo_segundos) AS velocidade_km_hora,
    position_a,
    position_b,
    ponto_a,
    ponto_b,
    CASE
      WHEN diferenca_tempo_segundos <= 10 THEN '1. 0-10 segundos'
      WHEN diferenca_tempo_segundos > 10 AND diferenca_tempo_segundos <= 30 THEN '2. 10-30 segundos'
      WHEN diferenca_tempo_segundos > 30 AND diferenca_tempo_segundos <= 60 THEN '3. 30-60 segundos'
      WHEN diferenca_tempo_segundos > 60 AND diferenca_tempo_segundos <= 60 * 2 THEN '4. 1-2 minutos'
      WHEN diferenca_tempo_segundos > 60 * 2 AND diferenca_tempo_segundos <= 60 * 5 THEN '5. 2-5 minutos'
      WHEN diferenca_tempo_segundos > 60 * 5 AND diferenca_tempo_segundos <= 60 * 10 THEN '6. 5-10 minutos'
      WHEN diferenca_tempo_segundos > 60 * 10 AND diferenca_tempo_segundos <= 60 * 30 THEN '7. 10-30 minutos'
      WHEN diferenca_tempo_segundos > 60 * 30 AND diferenca_tempo_segundos <= 60 * 60 THEN '8. 30-60 minutos'
      WHEN diferenca_tempo_segundos > 60 * 60 AND diferenca_tempo_segundos <= 60 * 60 *2 THEN '9. 1-2 horas'
      WHEN diferenca_tempo_segundos > 60 * 60 *2 AND diferenca_tempo_segundos <= 60 * 60 *5 THEN '10. 2-5 horas'
      ELSE '11. >5 horas'
  END AS bin_diferenca_tempo_segundos,
  CASE
      WHEN 3.6 * SAFE_DIVIDE(distancia, diferenca_tempo_segundos) <= 200 THEN '0-200 km/h'
      WHEN 3.6 * SAFE_DIVIDE(distancia, diferenca_tempo_segundos) > 200 AND 3.6 * SAFE_DIVIDE(distancia, diferenca_tempo_segundos) <= 250 THEN '0. 200-250 km/h'
      WHEN 3.6 * SAFE_DIVIDE(distancia, diferenca_tempo_segundos) > 250 AND 3.6 * SAFE_DIVIDE(distancia, diferenca_tempo_segundos) <= 300 THEN '1. 250-300 km/h'
      WHEN 3.6 * SAFE_DIVIDE(distancia, diferenca_tempo_segundos) > 300 AND 3.6 * SAFE_DIVIDE(distancia, diferenca_tempo_segundos) <= 400 THEN '2. 300-400 km/h'
      WHEN 3.6 * SAFE_DIVIDE(distancia, diferenca_tempo_segundos) > 400 AND 3.6 * SAFE_DIVIDE(distancia, diferenca_tempo_segundos) <= 500 THEN '3. 400-500 km/h'
      WHEN 3.6 * SAFE_DIVIDE(distancia, diferenca_tempo_segundos) > 500 AND 3.6 * SAFE_DIVIDE(distancia, diferenca_tempo_segundos) <= 750 THEN '4. 500-750 km/h'
      WHEN 3.6 * SAFE_DIVIDE(distancia, diferenca_tempo_segundos) > 750 AND 3.6 * SAFE_DIVIDE(distancia, diferenca_tempo_segundos) <= 1000 THEN '5. 750-1000 km/h'
      WHEN 3.6 * SAFE_DIVIDE(distancia, diferenca_tempo_segundos) > 1000 AND 3.6 * SAFE_DIVIDE(distancia, diferenca_tempo_segundos) <= 5000 THEN '6. 1-5 mil km/h'
      WHEN 3.6 * SAFE_DIVIDE(distancia, diferenca_tempo_segundos) > 5000 AND 3.6 * SAFE_DIVIDE(distancia, diferenca_tempo_segundos) <= 10000 THEN '7. 5-10 mil km/h'
      WHEN 3.6 * SAFE_DIVIDE(distancia, diferenca_tempo_segundos) > 10000 AND 3.6 * SAFE_DIVIDE(distancia, diferenca_tempo_segundos) <= 50000 THEN '8. 10-50 mil km/h'
      ELSE '9. >50 mil km/h'
  END AS bin_velocidade,
FROM placas_duplicadas
WHERE 
  3.6 * SAFE_DIVIDE(distancia, diferenca_tempo_segundos) > 250
ORDER BY datahora_a;