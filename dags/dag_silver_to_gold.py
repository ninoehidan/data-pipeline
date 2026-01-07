from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from datetime import datetime
import pandas as pd
import io

def silver_to_gold():
    # 1. Extrair dados da Silver (Postgres)
    pg_hook = PostgresHook(postgres_conn_id='postgres_dw')
    df = pg_hook.get_pandas_df(sql="SELECT * FROM monitoramento_cpu")
    
    if df.empty:
        print("Nenhum dado encontrado na Silver.")
        return

    # 2. Transformação Gold (Agregação/Refinamento)
    # Exemplo: Vamos calcular a média de temperatura por status
    df_gold = df.groupby('status')['temperatura_cpu'].mean().reset_index()
    df_gold.columns = ['status', 'media_temperatura']
    df_gold['dt_analise'] = datetime.now()

    # 3. Converter para Parquet na memória
    parquet_buffer = io.BytesIO()
    df_gold.to_parquet(parquet_buffer, index=False, engine='pyarrow')
    
    # 4. Salvar na Gold Zone (MinIO)
    s3_hook = S3Hook(aws_conn_id='minio_s3_conn')
    s3_hook.load_bytes(
        bytes_data=parquet_buffer.getvalue(),
        key=f"analise_cpu/media_temp_{datetime.now().strftime('%Y%m%d_%H%M')}.parquet",
        bucket_name='gold-zone',
        replace=True
    )
    print("Dado Gold (Parquet) disponibilizado com sucesso!")

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
