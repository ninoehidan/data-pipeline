import requests
import json

# O endpoint do seu container Kafka Connect
CONNECT_URL = "http://localhost:8083/connectors"


def create_postgres_sink():
    """Configura o conector para enviar dados do Kafka para o Postgres (Silver)"""

    config = {
        "name": "sink_postgres_sensor_data",
        "config": {
            "connector.class": "io.confluent.connect.jdbc.JdbcSinkConnector",
            "tasks.max": "1",
            "topics": "sensor-temperatura",
            "connection.url": "jdbc:postgresql://postgres-db:5432/airflow_db",
            "connection.user": "baptista",
            "connection.password": "cygnusX-1book2",
            "insert.mode": "insert",
            "auto.create": "true",  # Cria a tabela se não existir
            "pk.mode": "none",
            "key.converter": "org.apache.kafka.connect.storage.StringConverter",
            "value.converter": "org.apache.kafka.connect.json.JsonConverter",
            "value.converter.schemas.enable": "false"
        }
    }

    headers = {"Content-Type": "application/json"}

    response = requests.post(CONNECT_URL, data=json.dumps(config), headers=headers)

    if response.status_code == 201:
        print("Conector criado com sucesso!", flush=True)
    elif response.status_code == 409:
        print("O conector já existe.", flush=True)
    else:
        print(f"Erro: {response.status_code} - {response.text}", flush=True)


def list_connectors():
    """Lista todos os conectores ativos"""
    response = requests.get(CONNECT_URL)
    print(f"Conectores ativos: {response.json()}")


if __name__ == "__main__":
    # Primeiro listamos, depois tentamos criar
    list_connectors()
    create_postgres_sink()
