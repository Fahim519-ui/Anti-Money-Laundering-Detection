# ClearFlow — BOCHK Compliance Dashboard Demo

Interactive prototype for the BOCHK innovation challenge: a cross-border compliance monitoring dashboard with three judge-interactive panels.

## Panels

1. **Transaction Risk Scorer** — PaySim-style transaction scoring (0–100), triggered regulatory rules (FATF, OFAC, PBOC, HKMA), tokenization layer, and GenAI-style explanations
2. **Regulatory Pulse Feed** — Live-style feed from HKMA, PBOC, FATF, OFAC with filtering and RAG-style Q&A
3. **Pattern Anomaly Map** — Industry-corridor Z-score analysis with anomaly briefing narratives

## Enter Your Own Case

Panel 1 is now a **custom case form** — fill in any transaction details and click **Score Transaction**. All three panels update:

- **Panel 1** — Risk score, triggered rules, tokenization, explanations
- **Panel 2** — Regulations filtered for your corridor/purpose
- **Panel 3** — Your corridor highlighted; computed briefing for new corridors

You can also click **Paste JSON instead** to submit a full case object, or use **Load Sample** for pre-built examples.

### Example demo case (Myanmar)

| Field | Value |
|-------|-------|
| Customer | ABC Trading Ltd |
| Amount | 2,300,000 HKD |
| Destination | Myanmar |
| Counterparty | XYZ Ltd |
| Prior history | No |
| Hour | 2 |

Expected score: **87** — FATF, PBOC, HKMA rules triggered

## Quick Start

```bash
cd clearflow-demo
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd backend
uvicorn main:app --reload --port 8080
```

Open [http://localhost:8080](http://localhost:8080)

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/transactions/demo-case` | Demo transaction + risk assessment |
| `GET /api/transactions/{id}/score` | Score a specific transaction |
| `GET /api/regulatory-feed` | Regulatory pulse feed |
| `POST /api/regulatory-query` | RAG-style regulatory Q&A |
| `GET /api/corridor-patterns` | Anomaly map data |
