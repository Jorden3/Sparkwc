#!/usr/bin/python
"""BigQuery I/O PySpark example."""
import json
import pprint
import subprocess
import pyspark

sc = pyspark.SparkContext()

# Use the Google Cloud Storage bucket for temporary BigQuery export data used
# by the InputFormat. This assumes the Google Cloud Storage connector for
# Hadoop is configured.
bucket = sc._jsc.hadoopConfiguration().get('fs.gs.system.bucket')
project = sc._jsc.hadoopConfiguration().get('fs.gs.project.id')
#input_directory = 'gs://{}/hadoop/tmp/bigquery/pyspark_input'.format(bucket)
input_directory = 'gs://dataproc-ce38408e-9214-4e9d-b5a4-d725cf0b6355-us/hadoop/tmp/bigquery/pyspark_input'.format(bucket)

conf = {
    # Input Parameters
    'mapred.bq.project.id': project,
    'mapred.bq.gcs.bucket': bucket,
    'mapred.bq.temp.gcs.path': input_directory,
    'mapred.bq.input.project.id': 'assignment4-167412',
    'mapred.bq.input.dataset.id': 'Harry',
    'mapred.bq.input.table.id': 'Characters',
}

# Output Parameters
#output_dataset = 'wordcount_dataset'
#output_table = 'wordcount_table'
output_dataset = 'Harry'
output_table = 'Last_Name_Ocurrance'

# Load data in from BigQuery.
table_data = sc.newAPIHadoopRDD(
    'com.google.cloud.hadoop.io.bigquery.JsonTextBigQueryInputFormat',
    'org.apache.hadoop.io.LongWritable',
    'com.google.gson.JsonObject',
    conf=conf)

# Perform word count.
word_counts = (
    table_data
    .map(lambda (_, record): json.loads(record))
    .map(lambda x: (x['lastName'].lower(), int(x['count'])))
    .reduceByKey(lambda x, y: x + y))

# Display 10 results.
pprint.pprint(word_counts.take(10))

# Stage data formatted as newline-delimited JSON in Google Cloud Storage.
output_directory = 'gs://dataproc-ce38408e-9214-4e9d-b5a4-d725cf0b6355-us/hadoop/tmp/bigquery/pyspark_output'.format(bucket)
partitions = range(word_counts.getNumPartitions())
output_files = [output_directory + '/part-{:05}'.format(i) for i in partitions]

(word_counts
 .map(lambda (w, c): json.dumps({'lastName': w, 'count': c}))
 .saveAsTextFile(output_directory))

# Shell out to bq CLI to perform BigQuery import.
subprocess.check_call(
    'bq load --source_format NEWLINE_DELIMITED_JSON '
    '--schema lastName:STRING,count:INTEGER '
    '{dataset}.{table} {files}'.format(
        dataset=output_dataset, table=output_table, files=','.join(output_files)
    ).split())

# Manually clean up the staging_directories, otherwise BigQuery
# files will remain indefinitely.
input_path = sc._jvm.org.apache.hadoop.fs.Path(input_directory)
input_path.getFileSystem(sc._jsc.hadoopConfiguration()).delete(input_path, True)
output_path = sc._jvm.org.apache.hadoop.fs.Path(output_directory)
output_path.getFileSystem(sc._jsc.hadoopConfiguration()).delete(
    output_path, True)