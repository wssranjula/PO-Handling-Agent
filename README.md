# Purchase Order Intake Agent

A LangGraph workflow that receives purchase orders by email webhook, extracts structured data,
validates it, and routes clean orders or review cases.

Extraction uses the OpenAI Responses API with a Pydantic structured-output schema. The response
includes the purchase order, verbatim source evidence, extraction warnings, and confidence. The
graph routes low-confidence or weakly supported output to review before business-rule validation.

## Local setup

```powershell
./scripts/setup.ps1
.\.venv\Scripts\Activate.ps1
$env:OPENAI_API_KEY = "your-api-key"
uvicorn app.api:app --reload
```

Alternatively, put `OPENAI_API_KEY` in `.env`. The default extraction model is `gpt-5.4-mini` and
can be changed with `OPENAI_MODEL`. Set `EXTRACTION_BACKEND=development` only for offline tests.

## Logs and tracing

Application events are logged to the console with a request ID and processing-run ID. Change
verbosity with `LOG_LEVEL=DEBUG` or `LOG_LEVEL=INFO`.

LangSmith tracing is configured through `LANGSMITH_TRACING`, `LANGSMITH_API_KEY`, and
`LANGSMITH_PROJECT`. Traces are grouped in the `po-intake-agent` project and tagged with the app
environment. LangGraph node inputs can include extracted document text, so disable tracing when
working with documents that must not leave the local environment.

## Seed the RAG knowledge base

The local knowledge base contains customers, approved ship-to addresses, product aliases, contract
prices, and order-acceptance policy. Seed or refresh it with:

```powershell
.\.venv\Scripts\python.exe scripts\seed_knowledge.py
```

The command generates embeddings with `text-embedding-3-small` and stores 1536-dimensional vectors
in PostgreSQL/pgvector. The source documents are under `knowledge_base/`.

For each order, the graph now:

1. Extracts structured data with the LLM.
2. Retrieves customer, product, and policy chunks with vector search.
3. Resolves customer and SKU identifiers.
4. Checks active records, approved address, payment terms, contract prices, totals, and duplicate PO.
5. Creates a persisted draft order or an open review case.

`GET /runs/{run_id}` returns the original extraction, resolved order, retrieved evidence, validation
results, and draft order. `GET /reviews` lists review cases. Submit corrected structured data to
`POST /reviews/{review_id}/approve`; the corrected order is enriched and validated again before a
draft can be created.

Open `http://127.0.0.1:8000/docs` for the API UI.

## Operations UI

The React dashboard has separate pages for validated orders and purchase orders requiring human
review. Reviewers can correct extracted values and approve them (which reruns RAG and validation),
or reject the purchase order with an auditable reason.

Keep the API running, then start the UI in a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`. The Vite development server proxies `/api` requests to the FastAPI
server on port 8000. Use `npm run build` to create a production bundle.

The dashboard uses `GET /orders`, `GET /orders/{order_id}`, `GET /reviews`, and
`GET /reviews/{review_id}`. Decisions are submitted to `POST /reviews/{review_id}/approve` or
`POST /reviews/{review_id}/reject`.

## Try an intake

Create `sample-po.txt`:

```text
PO Number: PO-10482
Issue Date: 2026-08-10
Currency: USD
Customer: Acme Retail
Shipping Address: 10 Main Street
Subtotal: 4850.00
Tax: 0
Total: 4850.00
item|BTL-BLU-16|Blue insulated bottle 16oz|100|48.50
```

Then submit it:

```powershell
curl.exe -X POST http://127.0.0.1:8000/webhooks/email `
  -F "provider_message_id=demo-001" `
  -F "sender=buyer@example.com" `
  -F "subject=Purchase order PO-10482" `
  -F "attachment=@sample-po.txt;type=text/plain"
```

## Current boundary

The LLM extraction path supports text-bearing PDFs, CSV, and text attachments. OCR for scanned
PDFs/images is not implemented yet. Approved records are persisted as internal draft orders; a
connector to an external ERP or order-management system remains future work.
