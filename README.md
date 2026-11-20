# 🎓 University Text-to-SQL Service (Classic RAG)

RAG-enhanced **Text-to-SQL** microservice built with **Python 3.11**, **FastAPI**, **LangChain**, **PostgreSQL 16**, **Pinecone**, **OpenAI**, **uv**, and **LangSmith**. It translates natural language questions about university academic, administrative, and financial records into safe, read-only PostgreSQL queries.

---

## ✨ Key Architecture Highlights

* **Semantic Business Layer (Pinecone Serverless):** Domain rules (`src/chunking/layer.md`) are split by Markdown headers (`##`) and stored in a managed **Pinecone** serverless index, keeping embeddings decoupled from the 14-table OLTP PostgreSQL database (`university`).
* **Idempotent Auto-Indexing:** An ephemeral `vector-store-init` container hashes `layer.md` + `EMBEDDING_MODEL` (SHA-256) on startup and checks Pinecone stats and `source_hash` metadata—skipping re-indexing when unchanged and refreshing automatically when rules or models change.
* **Decoupled Modules & Purpose-Based Config:** Retrieval logic is isolated under `src/retriever/` (`VectorRetriever` backed by a cached `PineconeVectorStore`), and environment variables are grouped by architectural role (`OLTP_STORE_*`, `VECTOR_STORE_*`, `OBSERVABILITY_*`).
* **LangSmith Observability:** Traces `SQL_Generation` and `LLMSqlGeneratorService.invoke` (`1_Retrieval` and `2_Generation` steps) along with per-stage latency feedback metrics (`service_retrieval_duration`, `service_generation_duration`, `sql_validation_duration`) in **LangSmith**.
* **Reproducible Dependencies:** Strictly locked with `uv` (`pyproject.toml` + `uv.lock`) inside Docker—zero host tool setup required.
* **3-Layer Evaluation Suite:**
  1. **AST Safety (`sqlglot`):** Enforces valid, read-only `SELECT` queries.
  2. **Logical Equivalence (`Ragas AspectCritic`):** Evaluates semantic alignment using `gpt-4o-mini`.
  3. **Execution Accuracy (`asyncpg` + `pandas`):** Runs expected vs. generated SQL in rolled-back transactions and compares DataFrames.

---

## 📂 Project Structure

```text
.
├── infra/
│   ├── .env                    # Environment configuration (not committed)
│   ├── .env.example            # Environment template with placeholders
│   ├── app.Dockerfile          # Python 3.11 + uv frozen sync
│   ├── pg.Dockerfile           # PostgreSQL 16 seeded with schema.sql & data.sql
│   └── docker-compose.yaml     # Stack: postgres-db, vector-store-init, ia-endpoint
├── src/
│   ├── api/                    # FastAPI app & /v1/sqlgen endpoint
│   ├── chunking/               # Business rules (layer.md) & hash-based chunker.py
│   ├── llm/                    # LLMSqlGeneratorService, structured output schema & SQL guardrail
│   ├── prompts/                # System/user prompt templates
│   ├── retriever/              # Cached PineconeVectorStore & VectorRetriever
│   ├── schema/                 # OLTP DDL (schema.sql) and seed data (data.sql)
│   └── utils.py                # Env loader, schema reader & LangSmith metrics client
├── tests/                      # Safety, Ragas AspectCritic, execution accuracy & endpoint tests
├── pyproject.toml
├── uv.lock
└── pytest.ini
```

---

## 🚀 Quick Start

### 1. Configure `infra/.env`

Create `infra/.env` (or copy `infra/.env.example`) with your provider keys and local database settings:

```env
OPENAI_API_KEY=<YOUR_OPENAI_API_KEY>
MAIN_MODEL_NAME=gpt-4o
TEST_MODEL_NAME=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small

OLTP_STORE_HOST=oltp_store
OLTP_STORE_PORT=5432
OLTP_STORE_USER=user
OLTP_STORE_PASSWORD=<YOUR_OLTP_PASSWORD>
OLTP_STORE_DB=university

VECTOR_STORE_API_KEY=<YOUR_PINECONE_API_KEY>
VECTOR_STORE_INDEX_NAME=bussines-index

OBSERVABILITY_ENABLED=true
OBSERVABILITY_ENDPOINT=https://api.smith.langchain.com
OBSERVABILITY_PROJECT_NAME=Project_LLM_Gen_dev
OBSERVABILITY_API_KEY=<YOUR_LANGSMITH_API_KEY>
```

### 2. Launch the Stack

```bash
docker compose -f infra/docker-compose.yaml up --build -d
```

`vector-store-init` verifies or indexes `layer.md` into Pinecone before `ia-endpoint` starts.

| Service | Container / Provider | Endpoint |
| :--- | :--- | :--- |
| FastAPI API / Swagger | `ia_endpoint` | `http://localhost:8001` (`/docs`) |
| OLTP PostgreSQL 16 | `oltp_store` | `localhost:5432` |
| Vector Store | Pinecone (Managed) | Cloud (`VECTOR_STORE_INDEX_NAME`) |
| Observability | LangSmith (Managed) | `https://smith.langchain.com` |

To stop (`down`) or reset local database volumes (`down -v`):

```bash
docker compose -f infra/docker-compose.yaml down
```

---

## 🌐 API Usage

**`POST /v1/sqlgen`**

```bash
curl -X POST "http://localhost:8001/v1/sqlgen" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Dame los nombres y apellidos de los alumnos de Ingeniería Civil Informática que en 2019-1 tienen estado financiero moroso y carrera activa."
  }'
```

```json
{
  "sql_query": "SELECT a.nombres, a.apellidos FROM alumno a JOIN ... WHERE ...;",
  "is_error": false,
  "error_message": null
}
```

Out-of-domain or unsafe queries return `"sql_query": null`, `"is_error": true`, and an actionable `"error_message"`.

---

## 🧪 Evaluation & Maintenance

Run tests inside the application container (`logs/` stores timestamped debug reports):

```bash
# Run full evaluation suite
docker exec -it ia_endpoint pytest -s tests/

# Or run individual suites
docker exec -it ia_endpoint pytest -s tests/test_sql_safety.py
docker exec -it ia_endpoint pytest -s tests/test_aspect_critic.py
docker exec -it ia_endpoint pytest -s tests/test_data_compy_score.py
docker exec -it ia_endpoint pytest -s tests/test_endpoint_ok.py
docker exec -it ia_endpoint pytest -s tests/test_dendpoint_error.py
```

**Re-indexing after editing `src/chunking/layer.md`:**

```bash
docker compose -f infra/docker-compose.yaml up vector-store-init
# Or force a full rebuild regardless of hash:
docker exec -it ia_endpoint python -m src.chunking.chunker --force
```