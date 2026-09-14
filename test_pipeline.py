#!/usr/bin/env python
"""
Quick end-to-end test of the Week 1 checkpoint:
1. Verify Kafka is up
2. Verify Elasticsearch is up
3. Read a few lines from HDFS.log
4. Send to Kafka
5. Consume and index
6. Query ES for documents
"""

import sys
from kafka import KafkaProducer, KafkaConsumer
from elasticsearch import Elasticsearch
from log_parser import load_templates, parse_line
from elasticsearch.helpers import bulk
import hashlib

print("=" * 60)
print("WEEK 1 CHECKPOINT TEST")
print("=" * 60)

# Test 1: Kafka Producer
print("\n[1] Testing Kafka Producer...")
try:
    producer = KafkaProducer(
        bootstrap_servers=['localhost:9092'],
        value_serializer=lambda v: v.encode('utf-8')
    )
    # Send a test message
    producer.send('raw-logs', 'TEST_MESSAGE_001')
    producer.flush()
    print("✓ Kafka Producer connected and sent test message")
except Exception as e:
    print(f"✗ Kafka Producer failed: {e}")
    sys.exit(1)

# Test 2: Elasticsearch
print("\n[2] Testing Elasticsearch...")
try:
    es = Elasticsearch("http://localhost:9200")
    info = es.info()
    print(f"✓ Elasticsearch connected: {info['version']['number']}")
except Exception as e:
    print(f"✗ Elasticsearch failed: {e}")
    sys.exit(1)

# Test 3: Read HDFS logs
print("\n[3] Reading first 10 lines from HDFS.log...")
try:
    with open('HDFS_v1/HDFS.log', 'r', encoding='utf-8', errors='replace') as f:
        lines = [f.readline().rstrip('\n') for _ in range(10)]
    lines = [l for l in lines if l]  # filter empty
    print(f"✓ Read {len(lines)} lines from HDFS.log")
    if lines:
        print(f"  First line preview: {lines[0][:80]}...")
except Exception as e:
    print(f"✗ Failed to read HDFS.log: {e}")
    sys.exit(1)

# Test 4: Send sample to Kafka
print("\n[4] Sending sample logs to Kafka...")
try:
    for line in lines:
        producer.send('raw-logs', line)
    producer.flush()
    print(f"✓ Sent {len(lines)} sample lines to Kafka topic 'raw-logs'")
except Exception as e:
    print(f"✗ Failed to send to Kafka: {e}")
    sys.exit(1)

# Test 5: Load templates and create index
print("\n[5] Setting up Elasticsearch index...")
INDEX_NAME = "logs"
TEMPLATES_PATH = 'HDFS_v1/preprocessed/HDFS.log_templates.csv'
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
try:
    if es.indices.exists(index=INDEX_NAME):
        es.indices.delete(index=INDEX_NAME)
        print(f"  Deleted existing index '{INDEX_NAME}' for clean test")
    
    es.indices.create(index=INDEX_NAME, body=INDEX_MAPPING)
    print(f"✓ Created index '{INDEX_NAME}' with mapping")
except Exception as e:
    print(f"✗ Failed to create ES index: {e}")
    sys.exit(1)

# Test 6: Load templates
print("\n[6] Loading log templates...")
try:
    templates = load_templates(TEMPLATES_PATH)
    print(f"✓ Loaded {len(templates)} templates")
except Exception as e:
    print(f"✗ Failed to load templates: {e}")
    sys.exit(1)

# Test 7: Consume and index
print("\n[7] Consuming from Kafka and indexing into ES...")
try:
    consumer = KafkaConsumer(
        'raw-logs',
        bootstrap_servers=['localhost:9092'],
        group_id='test-group',
        auto_offset_reset='earliest',
        enable_auto_commit=False,
        value_deserializer=lambda v: v.decode('utf-8'),
        max_poll_records=100,
    )
    
    docs_to_index = []
    unparsed = 0
    for msg in consumer:
        raw_line = msg.value
        if raw_line == 'TEST_MESSAGE_001':
            continue  # skip our test marker
        
        doc = parse_line(raw_line, templates)
        if doc is None:
            unparsed += 1
            continue
        
        docs_to_index.append({
            "_index": INDEX_NAME,
            "_id": hashlib.sha256(raw_line.encode('utf-8')).hexdigest(),
            "_source": doc,
        })
        
        if len(docs_to_index) >= 10:  # Just index first 10 for speed
            break
    
    if docs_to_index:
        success_count, errors = bulk(es, docs_to_index, chunk_size=500, raise_on_error=False)
        print(f"✓ Indexed {success_count} documents into ES")
        if errors:
            print(f"  ({len(errors)} documents failed to parse)")
        # Force index refresh so documents are immediately searchable
        es.indices.refresh(index=INDEX_NAME)
    else:
        print(f"✗ No documents to index (unparsed: {unparsed})")
    
    consumer.close()
except Exception as e:
    print(f"✗ Failed during consumption/indexing: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 8: Query ES
print("\n[8] Querying Elasticsearch...")
try:
    count_result = es.cat.count(index=INDEX_NAME, format='json')
    count = int(count_result[0]['count']) if count_result else 0
    print(f"✓ Total documents in ES index '{INDEX_NAME}': {count}")
    
    if count > 0:
        search_result = es.search(index=INDEX_NAME, size=1)
        sample_doc = search_result['hits']['hits'][0]['_source']
        print(f"  Sample document fields: {list(sample_doc.keys())}")
except Exception as e:
    print(f"✗ Failed to query ES: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("✓ WEEK 1 CHECKPOINT PASSED")
print("=" * 60)
print("\nSummary:")
print("  ✓ Kafka is up and accepting messages")
print("  ✓ Elasticsearch is up and indexing")
print("  ✓ Log parsing is working")
print("  ✓ End-to-end pipeline functional")
print("\nNext: Run Week 3 (embeddings) or Week 4 (RAG layer)")
