import json
from confluent_kafka import Consumer, Producer, KafkaError
import pika

# Configuração do Ambiente
BROKER = '192.168.0.106:9094'
RABBIT_HOST = '192.168.0.106'

# --- 1. CONFIGURAR RABBITMQ ---
try:
    rb_conn = pika.BlockingConnection(pika.ConnectionParameters(host=RABBIT_HOST))
    rb_channel = rb_conn.channel()
    rb_channel.queue_declare(queue='alertas_criticos')
    print("✅ Conectado ao RabbitMQ")
except Exception as e:
    print(f"❌ Erro ao conectar no RabbitMQ: {e}")
    rb_channel = None

# 2. Configurar o Consumer (Entrada Kafka)
conf_consumer = {
    'bootstrap.servers': BROKER,
    'group.id': 'sensor-processor-group',
    'auto.offset.reset': 'earliest'
}

# 3. Configurar o Producer (Saída Kafka)
conf_producer = {'bootstrap.servers': BROKER}

consumer = Consumer(conf_consumer)
producer = Producer(conf_producer)


def delivery_report(err, msg):
    if err is not None:
        print(f'Erro ao enviar mensagem no Kafka: {err}')


consumer.subscribe(['sensor-temperatura'])

print("🚀 Stream Processor Nativo Iniciado (Kafka + RabbitMQ)...")

try:
    while True:
        msg = consumer.poll(1.0)

        if msg is None:
            continue

        if msg.error():
            if msg.error().code() == KafkaError._PARTITION_EOF:
                continue
            else:
                print(f"Erro: {msg.error()}", flush=True)
                break

        data = json.loads(msg.value().decode('utf-8'))

        if data['temperatura'] > 35.0:
            print(f"🔥 ALERTA: {data['sensor_id']} com {data['temperatura']}°C", flush=True)
            data['status'] = 'CRÍTICO'

            # --- AÇÃO 1: Enviar para o Kafka (Tópico de Alertas/Silver) ---
            producer.produce(
                'sensor-alertas',
                value=json.dumps(data).encode('utf-8'),
                callback=delivery_report
            )
            producer.flush()

            # --- AÇÃO 2: Enviar para o RabbitMQ (Disparo de Notificação) ---
            if rb_channel:
                rb_channel.basic_publish(
                    exchange='',
                    routing_key='alertas_criticos',
                    body=json.dumps(data)
                )
        else:
            print(f"✅ Sensor {data['sensor_id']}: {data['temperatura']}°C (Normal)", flush=True)

except KeyboardInterrupt:
    print("Terminando...", flush=True)
finally:
    if rb_channel:
        rb_conn.close()

    consumer.close()
