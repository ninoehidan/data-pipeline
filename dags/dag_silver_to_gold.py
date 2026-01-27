from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from datetime import datetime
import io
import os


def export_gold_to_storage():
    import pandas as pd
    pg_hook = PostgresHook(postgres_conn_id='postgres_dw')

    # Lendo da VIEW Gold validada pelo dbt
    df_gold = pg_hook.get_pandas_df(sql="SELECT * FROM public.gold_uso_cpu_hourly")

    if df_gold.empty:
        print("Nenhum dado na View Gold.")
        return

    # Salvar no MinIO (S3)
    parquet_buffer = io.BytesIO()
    df_gold.to_parquet(parquet_buffer, index=False)
    s3_hook = S3Hook(aws_conn_id='minio_s3_conn')
    s3_hook.load_bytes(
        bytes_data=parquet_buffer.getvalue(),
        key="analise_cpu/media_temp_gold.parquet",
        bucket_name='gold-zone',
        replace=True
    )

    # Salvar LOCAL para DuckDB/CloudBeaver
    local_path = '/opt/airflow/dags/data/gold_monitor.parquet'
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    df_gold.to_parquet(local_path, index=False)
    print(f"Sucesso! Arquivo gerado em: {local_path}")


with DAG(
    '03_process_dbt_and_export_gold',
    start_date=datetime(2026, 1, 7),
    schedule_interval=None,
    catchup=False,
    tags=['dbt', 'gold', 'quality_check']
) as dag:

    # TASK 1: Transforma E Testa (Se o teste falhar, a DAG para aqui)
    run_dbt = BashOperator(
        task_id='run_and_test_dbt',
        bash_command=(
            "cd /opt/airflow/dbt/analytics_sensores && "
            "/home/airflow/.local/bin/dbt run --profiles-dir /opt/airflow/dbt && "
            "/home/airflow/.local/bin/dbt test --profiles-dir /opt/airflow/dbt"
        )
    )

    # TASK 2: Exporta apenas dados validados
    export_data = PythonOperator(
        task_id='export_gold_to_storage',
        python_callable=export_gold_to_storage
    )

    run_dbt >> export_data
