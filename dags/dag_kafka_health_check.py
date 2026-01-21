from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import requests
import pika
import json

# Configurações
KAFKA_CONNECT_URL = "http://192.168.0.106:8083/connectors/sink-elastic-sensores/status"
RABBITMQ_HOST = "192.168.0.106"
QUEUE_NAME = "alertas_sensores"


def send_rabbitmq_alert(message):
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
    channel = connection.channel()
    channel.queue_declare(queue=QUEUE_NAME, durable=True)

    alert_payload = {
        "status": "CRITICAL",
        "service": "Kafka Connect",
        "error": message,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    channel.basic_publish(
        exchange='',
        routing_key=QUEUE_NAME,
        body=json.dumps(alert_payload)
    )
    connection.close()


def check_kafka_connect_status():
    try:
        response = requests.get(KAFKA_CONNECT_URL, timeout=10)
        if response.status_code == 200:
            status = response.json()
            state = status['connector']['state']
            if state != 'RUNNING':
                send_rabbitmq_alert(f"Conector parado! Estado: {state}")
                raise Exception(f"Connector is in {state} state")
        else:
            send_rabbitmq_alert(f"Erro API Connect: {response.status_code}")
            raise Exception(f"API returned status {response.status_code}")
    except Exception as e:
        send_rabbitmq_alert(f"Falha Crítica no Connect: {str(e)}")
        raise


default_args = {
    'owner': 'baptista',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}


with DAG(
    'monitor_kafka_connect_health',
    default_args=default_args,
    description='Monitora o status do Sink Connector do Elasticsearch',
    schedule_interval=timedelta(minutes=5),  # Executa a cada 5 minutos
    catchup=False,
    tags=['monitoramento', 'kafka'],
) as dag:

    task_check_health = PythonOperator(
        task_id='check_kafka_connect_health',
        python_callable=check_kafka_connect_status,
    )
