import json
from confluent_kafka import Consumer, Producer, KafkaError

# Configuração do Ambiente
BROKER = '192.168.0.106:9094'

# 1. Configurar o Consumer (Entrada)
conf_consumer = {
    'bootstrap.servers': BROKER,
    'group.id': 'sensor-processor-group',
    'auto.offset.reset': 'earliest'
}

# 2. Configurar o Producer (Saída para Alertas)
conf_producer = {'bootstrap.servers': BROKER}

consumer = Consumer(conf_consumer)
producer = Producer(conf_producer)


def delivery_report(err, msg):
    if err is not None:
        print(f'Erro ao enviar mensagem: {err}')


# Subscrever ao tópico original
consumer.subscribe(['sensor-temperatura'])

print("Stream Processor Nativo Iniciado...")

try:
    while True:
        msg = consumer.poll(1.0)  # Espera por dados

        if msg is None:
            continue

        if msg.error():
            if msg.error().code() == KafkaError._PARTITION_EOF:
                continue
            else:
                print(f"Erro: {msg.error()}", flush=True)
                break

        # --- LÓGICA DE PROCESSAMENTO (O "STREAM") ---
        data = json.loads(msg.value().decode('utf-8'))

        # Exemplo: Se temp > 35, enviamos para o tópico de alertas
        if data['temperatura'] > 35.0:
            print(f"ALERTA: {data['sensor_id']} com {data['temperatura']}°C", flush=True)

            # Enriquecendo o dado antes de enviar para o próximo tópico
            data['status'] = 'CRÍTICO'

            producer.produce(
                'sensor-alertas',
                value=json.dumps(data).encode('utf-8'),
                callback=delivery_report
            )

            producer.flush()  # Garante o envio imediato
        else:
            print(f"Sensor {data['sensor_id']}: {data['temperatura']}°C (Normal)", flush=True)

except KeyboardInterrupt:
    print("Terminando...", flush=True)
finally:
    consumer.close()
