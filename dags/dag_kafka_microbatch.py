from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import pandas as pd
import json
import os

# Configurações do Micro-batch
TOPIC = 'sensor-temperatura'
BOOTSTRAP_SERVER = '192.168.0.106:9094'  # Usando a porta externa configurada
OUTPUT_DIR = '/opt/airflow/dags/data'  # Pasta mapeada no seu volume


def consume_kafka_to_parquet():
    from confluent_kafka import Consumer

    c = Consumer({
        'bootstrap.servers': BOOTSTRAP_SERVER,
        'group.id': 'airflow-batch-consumer',
        'auto.offset.reset': 'earliest',
        'socket.timeout.ms': 5000,  # 5 segundos de timeout
        'reconnect.backoff.ms': 1000
    })

    c.subscribe([TOPIC])

    messages = []
    # Tenta coletar mensagens por até 10 segundos
    try:
        count = 0
        while count < 100:  # Limite de 100 mensagens por batch para teste
            msg = c.poll(1.0)
            if msg is None:
                break
            if msg.error():
                continue

            messages.append(json.loads(msg.value().decode('utf-8')))
            count += 1
    finally:
        c.close()

    if messages:
        df = pd.DataFrame(messages)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{OUTPUT_DIR}/bronze_sensors_{timestamp}.parquet"

        # Cria a pasta data se não existir
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        df.to_parquet(filename, index=False)
        print(f"Sucesso! {len(messages)} mensagens salvas em {filename}")
    else:
        print("Nenhuma mensagem nova no Kafka.")


default_args = {
    'owner': 'baptista',
    'start_date': datetime(2024, 1, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'dag_kafka_microbatch_bronze',
    default_args=default_args,
    description='Consome dados do Kafka e salva em Micro-batch Parquet',
    schedule_interval='*/10 * * * *',  # Roda a cada 10 minutos
    catchup=False
) as dag:

    task_consume = PythonOperator(
        task_id='consume_from_kafka',
        python_callable=consume_kafka_to_parquet
    )
