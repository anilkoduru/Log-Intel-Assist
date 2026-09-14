# Log Intelligence Assistant - Project Checklist

## ✅ WEEK 1: Data + Environment Setup
**Status: COMPLETE & VERIFIED ✓**

- [x] Docker + Docker Compose installed and working
- [x] Python 3.10+ installed, venv activated
- [x] LLM access configured (Ollama setup in .env)
- [x] GitHub setup and git initialized
- [x] Project folder and venv created
- [x] HDFS dataset downloaded and available in `HDFS_v1/`
- [x] Dependencies installed (kafka-python, elasticsearch, chromadb, sentence-transformers, ollama, python-dotenv)
- [x] `.env` file created with all configuration
- [x] `.gitignore` created with `venv/`, `.env`, `data/raw/`, `__pycache__/`
- [x] Docker Compose with Zookeeper, Kafka, Elasticsearch, Kibana running
- [x] `producer.py` working - sends raw logs to Kafka topic `raw-logs`
- [x] `consumer.py` working - consumes from Kafka, parses, indexes to Elasticsearch
- [x] Verified end-to-end: raw logs → Kafka → parsed logs → Elasticsearch

**Checkpoint Validation:** ✓ PASSED
- Kafka is up and accepting messages
- Elasticsearch is up and indexing documents  
- Log parsing is working correctly
- End-to-end pipeline functional

---

## 🔄 WEEK 2: Parsing & Structuring
**Status: COMPLETE & WORKING ✓**

- [x] Schema designed with fields: timestamp, level, component_class, component_inner, block_id, event_id, message, raw_line
- [x] Log parser regex implemented and tested (`log_parser.py`)
- [x] Parser extracts templates from HDFS.log_templates.csv (29 templates loaded)
- [x] Consumer updated with structured field extraction
- [x] Elasticsearch index mapping defined (explicit types, not auto-inferred)
- [x] Full pipeline re-run and verified with structured fields
- [x] Verified documents have all required fields (not just raw text)

**Checkpoint Validation:** ✓ READY
- Every log entry has structured fields (timestamp, level, component, etc.)
- Can filter/aggregate by severity, component, and time
- Documents indexed with correct field types

---

## 🟡 WEEK 3: Embeddings + Vector Search
**Status: IN PROGRESS (ETA 2-4 hours remaining)**

### Completed:
- [x] Installed Chroma and sentence-transformers
- [x] Selected embedding model: `all-MiniLM-L6-v2` (fast, local, CPU-friendly)
- [x] Optimized `embed_and_store.py`:
  - [x] Reduced batch size to 512 (memory efficient)
  - [x] Added GPU detection (falls back to CPU)
  - [x] Added resume capability (skip already-embedded)
  - [x] Added progress tracking (% complete, time elapsed)
- [x] Started embedding 874,791 documents from Elasticsearch
  - Currently generating vectors on CPU
  - Speed: ~50-100 docs/second
  - Progress tracked in terminal output

### Still To Do:
- [ ] Wait for embedding to complete (will show "✓ SUCCESS" message)
- [ ] Verify Chroma collection count matches ES documents
- [ ] Quick semantic search validation

### Checkpoint: 
- [x] Elasticsearch has 874,791 indexed documents
- [ ] Chroma DB has 874,791 embeddings (when complete)
- [ ] Semantic search ready for Week 4

**Status:** ~70% done (currently embedding on CPU)

---

## 🔴 WEEK 4: RAG Layer (LLM Integration)
**Status: NOT STARTED - NEXT PHASE**

### Tasks:
- [ ] Verify Ollama installed (`ollama --version`)
- [ ] Pull LLM model: `ollama pull llama3.1:8b`
- [ ] Test Ollama manually: `ollama run llama3.1:8b "say hello"`
- [ ] Install Python Ollama client: `pip install ollama`
- [ ] Create abstraction function:
  ```python
  def call_llm(prompt: str) -> str:
      response = ollama.chat(
          model="llama3.1:8b",
          messages=[{"role": "user", "content": prompt}]
      )
      return response["message"]["content"]
  ```
- [ ] Design prompt template with:
  - [ ] System instructions (you are a log analyst, cite specific logs)
  - [ ] Retrieved logs as context (top-5 documents)
  - [ ] User question
- [ ] Build `ask(question)` function:
  - [ ] Embed question
  - [ ] Retrieve top-k logs from Chroma
  - [ ] Fetch full entries from ES
  - [ ] Build prompt with context
  - [ ] Call LLM
  - [ ] Return answer
- [ ] Test with realistic questions:
  - [ ] "What errors happened around [timestamp]?"
  - [ ] "Summarize the most common failure type"
  - [ ] "Is there a pattern in these warnings?"
- [ ] Diagnose answer quality:
  - [ ] Retrieval issue? → adjust embedding model or search parameters
  - [ ] Generation issue? → adjust prompt template or LLM model

### Checkpoint:
- [ ] Can ask natural-language question → get coherent, grounded answer referencing real logs

**Estimated Duration:** 4 days

---

## 🔴 WEEK 4: RAG Layer (IMPLEMENTATION COMPLETE)
**Status: READY TO TEST (Awaiting Ollama Setup)**

### Implementation Complete ✓
- [x] `rag.py` - Full RAG system
  - Semantic search (Chroma + Elasticsearch)
  - Ollama LLM integration (free, local, offline)
  - `ask(question)` main function
  - System readiness checker
  - Interactive query mode
- [x] `setup_ollama.py` - Installation guide
  - Detect/install Ollama
  - Download models
  - Testing utilities
- [x] `test_rag.py` - Test suite with 5 queries
- [x] `WEEK4_GUIDE.py` - Complete execution guide

### Manual Setup Required:
- [ ] Download Ollama from https://ollama.ai
- [ ] Install Ollama (~5 minutes)
- [ ] Run: `ollama pull llama3.1:8b` (~5-10 minutes)
- [ ] Verify embeddings finished (embed_and_store.py)

### Quick Start:
```powershell
# 1. Install Ollama (download from ollama.ai)
# 2. Pull model
ollama pull llama3.1:8b

# 3. Check system ready
python rag.py

# 4. Run tests
python test_rag.py

# 5. Interactive queries
python rag.py
# Then ask questions!
```

### Checkpoint:
- [ ] Ollama running with llama3.1:8b
- [ ] `python rag.py` shows all components ready
- [ ] `python test_rag.py` passes all 5 tests
- [ ] Can ask custom questions interactively

---

## 🔴 WEEK 5: FastAPI Service
**Status: NOT STARTED**

- [ ] Install FastAPI and Uvicorn
- [ ] Build API endpoints:
  - [ ] `POST /ask` - question → answer
  - [ ] `GET /logs` - filtered search
  - [ ] `GET /health` - status check
- [ ] Separate RAG logic from API layer
- [ ] Error handling for edge cases
- [ ] Manual testing with curl and `/docs` UI
- [ ] Test edge cases (long queries, gibberish, empty dataset)
- [ ] Commit and document

### Checkpoint:
- [ ] Can run FastAPI service and use `/docs` interface to ask questions

**Estimated Duration:** 3 days

---

## 🔴 WEEK 6: Polish, Document, Ship
**Status: NOT STARTED**

- [ ] Dockerize the FastAPI app
- [ ] Update docker-compose.yml to include app service
- [ ] Write comprehensive README:
  - [ ] What the project does
  - [ ] Architecture diagram
  - [ ] Setup instructions
  - [ ] Example queries with real output
  - [ ] Design decisions (why Kafka, why Chroma, tradeoffs at scale)
- [ ] Create `.env.example` with dummy values
- [ ] Final README review (can a stranger follow it?)
- [ ] Push to GitHub
- [ ] Make repo public
- [ ] Add to GitHub profile
- [ ] Add to resume with one-line description

### Checkpoint:
- [ ] Stranger can clone, follow README, and run the system

**Estimated Duration:** 2-3 days

---

## 📊 Project Timeline

| Week | Objective | Status | Effort |
|------|-----------|--------|--------|
| 1 | Infra + raw logs | ✅ DONE | ~1 hour |
| 2 | Parsing + structure | ✅ DONE | ~1 hour |
| 3 | Embeddings + vectors | 🟡 READY | 3 days |
| 4 | RAG + LLM | 🔴 NEXT | 4 days |
| 5 | FastAPI service | 🔴 PENDING | 3 days |
| 6 | Polish + ship | 🔴 PENDING | 2-3 days |

**Total Remaining:** ~12-14 days @ 1 hour/day = 2-3 weeks to v1

---

## 🔧 Critical Files

| File | Purpose | Status |
|------|---------|--------|
| `producer.py` | Send logs to Kafka | ✅ Working |
| `consumer.py` | Index logs to ES | ✅ Working |
| `log_parser.py` | Parse HDFS format | ✅ Working |
| `embed_and_store.py` | Generate embeddings | ⏳ Ready to run |
| `test_pipeline.py` | E2E validation | ✅ Passing |
| `.env` | Configuration | ✅ Configured |
| `docker-compose.yaml` | Infrastructure | ✅ Running |

---

## 🎯 Next Action

**Start Week 3 - Run embeddings:**

```powershell
# Make sure you're in venv
python embed_and_store.py
```

This will:
1. Fetch all indexed logs from Elasticsearch
2. Generate embeddings using `all-MiniLM-L6-v2` model
3. Store vectors in Chroma DB at `./chroma_db`
4. Show progress and completion time

Expected output: 10,000+ documents embedded and stored in Chroma

---

## 📝 Notes

- Week 1 & 2 complete and verified ✓
- Full dataset ready in `HDFS_v1/HDFS.log`
- Kubernetes/production setup is out of scope for v1
- All secrets (API keys) go in `.env` (never commit)
- Each week ends with a git commit with clear message
