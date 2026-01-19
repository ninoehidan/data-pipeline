from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.providers.postgres.hooks.postgres import PostgresHook
from datetime import datetime
import pandas as pd
import io


def process_and_load():
    # 1. Ler o arquivo mais recente do MinIO
    s3_hook = S3Hook(aws_conn_id='minio_s3_conn')

    # Listar arquivos no bucket
    keys = s3_hook.list_keys(bucket_name='landing-zone', prefix='landing/')
    if not keys:
        raise ValueError("Nenhum arquivo encontrado no MinIO!")

    latest_key = sorted(keys)[-1]  # Pega o arquivo mais recente por nome/data
    print(f"Lendo o arquivo: {latest_key}")

    file_obj = s3_hook.get_key(latest_key, bucket_name='landing-zone')
    file_content = file_obj.get()['Body'].read().decode('utf-8')

    # 2. Transformação Simples com Pandas
    df = pd.read_csv(io.StringIO(file_content))
    df['dt_processamento'] = datetime.now()  # Adiciona timestamp de carga

    # 3. Carregar no Postgres
    pg_hook = PostgresHook(postgres_conn_id='postgres_dw')
    engine = pg_hook.get_sqlalchemy_engine()

    # Cria a tabela se não existir e insere os dados
    df.to_sql('monitoramento_cpu', engine, if_exists='append', index=False)
    print("Dados inseridos no Postgres com sucesso!")


with DAG(
    '02_load_minio_to_postgres',
    start_date=datetime(2026, 1, 7),
    schedule_interval=None,
    catchup=False
) as dag:

    load_task = PythonOperator(
        task_id='minio_to_postgres_task',
        python_callable=process_and_load
    )
