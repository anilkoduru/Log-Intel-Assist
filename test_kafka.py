#!/usr/bin/env python
"""Quick test to verify Kafka connectivity and template loading."""

import os
from kafka import KafkaConsumer
from log_parser import load_templates

TEMPLATES_PATH = os.path.join('HDFS_v1', 'preprocessed', 'HDFS.log_templates.csv')

# Test 1: Load templates
print("Testing template loading...")
templates = load_templates(TEMPLATES_PATH)
print(f"Loaded {len(templates)} templates")
for i, (eid, regex) in enumerate(templates[:3]):
    print(f"  Template {i+1}: {eid}")

# Test 2: Check Kafka connection and read a few messages
print("\nTesting Kafka consumer...")
consumer = KafkaConsumer(
    'raw-logs',
    bootstrap_servers=['localhost:9092'],
    group_id='test-group',
    auto_offset_reset='earliest',
    value_deserializer=lambda v: v.decode('utf-8'),
    max_poll_records=5,
    session_timeout_ms=10000,
)

print("Reading messages from Kafka...")
message_count = 0
for msg in consumer:
    message_count += 1
    print(f"Message {message_count}: {msg.value[:80]}")
    if message_count >= 3:
        break

consumer.close()
print(f"Successfully read {message_count} messages from Kafka.")
