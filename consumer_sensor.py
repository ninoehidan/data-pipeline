import json
from confluent_kafka import Consumer, KafkaError

# Configuração do Consumidor
config = {
    'bootstrap.servers': '192.168.0.106:9094',
    'group.id': 'grupo-estudo-dados',       # Identifica quem está lendo
    'auto.offset.reset': 'earliest'        # Começa a ler desde a primeira mensagem disponível
}

consumer = Consumer(config)
consumer.subscribe(['sensor-temperatura'])

print("Aguardando mensagens... (Ctrl+C para parar)")

try:
    while True:
        # Tenta ler uma mensagem do tópico (espera até 1 segundo)
        msg = consumer.poll(1.0)

        if msg is None:
            continue
        if msg.error():
            if msg.error().code() == KafkaError._PARTITION_EOF:
                continue
            else:
                print(f"Erro no Consumer: {msg.error()}")
                break

        # 1. Recebe os bytes e decodifica para String/JSON
        dados_raw = msg.value().decode('utf-8')
        dados = json.loads(dados_raw)

        # 2. Exibe o dado processado
        print("--- Novo Evento Recebido ---")
        print(f"Sensor: {dados['sensor_id']}")
        print(f"Temperatura: {dados['temperatura']}°C")
        print(f"Data/Hora: {dados['timestamp']}")

        # 3. Aqui entraria sua lógica de negócio (Ex: Salvar no DuckDB ou Postgres)

except KeyboardInterrupt:
    print("\nEncerrando consumidor...")
finally:
    consumer.close()
