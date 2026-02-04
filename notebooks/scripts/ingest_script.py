from pyspark.sql import SparkSession

# 1. Configuração da Sessão Spark (Engine do Iceberg)
spark = SparkSession.builder \
    .appName("PostgresToIceberg_Production") \
    .config("spark.sql.catalog.nessie", "org.apache.iceberg.spark.SparkCatalog") \
    .config("spark.sql.catalog.nessie.catalog-impl", "org.apache.iceberg.nessie.NessieCatalog") \
    .config("spark.sql.catalog.nessie.uri", "http://nessie:19120/api/v1") \
    .config("spark.sql.catalog.nessie.ref", "main") \
    .config("spark.sql.catalog.nessie.warehouse", "s3a://iceberg-bucket/") \
    .config("spark.sql.catalog.nessie.io-impl", "org.apache.iceberg.hadoop.HadoopFileIO") \
    .config("spark.sql.catalog.nessie.s3.endpoint", "http://minio:9000") \
    .config("spark.sql.catalog.nessie.s3.path-style-access", "true") \
    .config("spark.sql.catalog.nessie.s3.access-key-id", "baptista") \
    .config("spark.sql.catalog.nessie.s3.secret-access-key", "cygnusX-1book2") \
    .config("spark.sql.defaultCatalog", "nessie") \
    .getOrCreate()

# 2. Leitura do Postgres
df_postgres = spark.read \
    .format("jdbc") \
    .option("url", "jdbc:postgresql://postgres-db:5432/airflow_db") \
    .option("dbtable", "dag_run") \
    .option("user", "baptista") \
    .option("password", "cygnusX-1book2") \
    .option("driver", "org.postgresql.Driver") \
    .load()

# 3. Criação do Namespace e Escrita no Iceberg
print("📦 Iniciando gravação na Silver Layer...")
spark.sql("CREATE NAMESPACE IF NOT EXISTS nessie.silver_layer")

df_postgres.writeTo("nessie.silver_layer.airflow_dag_runs").createOrReplace()

# 4. Validação final para o Log do Airflow
print("✅ Sucesso! Amostra da tabela Iceberg:")
spark.sql("SELECT dag_id, run_type, state, start_date FROM nessie.silver_layer.airflow_dag_runs LIMIT 5").show()

spark.stop()
