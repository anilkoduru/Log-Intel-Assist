#!/usr/bin/env python
"""Diagnose current state of the pipeline"""

print("=" * 70)
print("PIPELINE DIAGNOSTICS")
print("=" * 70)

# Check Elasticsearch
print("\n[1] Checking Elasticsearch...")
try:
    from elasticsearch import Elasticsearch
    es = Elasticsearch("http://localhost:9200")
    info = es.info()
    print(f"✓ ES connected: v{info['version']['number']}")
    
    # Check if logs index exists
    indices = es.indices.get_alias(index="*")
    print(f"✓ Available indices: {list(indices.keys())}")
    
    # Check logs index specifically
    if es.indices.exists(index="logs"):
        count_result = es.cat.count(index="logs", format='json')
        count = int(count_result[0]['count']) if count_result else 0
        print(f"✓ Index 'logs' exists with {count:,} documents")
    else:
        print(f"✗ Index 'logs' does NOT exist")
        
except Exception as e:
    print(f"✗ Elasticsearch error: {e}")

# Check Kafka
print("\n[2] Checking Kafka...")
try:
    from kafka import KafkaConsumer
    consumer = KafkaConsumer(
        'raw-logs',
        bootstrap_servers=['localhost:9092'],
        group_id='diagnostic-group',
        auto_offset_reset='earliest',
        max_poll_records=1
    )
    # Try to get one message
    msg_count = 0
    for msg in consumer:
        msg_count += 1
        break
    consumer.close()
    print(f"✓ Kafka connected, topic 'raw-logs' has messages")
except Exception as e:
    print(f"✗ Kafka error: {e}")

# Check Chroma
print("\n[3] Checking Chroma...")
try:
    import chromadb
    client = chromadb.PersistentClient(path="./chroma_db")
    collections = client.list_collections()
    print(f"✓ Chroma connected, collections: {[c.name for c in collections]}")
    
    if collections:
        for collection in collections:
            count = collection.count()
            print(f"  - '{collection.name}': {count:,} embeddings")
    else:
        print(f"  No collections yet")
except Exception as e:
    print(f"✗ Chroma error: {e}")

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print("""
If you see:
✓ ES connected with 'logs' index having 0 documents
✗ Kafka has messages
→ Consumer didn't index the messages to ES

SOLUTION:
1. Re-run consumer.py
2. Check for error messages
3. Look at unparsed_lines.log to see what failed to parse
""")
