# Log Intelligence Assistant — v1 Build Guide

**Goal:** Build a RAG-based system that lets you semantically search and ask questions over log data, using a public LogHub dataset. No proprietary/work data involved.

**Time budget:** ~1 hour/day, 6 weeks to v1.

**How to use this doc:** Work top to bottom. Check off each task as you finish it. Don't skip the "Checkpoint" at the end of each week — if you can't do the checkpoint, don't move on, debug first. Debugging *is* the work, not a delay from it.

---

## Prerequisites (do once, before Week 1)

- [ ] Docker + Docker Compose installed and working (`docker --version`, `docker compose version`)
- [ ] Python 3.10+ installed, `venv` module available
- [ ] **LLM access — free option (default for this guide): Ollama**, running a small open model locally. No API key, no billing, no usage caps. (If you'd rather use a hosted API like Anthropic/OpenAI instead — e.g. for better answer quality on a final demo — that's a drop-in swap in Week 4, see the note there.)
- [ ] A GitHub account (to version-control this project from day one — commit after every session, even small ones)
- [ ] Create the project folder and a git repo:
  ```bash
  mkdir log-intel-assistant && cd log-intel-assistant
  git init
  python3 -m venv venv
  source venv/bin/activate
  ```

---

## Week 1 — Data + Environment Setup

**Objective:** Raw log lines flowing from a file → Kafka → Elasticsearch. No intelligence yet — just plumbing.

### Day 1 — Get the dataset
- [ ] Go to the LogHub repository (github.com/logpai/loghub) and pick a dataset. **Recommended starting point: HDFS_1** (well-documented, moderate size ~1.5GB raw / has a smaller labeled sample too) or **Apache** logs (smaller, simpler format — good if you want an easier first pass).
- [ ] Download the dataset, unzip it into `data/raw/`.
- [ ] Open the file, read the first ~50 lines manually. Understand the log format before writing any code — note timestamp format, severity levels, message structure.

### Day 2 — Environment setup
- [ ] Install core dependencies:
  ```bash
  pip install kafka-python elasticsearch python-dotenv
  ```
- [ ] Create a `.env` file for config (Kafka broker address, ES host, later your LLM API key). Add `.env` to `.gitignore` immediately.
- [ ] Create `.gitignore` with at least: `venv/`, `.env`, `data/raw/`, `__pycache__/`

### Day 3 — Spin up infra with Docker Compose
- [ ] Write a `docker-compose.yml` with three services: Zookeeper, Kafka, Elasticsearch (single-node, security disabled for local dev). Add Kibana too if you want a UI to poke at ES data (optional but genuinely helpful for debugging).
- [ ] `docker compose up -d` and confirm all containers are healthy (`docker ps`).
- [ ] Sanity check: create a Kafka topic manually and confirm you can produce/consume a test message via CLI before writing any Python.

### Day 4 — Producer script
- [ ] Write `producer.py`: reads the raw log file line by line, publishes each line as a message to a Kafka topic (e.g. `raw-logs`). Keep it dumb on purpose — no parsing yet, just get lines moving.
- [ ] Run it against a small slice of the dataset first (e.g. `head -n 1000 logfile.log`) before the full file — don't debug against the whole dataset.

### Day 5 — Consumer script
- [ ] Write `consumer.py`: subscribes to `raw-logs`, and for each message, indexes it into Elasticsearch as a document (even with just one field, `raw_message`, for now).
- [ ] Run producer + consumer together on your 1000-line sample. Confirm documents land in ES.

### Day 6 — Verify
- [ ] Query Elasticsearch directly (`curl` or Kibana Dev Tools) and confirm the document count matches your input line count.
- [ ] Spot-check a few documents — is the raw text intact, no encoding issues, no truncation?

### Day 7 — Buffer day
- [ ] Catch up on anything that slipped. Run the full dataset (not just the sample) through the pipeline once, end to end.
- [ ] Commit your code with a clear message. Write a 2-3 line note in a `NOTES.md` about anything that broke and how you fixed it — you'll want this later for interviews ("what was the hardest part") and it's genuinely useful documentation.

**Checkpoint — Week 1 done when:** You can run producer → Kafka → consumer → Elasticsearch on the full dataset and query the raw logs back out.

---

## Week 2 — Parsing & Structuring

**Objective:** Turn raw log lines into structured, queryable fields.

### Day 1-2 — Design the schema
- [ ] Decide on fields to extract: `timestamp`, `severity` (INFO/WARN/ERROR/etc. if present), `component`/`service`, `message`. Check if LogHub provides a "structured" version of your dataset (many do — a CSV with pre-parsed fields and a template ID) — if so, use it as ground truth to validate your own parser against.
- [ ] Write a parser function using regex tailored to your dataset's log format. Test it against 10-15 varied lines before running it on everything.

### Day 3-4 — Apply parsing + re-index
- [ ] Update the consumer (or write a separate enrichment step) to parse each raw line into structured fields before indexing.
- [ ] Define an explicit Elasticsearch index mapping (don't let it auto-infer types — set `timestamp` as a date field, `severity` as keyword, `message` as text) so queries behave correctly later.
- [ ] Re-run the full pipeline with parsing enabled.

### Day 5-6 — Query practice
- [ ] Write and test a handful of real Elasticsearch queries: "all ERROR logs in a time range," "logs from a specific component," "count of logs by severity." This isn't wasted time — it's what your RAG retrieval will lean on later, and it's also good system-design talking material (indexing strategy, query performance).

### Day 7 — Buffer + commit
- [ ] Fix stragglers, update `NOTES.md`, commit.

**Checkpoint — Week 2 done when:** Every log entry in Elasticsearch has structured fields (not just raw text), and you can filter/aggregate by severity, component, and time.

---

## Week 3 — Embeddings + Vector Search

**Objective:** Add semantic search on top of keyword search.

### Day 1 — Pick your vector store
- [ ] Use **Chroma** for local dev — it's the lowest-friction option (embedded, no separate server needed) and swappable later for something like pgvector if you want a "production-grade" story.
  ```bash
  pip install chromadb sentence-transformers
  ```

### Day 2-3 — Generate embeddings
- [ ] Pick an embedding model — a local `sentence-transformers` model (e.g. `all-MiniLM-L6-v2`) is fine and free for dev; note that a hosted embedding API is an easy later upgrade.
- [ ] Write a script that pulls log messages from Elasticsearch, embeds them, and stores the vectors in Chroma alongside the original log ID (so you can look the full document back up in ES after a vector match).

### Day 4-5 — Semantic search function
- [ ] Write a function: given a natural-language query ("connection timeout errors"), embed it, query Chroma for nearest neighbors, then fetch the full structured log entries from Elasticsearch by ID.
- [ ] Test it against queries where the exact keyword *isn't* in the logs but the meaning is related — this is the point of semantic search, so deliberately test that it beats plain keyword search on at least a few examples.

### Day 6-7 — Buffer + commit
- [ ] Handle batching if embedding the full dataset is slow (batch in chunks of a few thousand rather than one huge call).
- [ ] Commit, update `NOTES.md` with example queries that worked well — you'll reuse these as demo material.

**Checkpoint — Week 3 done when:** You can type a plain-English description of a problem and get back semantically relevant log entries, not just keyword matches.

---

## Week 4 — RAG Layer

**Objective:** Wire retrieval into an LLM to get actual answers, not just matched logs.

### Day 1 — Set up Ollama (free, local, no billing)
- [ ] Install Ollama (ollama.com — supports Mac/Linux/Windows). Confirm it's running: `ollama --version`.
- [ ] Pull a small model to start: `ollama pull llama3.1:8b` (or `mistral`, `phi3` if you want something lighter on RAM). This downloads once, then runs fully offline.
- [ ] Test it directly from the terminal first: `ollama run llama3.1:8b "say hello"` — confirm you get a response before writing any code.
- [ ] Install the Python client: `pip install ollama`
- [ ] Write a **one-function abstraction** for your LLM call, e.g. `call_llm(prompt: str) -> str`, that internally calls Ollama. Every other part of your RAG code should call this function, never the Ollama client directly — this is what makes swapping providers later a 5-minute change instead of a rewrite.
  ```python
  import ollama

  def call_llm(prompt: str) -> str:
      response = ollama.chat(
          model="llama3.1:8b",
          messages=[{"role": "user", "content": prompt}]
      )
      return response["message"]["content"]
  ```
- [ ] **Optional — hosted API instead:** if you'd rather use Anthropic or OpenAI (better answer quality, small cost), get an API key from console.anthropic.com or platform.openai.com, put it in `.env`, and swap only the *inside* of `call_llm()` to call that API instead. Keep the function signature identical so nothing else in your code changes.

### Day 2-3 — Prompt design
- [ ] Design a prompt template: system instructions ("you are a log analysis assistant, answer using only the provided log entries, cite specific log lines"), then inject the retrieved logs as context, then the user's question.
- [ ] Keep the first version simple — top-5 retrieved logs, no fancy re-ranking yet.

### Day 4-5 — Build the RAG function
- [ ] Write `ask(question)`: embed question → retrieve top-k logs from Chroma → pull full entries from Elasticsearch → build prompt → call LLM → return answer.
- [ ] Test with realistic questions: "what errors happened around timestamp X," "summarize the most common failure type," "is there a pattern in these warnings."

### Day 6-7 — Evaluate + iterate
- [ ] Run 10-15 varied test questions. For any bad answers, diagnose whether it's a retrieval problem (wrong logs pulled) or a generation problem (right logs, bad answer) — this distinction matters and is worth writing down, it's a real RAG-debugging skill.
- [ ] Commit, update `NOTES.md`.

**Checkpoint — Week 4 done when:** You can ask a natural-language question and get a coherent, grounded answer referencing real log entries. This is your core project working.

---

## Week 5 — Wrap in FastAPI

**Objective:** Turn the script into a usable service.

### Day 1-2 — Basic API
- [ ] `pip install fastapi uvicorn`
- [ ] Build endpoints: `POST /ask` (question → answer), `GET /logs` (basic filtered search), `GET /health`.
- [ ] Keep the RAG logic in a separate module — the API layer should just call into it, not contain business logic.

### Day 3 — Error handling
- [ ] Handle the obvious failure modes: empty query, LLM API failure/timeout, no relevant logs found. Return sensible HTTP status codes and messages, not stack traces.

### Day 4-5 — Manual testing
- [ ] Test every endpoint with `curl` or the FastAPI auto-docs (`/docs`). Try edge cases deliberately (very long question, gibberish input, empty dataset scenario).

### Day 6-7 — Buffer + commit
- [ ] Clean up, commit. This is your MVP milestone — pause and actually feel good about it before moving to polish week.

**Checkpoint — Week 5 done when:** You have a running FastAPI service you could demo live via `/docs` or `curl`, no manual script-running required.

---

## Week 6 — Polish, Document, Ship

**Objective:** Make it presentable — this week is as much about the README as the code.

### Day 1-2 — Dockerize the app itself
- [ ] Write a `Dockerfile` for your FastAPI app, add it to the `docker-compose.yml` alongside Kafka/ES so the whole thing spins up with one command.

### Day 3 — README
- [ ] Write a real README: what the project does, architecture diagram (even a simple ASCII/text one), setup instructions, example queries with real output, and — importantly — a short "design decisions" section (why Kafka, why Chroma, what you'd change at scale). This section is what you'll actually get asked about in interviews.

### Day 4 — Optional: deploy
- [ ] If you want a live link, deploy the FastAPI service (and a small hosted dataset) to a free tier host (Render/Railway/Fly.io). Not mandatory — a clean local setup with a good README is enough for a resume link, but a live demo is a nice-to-have.

### Day 5-6 — Final pass
- [ ] Re-read your own README as if you were a stranger — can you set this up from scratch following only your instructions? Fix what's unclear.
- [ ] Make sure `.env.example` exists (with dummy values) so others can see what config is needed without your real secrets.

### Day 7 — Ship
- [ ] Push to GitHub, make the repo public, pin it on your GitHub profile. Add it to your resume with a one-line description you can defend in an interview.

**Checkpoint — Week 6 done when:** A stranger could clone your repo, follow the README, and get the assistant running — and you can explain every architectural choice out loud.

---

## What comes after v1 (once you're ready to keep going)

- **Anomaly detection**: flag unusual spikes/rare error patterns, auto-generate incident summaries via the RAG layer
- **Agent layer**: a ReAct-style agent that chains multiple retrieval steps to investigate an issue, instead of one-shot Q&A
- **Semantic caching**: cache similar questions to cut LLM calls/cost — directly reuses a topic from your Qualcomm prep, now something you've actually implemented
- **Bot interface**: Slack/Discord front end instead of raw API calls
- **Multi-source logs**: ingest a second LogHub dataset (different system) to test whether your pipeline generalizes

## Reference links (verify current URLs when you sit down to build — repos move)

- LogHub dataset repository: `github.com/logpai/loghub`
- Ollama (free local LLM runner): `ollama.com`
- Chroma docs: `docs.trychroma.com`
- FastAPI docs: `fastapi.tiangolo.com`
- Sentence-Transformers: `sbert.net`
