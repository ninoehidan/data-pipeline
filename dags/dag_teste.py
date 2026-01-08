import pandas as pd
import boto3
import io


def ler_resultado_gold():
    # Conexão direta via Boto3 - funciona em qualquer lugar
    s3 = boto3.client('s3',
                      endpoint_url='http://192.168.0.106:9000',  # Porta de API do MinIO
                      aws_access_key_id='baptista',
                      aws_secret_access_key='cygnusX-1book2',
                      region_name='us-east-1')
    
    bucket = 'gold-zone'
    
    try:
        # Listar objetos para pegar o mais recente
        response = s3.list_objects_v2(Bucket=bucket)
        
        if 'Contents' not in response:
            print(f"O bucket '{bucket}' está vazio!")
            return

        # Ordenar por data de modificação para pegar o último Parquet gerado
        ultimo_arquivo = sorted(response['Contents'], key=lambda x: x['LastModified'])[-1]['Key']
        print(f"✅ Sucesso! Lendo arquivo: {ultimo_arquivo}")

        # Baixar o arquivo para a memória
        obj = s3.get_object(Bucket=bucket, Key=ultimo_arquivo)
        
        # O Pandas lê o Parquet usando a engine 'pyarrow' que você instalou
        df = pd.read_parquet(io.BytesIO(obj['Body'].read()))
        
        print("\n--- RELATÓRIO CAMADA GOLD ---")
        print(df.to_string(index=False))
        
    except Exception as e:
        print(f"❌ Erro ao acessar o MinIO: {e}")


if __name__ == "__main__":
    ler_resultado_gold()
