from kafka import KafkaConsumer
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from elasticsearch.exceptions import UnsupportedProductError
from itertools import islice
import hashlib
import os

from log_parser import load_templates, parse_line

es = Elasticsearch("http://localhost:9200") 

INDEX_NAME = "logs"
TEMPLATES_PATH = os.path.join('HDFS_v1', 'preprocessed', 'HDFS.log_templates.csv')
MAX_MESSAGES = None

# Explicit mapping — don't let ES auto-infer types (per Week 2 guidance:
# timestamp must be a real date field, keyword fields must not be
# analyzed/tokenized, or filtering and aggregation won't behave correctly).
INDEX_MAPPING = {
    "mappings": {
        "properties": {
            "timestamp": {"type": "date"},
            "level": {"type": "keyword"},
            "component_class": {"type": "keyword"},
            "component_inner": {"type": "keyword"},
            "block_id": {"type": "keyword"},
            "event_id": {"type": "keyword"},
            "message": {"type": "text"},
            "raw_line": {"type": "text"},
        }
    }
}


def ensure_index(index_name: str = INDEX_NAME):
    """Create the index with an explicit mapping if it doesn't exist yet."""
    if not es.indices.exists(index=index_name):
        es.indices.create(index=index_name, body=INDEX_MAPPING)
        print(f"Created index '{index_name}' with explicit mapping.")


def consume_logs(topic: str, group_id: str = 'log-consumer-group'):
    consumer = KafkaConsumer(
        topic,
        bootstrap_servers=['localhost:9092'],
        group_id=group_id,
        auto_offset_reset='earliest',
        enable_auto_commit=False,
        value_deserializer=lambda v: v.decode('utf-8')
    )
    return consumer


def doc_generator(consumer, templates, index_name: str,
                   unparsed_log_path: str = "unparsed_lines.log",
                   max_messages: int | None = None):
    """
    Yields bulk-indexing actions. Lines that fail to parse are logged
    to a separate file rather than silently dropped or crashing the
    consumer — worth reviewing that file periodically during Week 2
    testing to see if the envelope regex needs adjusting.
    """
    messages = consumer if max_messages is None else islice(consumer, max_messages)
    for message in messages:
        raw_line = message.value
        doc = parse_line(raw_line, templates)

        if doc is None:
            with open(unparsed_log_path, "a", encoding="utf-8") as f:
                f.write(raw_line + "\n")
            continue

        yield {
            "_index": index_name,
            "_id": hashlib.sha256(raw_line.encode('utf-8')).hexdigest(),
            "_source": doc,
        }


if __name__ == '__main__':
    topic = 'raw-logs'

    templates = load_templates(TEMPLATES_PATH)
    ensure_index(INDEX_NAME)
    consumer = consume_logs(topic)

    print(f"Consuming and parsing messages from topic '{topic}'...")

    try:
        # bulk() pulls from the generator and batches requests to ES
        # instead of issuing one HTTP call per line — matters once you
        # run this against the full dataset, not just the 1000-line sample.
        success_count, errors = bulk(
            es,
            doc_generator(consumer, templates, INDEX_NAME,
                          max_messages=MAX_MESSAGES),
            chunk_size=500,
            raise_on_error=False,
        )
        print(f"Indexed {success_count} documents.")
        if errors:
            print(f"{len(errors)} documents failed to index. First few:")
            for e in errors[:5]:
                print(e)
        consumer.commit()
    except UnsupportedProductError as e:
        print(f"Error connecting to Elasticsearch: {e}")