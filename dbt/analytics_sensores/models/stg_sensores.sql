{{ config(materialized='view') }}

SELECT
    id,
    nome,
    status,
    temperatura_cpu,
    dt_processamento as data_leitura,
    -- Regra de negócio: Classificação baseada na temperatura real do Note-Dev
    CASE
        WHEN temperatura_cpu > 80 THEN 'Crítico (Thermal Throttling)'
        WHEN temperatura_cpu > 65 THEN 'Alerta (Carga Alta)'
        ELSE 'Normal'
    END as classificacao_termica
FROM public.monitoramento_cpu
