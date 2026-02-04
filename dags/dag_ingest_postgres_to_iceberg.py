from airflow import DAG
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'baptista',
    'depends_on_past': False,
    'start_date': datetime(2026, 1, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'dag_ingest_postgres_to_iceberg',
    default_args=default_args,
    description='Ingestão histórica do Postgres para Iceberg (Silver Layer)',
    schedule_interval='@daily',
    catchup=False
) as dag:

    # O comando SparkSubmit envia as configurações que testamos no Jupyter
    ingest_task = SparkSubmitOperator(
        task_id='ingest_dag_run_history',
        application='/home/iceberg/notebooks/scripts/ingest_script.py',
        conn_id='spark_default',
        packages="org.apache.iceberg:iceberg-spark-runtime-3.4_2.12:1.3.1,org.projectnessie.nessie-integrations:nessie-spark-extensions-3.4_2.12:0.67.0,org.apache.hadoop:hadoop-aws:3.3.4,org.postgresql:postgresql:42.7.2",
        conf={
            "spark.driver.memory": "1g",
            "spark.executor.memory": "1g",
            "spark.sql.catalog.nessie": "org.apache.iceberg.spark.SparkCatalog",
            "spark.sql.catalog.nessie.catalog-impl": "org.apache.iceberg.nessie.NessieCatalog",
            "spark.sql.catalog.nessie.uri": "http://nessie:19120/api/v1",
            "spark.sql.catalog.nessie.ref": "main",
            "spark.sql.catalog.nessie.warehouse": "s3a://iceberg-bucket/",

            # TROCA IMPORTANTE AQUI:
            "spark.sql.catalog.nessie.io-impl": "org.apache.iceberg.hadoop.HadoopFileIO",

            # ADICIONE ESSAS LINHAS PARA O MINIO:
            "spark.hadoop.fs.s3a.endpoint": "http://minio:9000",
            "spark.hadoop.fs.s3a.access.key": "baptista",
            "spark.hadoop.fs.s3a.secret.key": "cygnusX-1book2",
            "spark.hadoop.fs.s3a.path.style.access": "true",
            "spark.hadoop.fs.s3a.impl": "org.apache.hadoop.fs.s3a.S3AFileSystem",
        },
        verbose=True
    )

    ingest_task
