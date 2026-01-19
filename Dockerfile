FROM apache/airflow:2.7.1

# Usuário root apenas para garantir permissões se necessário, 
# mas a instalação é feita no ambiente do usuário airflow
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER airflow

# Instalação limpa sem cache para economizar espaço e evitar travamentos
RUN pip install --no-cache-dir \
    apache-airflow-providers-amazon \
    duckdb \
    confluent-kafka \
    pandas \
    pyarrow
