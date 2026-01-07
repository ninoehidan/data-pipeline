import pandas as pd
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
import io

# Simulando o consumo da Gold Zone
def ler_resultado_gold():
    # Conectamos ao MinIO (usando a mesma lógica do pipeline)
    s3_hook = S3Hook(aws_conn_id='minio_s3_conn')
    
    # Listamos os arquivos na Gold Zone
    bucket = 'gold-zone'
    arquivos = s3_hook.list_keys(bucket_name=bucket)
    
    if not arquivos:
        print("Gold Zone está vazia!")
        return

    # Pegamos o arquivo mais recente
    ultimo_arquivo = sorted(arquivos)[-1]
    print(f"--- Lendo arquivo Gold: {ultimo_arquivo} ---")

    # Baixamos o Parquet
    file_obj = s3_hook.get_key(ultimo_arquivo, bucket_name=bucket)
    data = file_obj.get()['Body'].read()
    
    # O Pandas lê o Parquet direto da memória
    df = pd.read_parquet(io.BytesIO(data))
    
    print("\nResultados Agregados (Média de Temperatura por Status):")
    print(df.to_string(index=False))

if __name__ == "__main__":
    ler_resultado_gold()
