from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from datetime import datetime
import pandas as pd
import io

def upload_to_minio():
    # 1. Criar um dado de teste (Simulando uma extração)
    df = pd.DataFrame({
        "id": [1, 2, 3],
        "nome": ["Note-Dev", "Airflow", "MinIO"],
        "status": ["Online", "Active", "Cool"],
        "temperatura_cpu": [42, 42, 42]
    })
    
    # 2. Converter para CSV na memória
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    
    # 3. Conectar ao MinIO usando a sua Connection Id
    # Usamos o S3Hook pois o MinIO é compatível com o protocolo S3
    s3_hook = S3Hook(aws_conn_id='minio_s3_conn')
    
    # 4. Enviar o arquivo para o bucket que você criou
    s3_hook.load_string(
        string_data=csv_buffer.getvalue(),
        key=f"landing/teste_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        bucket_name='landing-zone',
        replace=True
    )
    print("Arquivo enviado com sucesso para o MinIO!")

with DAG(
    dag_id='01_teste_data_lake_minio',
    start_date=datetime(2026, 1, 7),
    schedule_interval=None,
    catchup=False,
    tags=['setup', 'minio']
) as dag:

    upload_task = PythonOperator(
        task_id='upload_csv_para_minio',
        python_callable=upload_to_minio
    )
