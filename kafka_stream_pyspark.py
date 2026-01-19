from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, window, avg
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, TimestampType

# 1. Iniciar a Sessão Spark com suporte ao Kafka
spark = SparkSession.builder \
    .appName("KafkaSensorWindowing") \
    .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0") \
    .getOrCreate()

# 2. Definir o Schema do JSON que vem do Kafka
schema = StructType([
    StructField("sensor_id", StringType()),
    StructField("temperatura", DoubleType()),
    StructField("timestamp", TimestampType())
])

# 3. Ler o Fluxo do Kafka (O "Stream")
raw_df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "192.168.0.106:9094") \
    .option("subscribe", "sensor-temperatura") \
    .load()

# 4. Converter os bytes do Kafka para Colunas
sensor_df = raw_df.selectExpr("CAST(value AS STRING)") \
    .select(from_json(col("value"), schema).alias("data")) \
    .select("data.*")

# 5. Janelamento: Média de 1 minuto, atualizada a cada 30 segundos
windowed_avg = sensor_df \
    .groupBy(
        window(col("timestamp"), "1 minute", "30 seconds"),
        col("sensor_id")
    ) \
    .agg(avg("temperatura").alias("media_temperatura"))

# 6. Escrever o resultado no console (ou de volta para o Kafka)
query = windowed_avg.writeStream \
    .outputMode("complete") \
    .format("console") \
    .start()

query.awaitTermination()
