{{ config(materialized='view') }}

SELECT
    date_trunc('hour', dt_processamento) as hora,
    nome as servidor,
    AVG(temperatura_cpu) as media_temperatura,
    MAX(temperatura_cpu) as pico_temperatura,
    COUNT(*) as total_leituras
FROM public.monitoramento_cpu
GROUP BY 1, 2
ORDER BY 1 DESC
