from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from datetime import datetime
import io
import os


def silver_to_gold():
    import pandas as pd

    # 1. Extrair (Postgres)
    pg_hook = PostgresHook(postgres_conn_id='postgres_dw')
    df = pg_hook.get_pandas_df(sql="SELECT * FROM monitoramento_cpu")

    if df.empty:
        print("Nenhum dado encontrado na Silver.")
        return

    # 2. Transformar
    df_gold = df.groupby('status')['temperatura_cpu'].mean().reset_index()
    df_gold.columns = ['status', 'media_temperatura']
    df_gold['dt_analise'] = datetime.now()

    # 3. Salvar no MinIO (S3)
    parquet_buffer = io.BytesIO()
    df_gold.to_parquet(parquet_buffer, index=False, engine='pyarrow')
    s3_hook = S3Hook(aws_conn_id='minio_s3_conn')

    # Removido o 'f' desnecessário para eliminar o aviso F541
    s3_hook.load_bytes(
        bytes_data=parquet_buffer.getvalue(),
        key="analise_cpu/media_temp_gold.parquet",
        bucket_name='gold-zone',
        replace=True
    )

    # 4. Salvar LOCALMENTE para o CloudBeaver ler via DuckDB
    # O CloudBeaver mapeia /home/baptista/projetos/data-pipeline/dags para /opt/airflow/dags/data
    local_path = '/opt/airflow/dags/data/gold_monitor.parquet'
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    df_gold.to_parquet(local_path, index=False)

    print(f"Sucesso! Arquivo gerado em: {local_path}")


with DAG(
    '03_process_silver_to_gold',
    start_date=datetime(2026, 1, 7),
    schedule_interval=None,
    catchup=False,
    tags=['gold', 'parquet']
) as dag:

    task_gold = PythonOperator(
        task_id='silver_to_gold_task',
        python_callable=silver_to_gold
    )
