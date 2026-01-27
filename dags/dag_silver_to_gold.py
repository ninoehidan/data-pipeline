from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator  # Para rodar o dbt
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from datetime import datetime
import io
import os


def export_gold_to_storage():
    import pandas as pd
    pg_hook = PostgresHook(postgres_conn_id='postgres_dw')

    # AGORA: Lemos da VIEW que o dbt criou, não da tabela bruta!
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

    # Salvar LOCALMENTE para o CloudBeaver/DuckDB
    local_path = '/opt/airflow/dags/data/gold_monitor.parquet'
    df_gold.to_parquet(local_path, index=False)


with DAG(
    '03_process_dbt_and_export_gold',
    start_date=datetime(2026, 1, 7),
    schedule_interval=None,
    catchup=False,
    tags=['dbt', 'gold']
) as dag:

    # TASK 1: O Airflow manda o dbt trabalhar
    # Usamos o caminho completo do executável dentro do container
    run_dbt = BashOperator(
        task_id='run_dbt_models',
        bash_command=(
            "cd /opt/airflow/dbt/analytics_sensores && "
            "/home/airflow/.local/bin/dbt run --profiles-dir /opt/airflow/dbt"
        )
    )

    # TASK 2: Exporta o resultado do dbt para Parquet/MinIO
    export_data = PythonOperator(
        task_id='export_gold_to_storage',
        python_callable=export_gold_to_storage
    )

    run_dbt >> export_data
