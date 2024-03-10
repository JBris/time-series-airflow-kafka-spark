from pyspark.sql import SparkSession

if __name__ == "__main__":
    spark = SparkSession.builder.remote("sc://localhost:7077").getOrCreate()
    spark.stop()

