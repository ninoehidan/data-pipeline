import requests
import pika
import json
import time

# Configurações
KAFKA_CONNECT_URL = "http://192.168.0.106:8083/connectors/sink-elastic-sensores/status"
RABBITMQ_HOST = "192.168.0.106"
QUEUE_NAME = "alertas_sensores"


def send_alert(message):
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
    channel = connection.channel()
    channel.queue_declare(queue=QUEUE_NAME, durable=True)

    alert_payload = {
        "status": "CRITICAL",
        "service": "Kafka Connect",
        "error": message,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    channel.basic_publish(
        exchange='',
        routing_key=QUEUE_NAME,
        body=json.dumps(alert_payload)
    )
    connection.close()
    print(f" [!] Alerta enviado: {message}")


def check_health():
    try:
        response = requests.get(KAFKA_CONNECT_URL, timeout=5)
        if response.status_code == 200:
            status = response.json()
            state = status['connector']['state']
            if state != 'RUNNING':
                send_alert(f"Conector parado! Estado atual: {state}")
        else:
            send_alert(f"Erro na API do Connect: Status {response.status_code}")
    except Exception as e:
        send_alert(f"Kafka Connect inacessível: {str(e)}")


if __name__ == "__main__":
    print("[*] Monitor de saúde iniciado...")
    while True:
        check_health()
        time.sleep(60)  # Verifica a cada 1 minuto
