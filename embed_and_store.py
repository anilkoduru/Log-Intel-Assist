import os
import time
import torch
from typing import Any, Dict, List, Optional, Set

from elasticsearch import Elasticsearch, exceptions as es_exceptions
import chromadb
from sentence_transformers import SentenceTransformer


ES_INDEX = "logs"
CHROMA_COLLECTION_NAME = "hdfs_logs"
CHROMA_PATH = "./chroma_db"
PAGE_SIZE = 1000
ENCODE_BATCH_SIZE = 512  # Reduced from 2000 for memory efficiency (2000 docs + batch_size=64 = too much RAM)
EMBEDDING_BATCH_SIZE = 64  # Internal batch size for the transformer
SKIP_EXISTING = True  # Resume capability: skip docs already in Chroma


def get_device() -> str:
    """Detect GPU availability and return device string for torch."""
    if torch.cuda.is_available():
        device = "cuda"
        print(f"✓ GPU available: {torch.cuda.get_device_name(0)}")
        print(f"  CUDA version: {torch.version.cuda}")
    else:
        device = "cpu"
        print("⚠ No GPU detected, using CPU (embeddings will be slower)")
    return device


def get_es_client() -> Elasticsearch:
    """Create an Elasticsearch client from env vars or defaults using modern API."""
    host = os.getenv("ES_HOST", "localhost")
    port = os.getenv("ES_PORT", "9200")
    try:
        port_int = int(port)
    except ValueError:
        print(f"Warning: ES_PORT={port!r} is not valid; falling back to 9200.")
        port_int = 9200

    # Modern Elasticsearch client API (v8.0+)
    client = Elasticsearch([f"http://{host}:{port_int}"], timeout=30)
    return client


def get_existing_chroma_ids(collection) -> Set[str]:
    """Fetch all existing IDs in Chroma to enable resume capability."""
    try:
        # Query all docs in collection to get their IDs
        result = collection.get()
        existing_ids = set(result.get("ids", []))
        print(f"Found {len(existing_ids)} documents already in Chroma collection")
        return existing_ids
    except Exception as e:
        print(f"Warning: could not fetch existing IDs from Chroma: {e}")
        return set()


def fetch_all_documents(es_client: Elasticsearch, index_name: str, page_size: int = PAGE_SIZE):
    """Fetch all documents from the index using the scroll API in batches."""
    scroll_timeout = "2m"
    scroll_id = None
    total_docs_fetched = 0

    try:
        response = es_client.search(
            index=index_name,
            scroll=scroll_timeout,
            size=page_size,
            query={"match_all": {}},
        )
    except Exception as exc:
        print(f"Error: failed to query Elasticsearch index '{index_name}': {exc}")
        return total_docs_fetched, None

    scroll_id = response.get("_scroll_id")
    hits = response.get("hits", {}).get("hits", [])

    while True:
        if not hits:
            break

        for hit in hits:
            source = hit.get("_source") or {}
            if not source:
                continue
            yield hit, source
            total_docs_fetched += 1

        try:
            response = es_client.scroll(scroll_id=scroll_id, scroll=scroll_timeout)
        except Exception as exc:
            print(f"Error: failed to continue Elasticsearch scroll: {exc}")
            break

        scroll_id = response.get("_scroll_id")
        hits = response.get("hits", {}).get("hits", [])

        if not scroll_id or not hits:
            break

    return total_docs_fetched, scroll_id


def sanitize_metadata_value(value: Any) -> Any:
    """Chroma metadata values must be simple scalar types, not None or nested objects."""
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def build_metadata(source: Dict[str, Any]) -> Dict[str, Any]:
    """Extract only the metadata required for Chroma alongside the embedded message."""
    return {
        "event_id": sanitize_metadata_value(source.get("event_id")),
        "block_id": sanitize_metadata_value(source.get("block_id")),
        "component_class": sanitize_metadata_value(source.get("component_class")),
        "component_inner": sanitize_metadata_value(source.get("component_inner")),
        "level": sanitize_metadata_value(source.get("level")),
        "timestamp": sanitize_metadata_value(source.get("timestamp")),
    }


def add_batch_to_chroma(collection, ids: List[str], documents: List[str], embeddings: List[List[float]], metadatas: List[Dict[str, Optional[str]]]):
    """Write one chunk to Chroma and continue even if one batch fails."""
    try:
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )
        return True
    except Exception as exc:
        print(f"Error: failed to add batch of {len(ids)} documents to Chroma: {exc}")
        return False


def main():
    """Embed all HDFS log messages and store them in a persistent Chroma collection."""
    start_time = time.time()
    
    print("=" * 70)
    print("WEEK 3: EMBEDDINGS + VECTOR SEARCH")
    print("=" * 70)
    
    # Connect to Elasticsearch
    es_client = None
    try:
        es_client = get_es_client()
        es_client.info()
        print(f"\n✓ Connected to Elasticsearch at {os.getenv('ES_HOST', 'localhost')}:{os.getenv('ES_PORT', '9200')}")
    except Exception as exc:
        print(f"✗ Error: could not connect to Elasticsearch: {exc}")
        return

    # Detect GPU
    print()
    device = get_device()

    # Load the embedding model once for batch processing
    try:
        print(f"\n⏳ Loading sentence-transformers model: all-MiniLM-L6-v2")
        model = SentenceTransformer("all-MiniLM-L6-v2")
        model = model.to(device)  # Move model to GPU if available
        print(f"✓ Model loaded on device: {device}")
    except Exception as exc:
        print(f"✗ Error: failed to load embedding model: {exc}")
        return

    # Create or open the persistent Chroma collection
    try:
        chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
        collection = chroma_client.get_or_create_collection(name=CHROMA_COLLECTION_NAME)
        print(f"✓ Using Chroma collection '{CHROMA_COLLECTION_NAME}' at '{CHROMA_PATH}'")
    except Exception as exc:
        print(f"✗ Error: could not initialize Chroma: {exc}")
        return

    # Get existing IDs for resume capability
    print()
    existing_ids = get_existing_chroma_ids(collection) if SKIP_EXISTING else set()

    # Get total document count from ES for progress calculation
    print()
    try:
        count_result = es_client.cat.count(index=ES_INDEX, format='json')
        total_es_count = int(count_result[0]['count']) if count_result else 0
        print(f"✓ Total documents in Elasticsearch: {total_es_count}")
    except Exception as exc:
        print(f"⚠ Warning: could not get total document count: {exc}")
        total_es_count = 0

    total_es_docs = 0
    total_chroma_added = 0
    skipped_existing = 0
    pending_ids: List[str] = []
    pending_documents: List[str] = []
    pending_metadatas: List[Dict[str, Optional[str]]] = []

    print(f"\n⏳ Starting embedding process...")
    print(f"   ENCODE_BATCH_SIZE={ENCODE_BATCH_SIZE}, EMBEDDING_BATCH_SIZE={EMBEDDING_BATCH_SIZE}")
    print(f"   Resume mode: {'ON (skip existing)' if SKIP_EXISTING else 'OFF (re-embed all)'}")
    print("-" * 70)

    try:
        # Scroll through all documents in batches
        for hit, source in fetch_all_documents(es_client, ES_INDEX):
            total_es_docs += 1
            es_doc_id = hit.get("_id")
            
            # Skip if already in Chroma (resume capability)
            if SKIP_EXISTING and es_doc_id in existing_ids:
                skipped_existing += 1
                continue
            
            message = source.get("message")
            if not message:
                continue

            if not es_doc_id:
                continue

            pending_ids.append(es_doc_id)
            pending_documents.append(message)
            pending_metadatas.append(build_metadata(source))

            # Process batch when it reaches target size
            if len(pending_documents) >= ENCODE_BATCH_SIZE:
                try:
                    # Encode batch with progress bar
                    embeddings = model.encode(
                        pending_documents,
                        batch_size=EMBEDDING_BATCH_SIZE,
                        show_progress_bar=True,
                        device=device,
                    )
                    embeddings = embeddings.tolist() if hasattr(embeddings, "tolist") else list(embeddings)

                    # Add to Chroma
                    success = add_batch_to_chroma(
                        collection,
                        ids=pending_ids,
                        documents=pending_documents,
                        embeddings=embeddings,
                        metadatas=pending_metadatas,
                    )
                    
                    if success:
                        total_chroma_added += len(pending_ids)
                        progress_pct = (total_es_docs / total_es_count * 100) if total_es_count else 0
                        elapsed = time.time() - start_time
                        print(f"✓ Added {len(pending_ids)} vectors to Chroma (total: {total_chroma_added}, "
                              f"progress: {progress_pct:.1f}%, elapsed: {elapsed:.1f}s)")
                except Exception as exc:
                    print(f"✗ Error: failed to encode or store batch: {exc}")

                pending_ids = []
                pending_documents = []
                pending_metadatas = []

        # Flush any remaining documents
        if pending_documents:
            try:
                embeddings = model.encode(
                    pending_documents,
                    batch_size=EMBEDDING_BATCH_SIZE,
                    show_progress_bar=True,
                    device=device,
                )
                embeddings = embeddings.tolist() if hasattr(embeddings, "tolist") else list(embeddings)

                success = add_batch_to_chroma(
                    collection,
                    ids=pending_ids,
                    documents=pending_documents,
                    embeddings=embeddings,
                    metadatas=pending_metadatas,
                )
                if success:
                    total_chroma_added += len(pending_ids)
                    print(f"✓ Added final batch of {len(pending_ids)} vectors to Chroma (total: {total_chroma_added})")
            except Exception as exc:
                print(f"✗ Error: failed to encode or store final batch: {exc}")

    except Exception as exc:
        print(f"✗ Error: unexpected failure while processing documents: {exc}")
        import traceback
        traceback.print_exc()

    # Summary
    elapsed_time = time.time() - start_time
    print("\n" + "=" * 70)
    print("EMBEDDING COMPLETE")
    print("=" * 70)
    print(f"Total documents fetched from ES:        {total_es_docs}")
    print(f"Total documents skipped (existing):     {skipped_existing}")
    print(f"Total documents added to Chroma:        {total_chroma_added}")
    print(f"Total time elapsed:                    {elapsed_time:.2f}s ({elapsed_time/60:.2f}m)")
    
    final_count = collection.count()
    print(f"Final Chroma collection size:           {final_count}")
    
    if final_count > 0:
        print(f"\n✓ SUCCESS: Chroma is ready for semantic search!")
        print(f"  Next step: Run Week 4 (RAG layer with Ollama LLM)")
    else:
        print(f"\n✗ WARNING: Chroma collection is empty!")
        print(f"  Check if Elasticsearch has documents in the '{ES_INDEX}' index")
    print("=" * 70)


if __name__ == "__main__":
    main()
