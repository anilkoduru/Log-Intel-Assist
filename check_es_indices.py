#!/usr/bin/env python
"""Check all Elasticsearch indices to find your data"""

from elasticsearch import Elasticsearch

print("=" * 70)
print("ELASTICSEARCH INDEX SCAN")
print("=" * 70)

try:
    es = Elasticsearch("http://localhost:9200")
    
    # Get all indices
    indices = es.indices.get_alias(index="*")
    
    if not indices:
        print("\n✗ No indices found in Elasticsearch")
    else:
        print(f"\n✓ Found {len(indices)} indices:\n")
        
        for idx_name in sorted(indices.keys()):
            # Skip system indices
            if idx_name.startswith('.'):
                continue
                
            try:
                # Get document count
                count_result = es.cat.count(index=idx_name, format='json')
                count = int(count_result[0]['count']) if count_result else 0
                
                # Get index size
                stats = es.indices.stats(index=idx_name)
                size_bytes = stats['indices'][idx_name]['primaries']['store']['size_in_bytes']
                size_mb = size_bytes / (1024 * 1024)
                
                print(f"Index: '{idx_name}'")
                print(f"  Documents: {count:,}")
                print(f"  Size: {size_mb:.2f} MB")
                
                # Show some fields if it's not empty
                if count > 0:
                    try:
                        result = es.search(index=idx_name, size=1)
                        if result['hits']['hits']:
                            doc = result['hits']['hits'][0]['_source']
                            print(f"  Fields: {list(doc.keys())}")
                    except:
                        pass
                print()
            except Exception as e:
                print(f"  Error checking index: {e}\n")
    
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("""
If you see an index with 800K+ documents:
  → That's your old data!
  → You can query it directly or re-run embedding from it

If only 'logs' index exists with 0 documents:
  → Your data was deleted during the Week 1 test
  → Need to re-index from Kafka or re-run producer

If you see other indices (logs-2024, logs-old, etc):
  → Check if your data is in one of those
  → You can re-index from that index
""")
    
except Exception as e:
    print(f"✗ Error connecting to Elasticsearch: {e}")
