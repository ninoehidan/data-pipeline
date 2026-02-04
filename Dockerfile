FROM apache/airflow:2.7.1

USER root

# 1. Instalação de dependências de sistema:
# - procps: Resolve o erro "ps: command not found"
# - default-jre: Necessário para rodar o Spark/Java
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    procps \
    default-jre \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Configura o JAVA_HOME (importante para o Spark encontrar o Java)
ENV JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64

USER airflow

# 2. Instalação das bibliotecas Python
# Adicionei o pyspark para garantir que o ambiente Python reconheça as libs
RUN pip install --no-cache-dir \
    apache-airflow-providers-apache-spark \
    apache-airflow-providers-amazon \
    pyspark==3.4.1 \
    duckdb \
    confluent-kafka \
    pandas \
    pyarrow \
    requests \
    pika \
    dbt-core \
    dbt-postgres \
    dbt-duckdb
