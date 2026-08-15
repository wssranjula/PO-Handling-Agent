# Purchase Order Intake Agent

An end-to-end purchase-order intake system built with FastAPI, LangGraph, OpenAI structured
outputs, PostgreSQL/pgvector, Gmail, LangSmith, and React.

The system receives purchase orders as email attachments, extracts a typed purchase-order object,
uses retrieval-augmented generation (RAG) to resolve messy customer and product references,
validates the result against operational records and policy, and routes it to either a clean-order
queue or a human-review queue.

Invoices are deliberately out of scope.

## What the system demonstrates

- Email intake through a multipart webhook or a read-only Gmail integration.
- LLM extraction into a strict Pydantic schema, including confidence, warnings, and source evidence.
- RAG over customer, product, and order-policy documents stored in PostgreSQL with pgvector.
- Deterministic validation of required fields, totals, customers, products, prices, addresses,
  payment terms, and duplicate PO numbers.
- Automatic persistence of clean orders.
- Human review for ambiguous or policy-breaking orders, with correction, revalidation, approval,
  and rejection.
- Request/run logging and LangSmith tracing.
- Idempotent processing of Gmail messages and attachments.

## System architecture

```text
 +-------------------+                         +-------------------+
 |   Gmail mailbox   |                         | Webhook / API user|
 +---------+---------+                         +---------+---------+
           | Gmail API                                   |
           v                                             | PDF / CSV / text
 +---------+---------+                                   |
 |   Gmail poller    |                                   |
 +---------+---------+                                   |
           |                                             |
           +----------------------+----------------------+
                                  v
                      +-----------+-----------+
                      |     Intake service    |
                      | validate, store, dedupe|
                      +-----------+-----------+
                                  |
                +-----------------+------------------+
                |                                    |
                v                                    v
 +--------------+--------------+       +-------------+-------------+
 | PostgreSQL                  |       | Attachment file storage   |
 | email, attachment, run state|       | original source documents |
 +--------------+--------------+       +---------------------------+
                |
                v
 +--------------+--------------------------------------------------+
 |                       LangGraph workflow                         |
 |                                                                  |
 |  Parse text --> LLM extraction --> RAG enrichment --> Validation |
 +--------------+-------------------------+-------------------------+
                |                         |
                | RAG queries             | traces
                v                         v
 +--------------+--------------+   +------+------+
 | PostgreSQL + pgvector       |   |  LangSmith  |
 | customers, products, policy|   +-------------+
 +--------------+--------------+
                |
                v
        +-------+--------+
        | Routing decision|
        +---+----------+--+
            |          |
      all checks     failed or uncertain
         pass           |
            |           v
            |   +-------+---------+
            |   | Human review UI |
            |   | edit / approve  |
            |   | or reject       |
            |   +-------+---------+
            |           |
            |      rerun RAG and validation
            |           |
            v           v
        +---+-----------+---+             +----------------+
        | Persist draft PO |             | Record rejection|
        +--------+---------+             +----------------+
                 |
                 v
        +--------+---------+
        | Processed POs UI |
        +------------------+
```

### Processing flow

1. The intake service validates and stores the attachment and creates a processing run.
2. `parse_document` extracts text from a PDF, CSV, or plain-text file.
3. `extract_order` calls the OpenAI Responses API using a strict structured-output schema.
4. `enrich_order` retrieves relevant knowledge chunks and resolves customer and SKU aliases.
5. `validate_order` combines extraction-quality, document-math, and authoritative business checks.
6. LangGraph routes the result to `auto_process` or `human_review`.
7. The outcome is committed as a draft order or review case.

Graph nodes return state and do not commit business records independently. Outcome persistence is
centralized so a completed workflow result is stored consistently.

## How RAG adds value

The knowledge base contains human-readable customer, product, and policy documents. For example,
it can retrieve evidence that:

- `Northstar Stores` is a known name for customer `CUST-NORTHSTAR`.
- `MUG-WHT` refers to product `MUG-WHITE-STD`.
- Northstar's approved payment terms are Net 45.
- A supplied shipping address is an approved destination.

RAG enriches messy document language with candidate identifiers and supporting evidence. It is not
the final authority. Resolved identifiers must exist and be active in the operational database,
and price, address, terms, totals, and duplicate checks are deterministic.

## Human-in-the-loop behavior

A failed check creates an open `ReviewCase` linked to the persisted `ProcessingRun`; it does not
leave an in-memory LangGraph execution waiting indefinitely.

The reviewer can edit the extracted order in the React UI and then:

- **Approve with changes:** derived totals are recalculated, RAG and every validation rule run
  again, and a draft order is created only when all checks pass.
- **Reject:** the case and processing run are closed with the reviewer and reason recorded.

If corrected data still fails validation, the case remains open and the new reasons are shown.

## Technology stack

| Area | Technology |
| --- | --- |
| API | FastAPI |
| Orchestration | LangGraph |
| Extraction | OpenAI Responses API with Pydantic structured output |
| Retrieval | OpenAI embeddings and pgvector |
| Database | PostgreSQL 16 |
| Email | Gmail API or multipart webhook |
| Tracing | LangSmith |
| UI | React, TypeScript, Vite |
| Database migrations | Alembic |
| Tests and quality | pytest, Ruff, Vitest, ESLint |

## Repository layout

```text
app/
  routes/             FastAPI transport layer
  services/           Intake, extraction, RAG, Gmail, review, and query use cases
  validation/         Pure extraction, PO, and authoritative validation rules
  workflows/          LangGraph state, nodes, and graph construction
  api.py               Application factory, middleware, and lifecycle
  models.py            SQLAlchemy persistence models
  schemas.py           Purchase-order and workflow domain schemas
frontend/src/
  pages/               Orders, order details, reviews, and review details
  review/              Review form components and derived-total calculations
knowledge_base/        Source documents used to seed RAG
migrations/            Alembic database migrations
scripts/               Setup, Gmail authorization/polling, seeding, and demo generation
tests/                 Backend unit and API-contract tests
output/pdf/            Ready-to-use demonstration purchase orders
```

## Prerequisites

- Python 3.12
- Docker Desktop with Docker Compose
- Node.js and npm
- An OpenAI API key for extraction and embeddings
- Optional: a LangSmith account for tracing
- Optional: a Google Cloud OAuth client for Gmail intake

## Quick start on Windows

### 1. Create the local configuration

```powershell
Copy-Item .env.example .env
```

Set at least the following value in `.env`:

```dotenv
OPENAI_API_KEY=your-openai-api-key
```

Do not commit `.env`, Gmail credentials, OAuth tokens, or API keys.

### 2. Install Python dependencies and start PostgreSQL

From the repository root:

```powershell
.\scripts\setup.ps1
```

The script creates `.venv`, installs the project and development dependencies, and starts the
pgvector-enabled PostgreSQL service from `compose.yaml`.

### 3. Apply database migrations

```powershell
.\.venv\Scripts\alembic.exe upgrade head
```

`AUTO_CREATE_SCHEMA=true` is useful during local development. Set it to `false` in deployed
environments and apply schema changes only through Alembic.

### 4. Seed the RAG knowledge base

```powershell
.\.venv\Scripts\python.exe scripts\seed_knowledge.py
```

This loads `knowledge_base/*.md`, creates embeddings, and stores the chunks in PostgreSQL/pgvector.
Run it again after changing the source documents.

### 5. Start the API

```powershell
.\.venv\Scripts\uvicorn.exe app.api:app --reload
```

- API documentation: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`

### 6. Start the operations UI

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`.

## Configuration

The application reads `.env` through Pydantic settings. See `.env.example` for the complete local
template.

| Variable | Default | Purpose |
| --- | --- | --- |
| `APP_ENV` | `development` | Environment name added to logs and traces |
| `DATABASE_URL` | Local PostgreSQL | Async SQLAlchemy connection URL |
| `ATTACHMENT_DIR` | `data/attachments` | Stored source attachments |
| `MAX_ATTACHMENT_BYTES` | `10485760` | Maximum upload size |
| `AUTO_CREATE_SCHEMA` | `true` | Convenience schema creation for local development |
| `EXTRACTION_BACKEND` | `openai` | Use `development` only for offline development/tests |
| `OPENAI_MODEL` | `gpt-5.4-mini` | Structured extraction model |
| `MIN_EXTRACTION_CONFIDENCE` | `0.85` | Minimum confidence for automatic processing |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Knowledge-base embedding model |
| `RAG_TOP_K` | `4` | Maximum retrieved chunks per query |
| `RAG_MATCH_THRESHOLD` | `0.70` | Similarity threshold for entity resolution |
| `PRICE_TOLERANCE_PERCENT` | `1.0` | Allowed deviation from the authoritative price |
| `LOG_LEVEL` | `INFO` | Console logging level |
| `LANGSMITH_TRACING` | `false` | Enable LangSmith traces |
| `LANGSMITH_PROJECT` | `po-intake-agent` | LangSmith project name |
| `GMAIL_ENABLED` | `false` | Enable periodic Gmail polling |
| `GMAIL_POLLER_IN_API` | `true` | Run polling in the API process for local development |
| `GMAIL_POLL_INTERVAL_SECONDS` | `30` | Poll interval |
| `GMAIL_QUERY` | `is:unread has:attachment newer_than:7d` | Gmail search query |

## Logging and LangSmith tracing

Every API request receives an `x-request-id`. Workflow logs also include the processing-run ID and
node transitions, allowing one document to be followed through parsing, extraction, enrichment,
validation, and routing.

Enable tracing with:

```dotenv
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your-langsmith-api-key
LANGSMITH_PROJECT=po-intake-agent
```

Restart the API after changing these values. LangGraph node inputs may contain extracted document
text, so disable tracing for documents that must not leave the local environment.

## Send a purchase order through the webhook

The webhook accepts one attachment per request:

```powershell
curl.exe -X POST http://127.0.0.1:8000/webhooks/email `
  -F "provider_message_id=demo-message-001" `
  -F "sender=buyer@example.com" `
  -F "subject=Purchase order attached" `
  -F "attachment=@output/pdf/loom-01-rag-enrichment-messy.pdf;type=application/pdf"
```

The response contains `message_id`, `attachment_id`, `run_id`, and the resulting processing
`status`. Inspect the complete result at `GET /runs/{run_id}` or in the React UI.

Use a new `provider_message_id` when intentionally submitting a new email. Reusing an existing ID
returns the existing processing run rather than creating a duplicate.

## Gmail integration

The Gmail integration uses read-only access. It does not delete messages, mark them as read, or
change labels.

### Configure Google OAuth

1. Create or select a project in Google Cloud.
2. Enable the Gmail API.
3. Configure the OAuth consent screen. When the app is in testing, add the mailbox as a test user.
4. Create an OAuth client with application type **Desktop app**.
5. Save the downloaded client file as `secrets/gmail-credentials.json`.
6. Run the one-time authorization flow:

```powershell
.\.venv\Scripts\python.exe scripts\gmail_authorize.py
```

The refreshable token is stored at `secrets/gmail-token.json`. The entire `secrets/` directory is
ignored by Git.

### Enable local polling

```dotenv
GMAIL_ENABLED=true
GMAIL_POLLER_IN_API=true
GMAIL_POLL_INTERVAL_SECONDS=30
GMAIL_QUERY="is:unread has:attachment newer_than:7d"
```

Useful endpoints:

- `GET /integrations/gmail/status` checks configuration and authorization state.
- `POST /integrations/gmail/poll` starts an immediate poll.

For a dedicated mailbox, apply a Gmail label such as `PO-Intake` and use:

```dotenv
GMAIL_QUERY="label:PO-Intake has:attachment"
```

### Multiple attachments and idempotency

One Gmail message can contain multiple supported attachments. The system stores one email record,
then creates a separate attachment and processing run for each PDF, CSV, or text file. If one
attachment fails, the poller logs that failure and continues with the others.

The Gmail message ID and MIME-part ID are stored separately. Polling the mailbox again does not
reprocess an attachment already recorded in the database, including records created by the older
combined-ID format.

### Production poller ownership

Do not start an in-process poller in every API worker. Configure the API with:

```dotenv
GMAIL_ENABLED=true
GMAIL_POLLER_IN_API=false
```

Run exactly one dedicated polling process:

```powershell
.\.venv\Scripts\python.exe scripts\run_gmail_poller.py
```

## Validation and routing rules

Automatic processing requires every applicable check to pass:

- The attachment is identified as a purchase order.
- Extraction meets the configured confidence threshold and has no unresolved warnings.
- Critical fields and line items have high-confidence source evidence.
- PO number, customer, currency, shipping address, total, and line items are present.
- Quantity × unit price matches each line total.
- Line totals match the subtotal, and subtotal + tax matches the total.
- Customer and products resolve to active database records.
- Shipping address and payment terms match the customer record.
- Unit prices match active customer pricing or the product price within tolerance.
- The PO number is unique for that customer.

Any failed check routes the PO to human review. Parsing or extraction exceptions mark the processing
run as `failed`, preserving the error type and message for diagnosis.

## API endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Database-backed health check |
| `POST` | `/webhooks/email` | Submit one email attachment |
| `GET` | `/integrations/gmail/status` | Inspect Gmail configuration |
| `POST` | `/integrations/gmail/poll` | Trigger Gmail polling immediately |
| `GET` | `/runs/{run_id}` | Inspect extraction, RAG evidence, validation, and outcome |
| `GET` | `/orders` | List processed draft orders |
| `GET` | `/orders/{order_id}` | Get one processed order |
| `GET` | `/reviews?status=open` | List review cases |
| `GET` | `/reviews/{review_id}` | Get review data and evidence |
| `POST` | `/reviews/{review_id}/approve` | Submit corrected data for revalidation |
| `POST` | `/reviews/{review_id}/reject` | Reject and close a review case |

## Demo files

Three presentation-ready files are included under `output/pdf/`:

| File | Demonstrates | Expected behavior |
| --- | --- | --- |
| `loom-01-rag-enrichment-messy.pdf` | Messy aliases and layout | RAG resolves the customer and SKUs, then validations decide routing |
| `loom-02-ambiguous-missing-fields.pdf` | Ambiguity and missing information | Extraction warnings or failed required-field checks send it to review |
| `loom-03-image-only-bad-scan.pdf` | Unreadable image-only document | Text parsing fails safely and the run is recorded as failed |

These cases are useful for demonstrating the clean path, RAG evidence, human review, and failure
handling in a Loom walkthrough.

## Tests and quality checks

Run backend validation from the repository root:

```powershell
.\.venv\Scripts\ruff.exe check app tests migrations scripts
.\.venv\Scripts\pytest.exe -q
.\.venv\Scripts\alembic.exe current
.\.venv\Scripts\alembic.exe check
```

Run frontend validation from `frontend/`:

```powershell
npm run lint
npm run test
npm run build
```

The frontend unit tests specifically verify that changing unit price or tax recalculates line
totals, subtotal, and total before approval.

## Current boundaries

- Text-bearing PDF, CSV, and plain-text documents are supported by the extraction pipeline.
- OCR is not implemented. Image files and image-only PDFs fail safely with a persisted failed run.
- Gmail intake processes PDF, CSV, and plain-text attachments; unsupported MIME types are skipped.
- Approved records are internal draft orders. Sending them to an ERP or order-management platform
  is a future integration point.
- The local workflow executes inside the API/poller process. A durable external job queue would be
  the next step for high-volume production processing.
