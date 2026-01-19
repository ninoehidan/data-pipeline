import json
from confluent_kafka import Consumer, Producer
from collections import deque

# Configurações
BROKER = '192.168.0.106:9094'
WINDOW_SIZE = 5  # Tamanho da janela (5 mensagens)

# Dicionário para armazenar as últimas leituras de cada sensor
# Ex: {'sensor_01': deque([22.5, 23.0, ...], maxlen=5)}
sensor_windows = {}

conf_consumer = {'bootstrap.servers': BROKER, 'group.id': 'window-group', 'auto.offset.reset': 'earliest'}
conf_producer = {'bootstrap.servers': BROKER}

consumer = Consumer(conf_consumer)
producer = Producer(conf_producer)
consumer.subscribe(['sensor-temperatura'])

print(f"Iniciando Processamento com Janela de {WINDOW_SIZE} mensagens...", flush=True)

try:
    while True:
        msg = consumer.poll(1.0)
        if msg is None or msg.error():
            continue

        data = json.loads(msg.value().decode('utf-8'))
        s_id = data['sensor_id']
        temp = data['temperatura']

        # 1. Gerenciar a Janela por Sensor
        if s_id not in sensor_windows:
            sensor_windows[s_id] = deque(maxlen=WINDOW_SIZE)

        sensor_windows[s_id].append(temp)

        # 2. Processar a Janela (Cálculo de Média Móvel)
        if len(sensor_windows[s_id]) == WINDOW_SIZE:
            avg_temp = sum(sensor_windows[s_id]) / WINDOW_SIZE

            # 3. Lógica de Negócio sobre a Janela
            status = "NORMAL"
            if avg_temp > 30.0:
                status = "ALERTA: MEDIA ALTA"

            output = {
                "sensor_id": s_id,
                "media_movel": round(avg_temp, 2),
                "leituras_na_janela": list(sensor_windows[s_id]),
                "status": status
            }

            print(f"Janela Completa [{s_id}]: Média {output['media_movel']}°C | {status}", flush=True)

            # Enviar o resultado agregado para um tópico "Gold" de streaming
            producer.produce('sensor-medias-moveis', value=json.dumps(output).encode('utf-8'))
            producer.flush()

except KeyboardInterrupt:
    print("Parando...", flush=True)
finally:
    consumer.close()
