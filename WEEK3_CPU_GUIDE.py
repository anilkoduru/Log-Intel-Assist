#!/usr/bin/env python
"""
WEEK 3 EXECUTION GUIDE FOR CPU (NO GPU)
========================================

This script guides you through the full Week 3 process:
1. Load FULL HDFS dataset into Elasticsearch
2. Generate embeddings on CPU
3. Store in Chroma for semantic search

Expected time: 15-60 minutes (depending on dataset size and CPU)
"""

import sys
import os
from pathlib import Path

print("=" * 80)
print("WEEK 3: EMBEDDINGS + VECTOR SEARCH (CPU-ONLY MODE)")
print("=" * 80)

# Step 1: Check dataset size
print("\n[STEP 1] Dataset Analysis")
print("-" * 80)

hdfs_log = Path("HDFS_v1/HDFS.log")
if not hdfs_log.exists():
    print(f"✗ ERROR: {hdfs_log} not found!")
    sys.exit(1)

file_size_mb = hdfs_log.stat().st_size / (1024 * 1024)
print(f"✓ HDFS.log found")
print(f"  File size: {file_size_mb:.2f} MB")

# Count lines
with open(hdfs_log, 'r', encoding='utf-8', errors='replace') as f:
    line_count = sum(1 for _ in f)

print(f"  Total lines: {line_count:,}")

# Step 2: Explain the pipeline
print("\n[STEP 2] Pipeline Breakdown")
print("-" * 80)

print("""
STEP 2A: Run Producer (HDFS.log → Kafka)
   - Sends ALL log lines to Kafka topic 'raw-logs'
   - Expected time: ~1-5 minutes depending on I/O
   - Command: python producer.py
   
STEP 2B: Run Consumer (Kafka → Elasticsearch)
   - Consumes from Kafka, parses, indexes to ES
   - Expected time: ~2-10 minutes depending on CPU
   - Command: python consumer.py
   - Note: This will block and consume all messages
   
STEP 2C: Run Embeddings (Elasticsearch → Chroma)
   - Fetches all docs from ES
   - Generates embeddings on CPU (SLOW but works)
   - Expected time: ~5-20 minutes for {line_count:,} docs
   - Command: python embed_and_store.py
   - Speed: ~50-100 docs/second on modern CPU
""".format(line_count=line_count))

# Step 3: Quick start instructions
print("\n[STEP 3] Quick Start Instructions")
print("-" * 80)

print("""
TERMINAL 1 - Run Producer:
   (venv) PS C:\\...\\log-intel-assistant> python producer.py
   
   Expected output:
   Line 1: Sent to partition 0, offset 0
   Line 2: Sent to partition 0, offset 1
   Line 3: Sent to partition 0, offset 2
   ...
   Sent <N> lines from HDFS_v1/HDFS.log to topic 'raw-logs'.

TERMINAL 2 - Run Consumer (open NEW terminal):
   (venv) PS C:\\...\\log-intel-assistant> python consumer.py
   
   Expected output:
   Consuming and parsing messages from topic 'raw-logs'...
   Indexed <N> documents.
   ... [may show some failed documents - this is normal] ...

TERMINAL 1 (after producer finishes):
   (venv) PS C:\\...\\log-intel-assistant> python embed_and_store.py
   
   Expected output:
   ✓ Connected to Elasticsearch at localhost:9200
   ⚠ No GPU detected, using CPU (embeddings will be slower)
   ✓ Model loaded on device: cpu
   ✓ Total documents in Elasticsearch: <N>
   ⏳ Starting embedding process...
   [Progress bars and batch completion messages...]
   ✓ SUCCESS: Chroma is ready for semantic search!
""")

# Step 4: Timing estimates
print("\n[STEP 4] Timing Estimates (CPU-ONLY)")
print("-" * 80)

datasets = [
    (10000, "~2-3 min", "~2-3 min", "~5-10 min"),
    (50000, "~3-5 min", "~5-10 min", "~15-30 min"),
    (100000, "~5-10 min", "~10-20 min", "~30-60 min"),
]

print(f"\nFor {line_count:,} documents:\n")

if line_count <= 10000:
    idx = 0
elif line_count <= 50000:
    idx = 1
else:
    idx = 2

docs, prod_time, cons_time, emb_time = datasets[idx]
print(f"Estimated Times:")
print(f"  Producer (logs → Kafka):     {prod_time}")
print(f"  Consumer (Kafka → ES):       {cons_time}")  
print(f"  Embeddings (ES → Chroma):    {emb_time}")
print(f"  ────────────────────────────────────────")
print(f"  Total:                       20-60 minutes")

# Step 5: Monitor progress
print("\n[STEP 5] How to Monitor Progress")
print("-" * 80)

print("""
During Producer:
  - Watch the "Sent <N> lines" message
  - It prints first 3 lines, then finishes quietly
  
During Consumer:
  - Blocks and waits for Kafka messages
  - No progress shown (it's consuming in background)
  - Will print "Indexed <N> documents" when done
  - You can Ctrl+C to stop early
  
During Embeddings:
  - Shows progress bars for each batch
  - Shows "Added <N> vectors to Chroma (progress: X%, elapsed: Ys)"
  - Shows final count and success/warning messages
  - LEAVES YOU IN CONTROL - you can watch it happen
""")

# Step 6: Troubleshooting
print("\n[STEP 6] Troubleshooting")
print("-" * 80)

print("""
If Producer hangs:
  → Check if Kafka is running: docker ps
  → Check if bootstrap_servers is correct in producer.py

If Consumer hangs:
  → This is NORMAL - it's waiting for Kafka messages
  → Let producer finish first, then run consumer
  → Consumer will consume all messages, then exit

If Embeddings fail:
  → Check if Elasticsearch has documents: 
    curl http://localhost:9200/logs/_count
  → Check if Chroma path exists: dir chroma_db
  → Re-run: it has resume capability, picks up where it left off

If "No module named X" error:
  → Activate venv: venv\\Scripts\\Activate.ps1
  → Install missing: pip install <package>
""")

# Step 7: Success criteria
print("\n[STEP 7] Success Criteria")
print("-" * 80)

print(f"""
Producer ✓ when: You see "Sent {line_count:,} lines from HDFS_v1/HDFS.log"

Consumer ✓ when: You see "Indexed <N> documents" message

Embeddings ✓ when:
  ✓ Final Chroma collection count: {line_count:,}
  ✓ SUCCESS: Chroma is ready for semantic search!
  
If numbers don't match:
  → Check Elasticsearch: some logs might not parse correctly
  → Check unparsed_lines.log for logs that failed to parse
  → This is expected - HDFS logs can be irregular
""")

# Step 8: Next steps
print("\n[STEP 8] After Week 3 Complete")
print("-" * 80)

print("""
Once embeddings finish, you're ready for Week 4:

WEEK 4 - RAG LAYER (LLM Integration):
  1. Ensure Ollama is installed: ollama.com
  2. Pull a model: ollama pull llama3.1:8b
  3. Test manually: ollama run llama3.1:8b "hello"
  4. Install Python client: pip install ollama
  5. Create RAG script with:
     - Semantic search (Chroma)
     - LLM integration (Ollama)
     - Prompt engineering
  6. Ask questions over your logs!

Expected questions you'll be able to ask:
  - "What are the most common errors?"
  - "Summarize failures around timestamp X"
  - "Find logs related to connection timeouts"
  - "What happened to block_id <X>?"
""")

print("\n" + "=" * 80)
print("READY? Open a terminal and run:")
print("  (venv) python producer.py")
print("=" * 80 + "\n")
