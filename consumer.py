from kafka import KafkaConsumer
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import UnsupportedProductError

es = Elasticsearch("http://localhost:9200")


def consume_logs(topic: str, group_id: str = 'log-consumer-group'):
    consumer = KafkaConsumer(
        topic,
        bootstrap_servers=['localhost:9092'],
        group_id=group_id,
        value_deserializer=lambda v: v.decode('utf-8')
    )
    return consumer

if __name__ == '__main__':
    topic = 'raw-logs'
    consumer = consume_logs(topic)

    print(f"Consuming messages from topic '{topic}'...")
    for message in consumer:
        log_entry = message.value
        try:
            es.index(index='logs', body={'message': log_entry})
            print("Log entry indexed in Elasticsearch.")
        except UnsupportedProductError as e:
            print(f"Error indexing log entry: {e}")