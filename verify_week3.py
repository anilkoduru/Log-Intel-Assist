#!/usr/bin/env python
"""Quick verification that Week 3 is complete"""

import chromadb
from elasticsearch import Elasticsearch

print("=" * 70)
print("WEEK 3 VERIFICATION")
print("=" * 70)

# Check Chroma
try:
    client = chromadb.PersistentClient(path='./chroma_db')
    collection = client.get_or_create_collection(name='hdfs_logs')
    chroma_count = collection.count()
    print(f"\n✓ Chroma DB Ready")
    print(f"  Embeddings: {chroma_count:,}")
except Exception as e:
    print(f"✗ Chroma Error: {e}")
    chroma_count = 0

# Check Elasticsearch
try:
    es = Elasticsearch('http://localhost:9200')
    result = es.cat.count(index='logs', format='json')
    es_count = int(result[0]['count'])
    print(f"✓ Elasticsearch Ready")
    print(f"  Documents: {es_count:,}")
except Exception as e:
    print(f"✗ Elasticsearch Error: {e}")
    es_count = 0

# Verify match
print(f"\n✓ MATCH: {chroma_count == es_count}")
print(f"  Chroma: {chroma_count:,}")
print(f"  ES:     {es_count:,}")

if chroma_count == es_count and chroma_count > 0:
    print("\n" + "=" * 70)
    print("✓✓✓ WEEK 3 CHECKPOINT PASSED ✓✓✓")
    print("=" * 70)
    print("\nREADY FOR WEEK 4: RAG SYSTEM")
    print("\nNext steps:")
    print("1. Download Ollama from https://ollama.ai")
    print("2. Run: ollama pull llama3.1:8b")
    print("3. Run: python test_rag.py")
    print("4. Run: python rag.py")
else:
    print("\n⚠ WARNING: Count mismatch or empty!")
