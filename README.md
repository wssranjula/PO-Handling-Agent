# Purchase Order Intake Agent

A LangGraph workflow that receives purchase orders by email webhook, extracts structured data,
validates it, and routes clean orders or review cases.

## Local setup

```powershell
./scripts/setup.ps1
.\.venv\Scripts\Activate.ps1
uvicorn app.api:app --reload
```

Open `http://127.0.0.1:8000/docs` for the API UI.

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

The first vertical slice uses a deterministic development extractor. The graph boundary is ready
for a schema-constrained LLM extractor, OCR fallback, RAG-based customer/product resolution, and a
resumable human-review interrupt. External order creation is deliberately a no-op until those
validation layers are implemented and evaluated.
