"""
WEEK 4: RAG LAYER - Semantic Search + LLM Integration
======================================================

This module combines:
1. Semantic search (Chroma vector DB)
2. Log retrieval (Elasticsearch)
3. LLM generation (Ollama - free, local, offline)

To use:
  from rag import ask
  answer = ask("What errors happened around midnight?")
"""

import os
import json
from typing import List, Dict, Optional, Any
from pathlib import Path

from elasticsearch import Elasticsearch
import chromadb
from sentence_transformers import SentenceTransformer
import ollama


# ============================================================================
# CONFIGURATION
# ============================================================================

ES_HOST = os.getenv("ES_HOST", "localhost")
ES_PORT = int(os.getenv("ES_PORT", "9200"))
ES_INDEX = os.getenv("ES_INDEX", "logs")

CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db")
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION_NAME", "hdfs_logs")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

EMBEDDING_MODEL = "all-MiniLM-L6-v2"
TOP_K_RETRIEVAL = 5  # Number of logs to retrieve for context


# ============================================================================
# CLIENTS (LAZY INITIALIZATION)
# ============================================================================

_es_client = None
_chroma_client = None
_chroma_collection = None
_embedding_model = None


def get_es_client() -> Elasticsearch:
    """Get or create Elasticsearch client."""
    global _es_client
    if _es_client is None:
        _es_client = Elasticsearch([f"http://{ES_HOST}:{ES_PORT}"], timeout=30)
    return _es_client


def get_embedding_model():
    """Get or create SentenceTransformer model."""
    global _embedding_model
    if _embedding_model is None:
        print(f"Loading embedding model: {EMBEDDING_MODEL}")
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL)
    return _embedding_model


def get_chroma_collection():
    """Get or create Chroma collection."""
    global _chroma_client, _chroma_collection
    if _chroma_collection is None:
        print(f"Connecting to Chroma at {CHROMA_PATH}")
        _chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
        _chroma_collection = _chroma_client.get_or_create_collection(
            name=CHROMA_COLLECTION
        )
    return _chroma_collection


# ============================================================================
# SEMANTIC SEARCH
# ============================================================================

def semantic_search(query: str, top_k: int = TOP_K_RETRIEVAL) -> List[Dict[str, Any]]:
    """
    Search for semantically similar logs.
    
    Args:
        query: Natural language query (e.g., "connection timeout errors")
        top_k: Number of results to return
    
    Returns:
        List of log documents with their fields
    """
    try:
        # Embed the query
        embedding_model = get_embedding_model()
        query_embedding = embedding_model.encode(query, show_progress_bar=False)
        
        # Search in Chroma
        collection = get_chroma_collection()
        results = collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=top_k
        )
        
        if not results or not results.get("ids") or not results["ids"][0]:
            print(f"⚠ No matching logs found for query: {query}")
            return []
        
        # Fetch full documents from Elasticsearch
        doc_ids = results["ids"][0]
        es_client = get_es_client()
        
        documents = []
        for doc_id in doc_ids:
            try:
                doc = es_client.get(index=ES_INDEX, id=doc_id)
                source = doc.get("_source", {})
                source["_id"] = doc_id  # Include ES doc ID
                documents.append(source)
            except Exception as e:
                print(f"⚠ Could not fetch document {doc_id}: {e}")
        
        return documents
    
    except Exception as e:
        print(f"✗ Error during semantic search: {e}")
        return []


# ============================================================================
# LLM INTEGRATION
# ============================================================================

def call_llm(prompt: str, system_prompt: Optional[str] = None) -> str:
    """
    Call Ollama LLM with the given prompt.
    
    Args:
        prompt: The user query/prompt
        system_prompt: Optional system instructions
    
    Returns:
        LLM response
    """
    try:
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=messages,
            stream=False
        )
        
        return response.get("message", {}).get("content", "")
    
    except Exception as e:
        print(f"✗ Error calling Ollama: {e}")
        return f"Error: Could not get response from LLM ({e})"


# ============================================================================
# RAG ORCHESTRATION
# ============================================================================

def ask(question: str, top_k: int = TOP_K_RETRIEVAL, verbose: bool = False) -> Dict[str, Any]:
    """
    Ask a question over your logs using RAG.
    
    This function:
    1. Semantically searches for relevant log entries
    2. Retrieves full documents from Elasticsearch
    3. Builds a prompt with the logs as context
    4. Sends to Ollama LLM for generation
    5. Returns the answer with source logs
    
    Args:
        question: Natural language question about logs
        top_k: Number of logs to use as context (default 5)
        verbose: If True, print detailed progress
    
    Returns:
        Dict with:
        - "answer": LLM response
        - "source_logs": List of retrieved log documents
        - "reasoning": Explanation of what was retrieved
    """
    
    if verbose:
        print("\n" + "=" * 70)
        print("RAG QUERY")
        print("=" * 70)
        print(f"Question: {question}\n")
    
    # Step 1: Semantic search
    if verbose:
        print("[1] Searching for relevant logs...")
    
    retrieved_logs = semantic_search(question, top_k=top_k)
    
    if not retrieved_logs:
        if verbose:
            print("✗ No logs found matching the query")
        return {
            "answer": "I couldn't find any relevant logs matching your query.",
            "source_logs": [],
            "reasoning": "No semantic matches found"
        }
    
    if verbose:
        print(f"✓ Found {len(retrieved_logs)} relevant logs")
    
    # Step 2: Format logs for context
    if verbose:
        print("\n[2] Formatting logs as context...")
    
    log_context = _format_logs_for_context(retrieved_logs)
    
    if verbose:
        print(f"✓ Context formatted ({len(log_context)} chars)")
    
    # Step 3: Build RAG prompt
    if verbose:
        print("\n[3] Calling LLM...")
    
    system_prompt = """You are a log analysis assistant. Your job is to answer questions about system logs.

INSTRUCTIONS:
- Answer ONLY based on the provided logs
- If you don't have information to answer, say so
- Cite specific log entries when possible
- Be concise but informative
- Highlight any errors, warnings, or anomalies"""
    
    user_prompt = f"""Based on the following log entries, answer this question:

QUESTION: {question}

LOG ENTRIES:
{log_context}

ANSWER:"""
    
    # Step 4: Call LLM
    try:
        answer = call_llm(user_prompt, system_prompt=system_prompt)
    except Exception as e:
        answer = f"Error calling LLM: {e}"
    
    if verbose:
        print("✓ LLM response received")
        print("\n" + "-" * 70)
        print(f"ANSWER:\n{answer}")
        print("-" * 70)
    
    return {
        "answer": answer,
        "source_logs": retrieved_logs,
        "reasoning": f"Retrieved {len(retrieved_logs)} semantically similar logs",
        "question": question
    }


# ============================================================================
# HELPERS
# ============================================================================

def _format_logs_for_context(logs: List[Dict[str, Any]]) -> str:
    """Format logs as readable context for LLM."""
    formatted = []
    
    for i, log in enumerate(logs, 1):
        timestamp = log.get("timestamp", "N/A")
        level = log.get("level", "N/A")
        component = log.get("component_class", "N/A")
        message = log.get("message", "N/A")
        
        entry = f"{i}. [{timestamp}] {level} - {component}\n   Message: {message}"
        formatted.append(entry)
    
    return "\n\n".join(formatted)


def check_system_ready() -> bool:
    """Verify all components are ready."""
    print("Checking RAG system readiness...\n")
    
    checks = []
    
    # Check Elasticsearch
    try:
        es = get_es_client()
        info = es.info()
        count = int(es.cat.count(index=ES_INDEX, format='json')[0]['count'])
        print(f"✓ Elasticsearch: {count:,} documents in '{ES_INDEX}' index")
        checks.append(True)
    except Exception as e:
        print(f"✗ Elasticsearch: {e}")
        checks.append(False)
    
    # Check Chroma
    try:
        collection = get_chroma_collection()
        count = collection.count()
        print(f"✓ Chroma: {count:,} embeddings in '{CHROMA_COLLECTION}' collection")
        checks.append(True)
    except Exception as e:
        print(f"✗ Chroma: {e}")
        checks.append(False)
    
    # Check Ollama
    try:
        response = ollama.list()
        models = [
            m.get("name") or m.get("model") or ""
            for m in response.get("models", [])
        ]
        model_available = any(
            installed == OLLAMA_MODEL
            or installed.split(":")[0] == OLLAMA_MODEL.split(":")[0]
            for installed in models
        )
        if model_available:
            print(f"✓ Ollama: Model '{OLLAMA_MODEL}' available")
            checks.append(True)
        else:
            print(f"⚠ Ollama: Model '{OLLAMA_MODEL}' not found")
            print(f"  Available models: {models}")
            print(f"  Install with: ollama pull {OLLAMA_MODEL.split(':')[0]}")
            checks.append(False)
    except Exception as e:
        print(f"✗ Ollama: Not running (expected at http://localhost:11434)")
        print(f"  Start it with: ollama serve")
        checks.append(False)
    
    print()
    if all(checks):
        print("✓ RAG system READY")
        return True
    else:
        print("✗ Some components not ready")
        return False


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import sys
    
    # Check system
    if not check_system_ready():
        print("\nPlease fix the issues above and try again.")
        sys.exit(1)
    
    print("\n" + "=" * 70)
    print("INTERACTIVE RAG QUERY MODE")
    print("=" * 70)
    print("Ask questions about your logs. Type 'exit' to quit.\n")
    
    while True:
        try:
            question = input("Question: ").strip()
            
            if question.lower() in ["exit", "quit", "q"]:
                print("Goodbye!")
                break
            
            if not question:
                continue
            
            # Run RAG query
            result = ask(question, verbose=True)
            
            print(f"\nSource logs ({len(result['source_logs'])} retrieved):")
            for i, log in enumerate(result['source_logs'], 1):
                print(f"\n  Log {i}:")
                print(f"    Timestamp: {log.get('timestamp', 'N/A')}")
                print(f"    Level: {log.get('level', 'N/A')}")
                print(f"    Component: {log.get('component_class', 'N/A')}")
                print(f"    Message: {log.get('message', 'N/A')[:100]}...")
            
            print("\n")
        
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}")
