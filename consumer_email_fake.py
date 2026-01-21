import pika
import json

# Use o IP fixo para garantir que ele alcance o container do RabbitMQ
connection = pika.BlockingConnection(pika.ConnectionParameters(host='192.168.0.106'))
channel = connection.channel()

# O NOME DA FILA DEVE SER IGUAL AO DO PROCESSOR
channel.queue_declare(queue='alertas_criticos')


def callback(ch, method, properties, body):
    # Decodificando o JSON para ficar mais bonito no print
    try:
        data = json.loads(body.decode())
        print(f"📧 [EMAIL SERVICE] Alerta crítico: Sensor {data['sensor_id']} registrou {data['temperatura']}°C!")
    except Exception as e:
        print(f"📧 [EMAIL SERVICE] Alerta bruto: {body.decode()}/nErro: {e.message}")


# O NOME DA FILA AQUI TAMBÉM DEVE SER IGUAL
channel.basic_consume(queue='alertas_criticos', on_message_callback=callback, auto_ack=True)

print('📢 Aguardando alertas críticos no RabbitMQ...')
channel.start_consuming()
