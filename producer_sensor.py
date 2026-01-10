import json
import time
import random
from confluent_kafka import Producer

# Configuração da conexão
# Note que usamos a porta 9094 (Externa) e seu IP Fixo
config = {
    'bootstrap.servers': '192.168.0.106:9094',
    'client.id': 'sensor-notebook-batista'
}

# Inicializa o Produtor
producer = Producer(config)


# Função de callback para confirmar que a mensagem chegou ao Kafka
def delivery_report(err, msg):
    if err is not None:
        print(f"Falha ao entregar mensagem: {err}")
    else:
        print(f"Mensagem entregue ao tópico: {msg.topic()} [Partição: {msg.partition()}]")


print("Iniciando envio de dados... (Ctrl+C para parar)")

try:
    while True:
        # 1. Simula o dado do sensor
        dados = {
            "sensor_id": "KD-771-TEMP",
            "temperatura": round(random.uniform(35.0, 85.0), 2),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        # 2. Converte para JSON (Kafka só aceita bytes)
        payload = json.dumps(dados).encode('utf-8')

        # 3. Envia para o tópico que criamos
        producer.produce(
            topic='sensor-temperatura',
            value=payload,
            callback=delivery_report
        )

        # 4. Flush garante que a mensagem saia do buffer do Python e vá para o Kafka
        producer.flush()

        time.sleep(2)  # Espera 2 segundos para o próximo envio

except KeyboardInterrupt:
    print("\nParando produtor...")
