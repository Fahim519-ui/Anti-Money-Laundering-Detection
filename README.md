# ClearFlow 🔍

> **Cross-Border Compliance Dashboard — BOCHK GBA Strategic Hub**  
> Built for the BOCHK Hackathon 2026 | Theme: Cross-Border × Big Data × GenAI

## The Problem

Cross-border transactions between Hong Kong and Mainland China, Southeast Asia, and beyond are subject to an ever-changing web of regulations — CIPS, SWIFT, HKMA rules, PBOC foreign exchange controls, AML requirements, and sanctions lists. Currently, compliance checks are:

- **Slow** — manual reviews delay legitimate business transactions
- **Reactive** — flags happen after suspicious patterns emerge
- **Opaque** — SMEs and corporates have no visibility into why transactions get flagged or delayed

HKMA issued **HKD 17.8M in AML fines in 2025**. Cross-border fraud losses hit **HKD 8.1B** in the same year.

---

## The Solution

ClearFlow is a **big data compliance monitoring dashboard** that ingests publicly available regulatory data, sanctions lists, and transaction pattern signals to give BOCHK compliance officers — and their SME customers — a live, explainable view of cross-border transaction risk.

---

## Live Demo

🌐 **[https://clearflow-demo-gamma.vercel.app](https://clearflow-demo-gamma.vercel.app)**

### Try This Demo Case
| Field | Value |
|---|---|
| Customer | ABC Trading Ltd |
| Amount (HKD) | 2,300,000 |
| Destination | Myanmar |
| Counterparty | XYZ Ltd |
| Payment Purpose | Trade settlement |
| Hour of Day | 2 |
| Prior Counterparty History | No |

Click **Score Transaction** to see the full compliance explanation with triggered regulatory rules.

---

## Features

### Panel 1 — Transaction Risk Scorer
- Scores transactions **0–100** using a deterministic rule-based engine with weighted regulatory signals
- **Three-layer scoring:** corridor base risk → FATF/OFAC/PBOC rule triggers → behavioural signals (velocity, timing, counterparty history)
- **Dual audience GenAI output:**
  - *Compliance Officer view* — technical rationale citing specific regulation codes and thresholds
  - *SME Customer view* — plain-language explanation with actionable documentation requests
- **Tokenization layer** — customer, account, amount, and counterparty identifiers are replaced with tokens before any data reaches the explanation module (PII protection)
- **Pipeline visualisation:** Transaction → Risk Engine → Tokenization → GenAI Module → Explanation
- **Recommended action** — auto-escalation logic: Hold / Standard Review / Auto-clear

### Panel 2 — Regulatory Pulse Feed
- Regulatory updates from HKMA, PBOC, FATF, OFAC, and MAS — tagged by corridor and severity
- Auto-filters to the active transaction's destination corridor on case submission
- **Regulatory Q&A** — keyword-matched retrieval over the regulatory corpus with synthesised plain-English answers
- Hardcoded priority feed IDs per destination ensure demo reliability (Myanmar, Cambodia, Mainland China, Singapore)

### Panel 3 — Pattern Anomaly Map
- Monitors **8 cross-border corridors** using Z-score trend analysis against 6-week baselines
- Detects structuring patterns (transactions clustering HKD 45k–55k, just below the HKD 60k reporting threshold)
- **GenAI anomaly briefing** — auto-generates a ready-to-share compliance memo for flagged corridors, citing FATF typology references
- **Cross-panel integration** — submitted case automatically computes a corridor Z-score and appears as a case corridor entry in Panel 3

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      CLEARFLOW SYSTEM                        │
├──────────────────┬────────────────────┬──────────────────────┤
│   Frontend       │    Backend         │   Data Sources       │
│   (Vercel)       │    (Railway)       │                      │
│                  │                    │  • transactions.json │
│   index.html     │   main.py          │  • corridor_         │
│   Vanilla JS     │   FastAPI + CORS   │    patterns.json     │
│   Single-page    │                    │  • regulatory_       │
│   dashboard      │   risk_engine.py   │    feed.json         │
│                  │   Rule-based scorer│                      │
│                  │   + tokenization   │  External signals:   │
│                  │                    │  • FATF black/grey   │
│                  │   anomaly_         │  • OFAC SDN list     │
│                  │   detection.py     │  • PBOC FX threshold │
│                  │   Z-score + case   │  • HKMA AML 4.3.2    │
│                  │   corridor compute │                      │
│                  │                    │                      │
│                  │   regulatory_      │                      │
│                  │   service.py       │                      │
│                  │   Feed matching +  │                      │
│                  │   RAG Q&A          │                      │
│                  │                    │                      │
│                  │   case_normalizer  │                      │
│                  │   .py              │                      │
│                  │   Alias resolution │                      │
│                  │   + PII tokenize   │                      │
└──────────────────┴────────────────────┴──────────────────────┘
```

### Three-Layer AI Architecture

| Layer | Implementation | Purpose |
|---|---|---|
| Rules Engine | `risk_engine.py` — hardcoded FATF/OFAC/PBOC/HKMA logic | Deterministic regulatory rule firing |
| Anomaly Scorer | `anomaly_detection.py` — Z-score + structuring detection | Corridor-level pattern flagging |
| Explanation Layer | `risk_engine.py` — template-driven narrative generation | Plain-English rationale, dual audience |

### Risk Scoring Logic (from `risk_engine.py`)

| Signal | Score Delta | Trigger |
|---|---|---|
| Corridor base risk | 8–35 | Destination country |
| FATF blacklist (Myanmar, North Korea, Iran) | +24 | Hardcoded blacklist |
| FATF greylist (Cambodia, Vietnam, Laos…) | +18 | Hardcoded greylist |
| PBOC FX threshold exceeded (HKD 500k) | +6–18 | Amount ratio |
| Structuring pattern (HKD 45k–59k) | +15 | Amount range |
| No prior counterparty history | +12 | Boolean flag |
| High transaction velocity (>50/30d) | +10 | Frequency field |
| Off-hours transaction (<6 or >22) | +6 | Hour of day |
| Historical compliance flags | +5 per flag | Flag count |

Minimum score floors: FATF blacklist → 82, blacklist + large amount → 85, blacklist + no counterparty history → 87.

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/transactions` | List demo transactions |
| `GET` | `/api/transactions/{id}/score` | Score a stored transaction |
| `POST` | `/api/score` | Score a custom transaction case |
| `GET` | `/api/regulatory-feed` | Get regulatory feed (filterable) |
| `POST` | `/api/regulatory-query` | RAG-style Q&A over regulatory corpus |
| `GET` | `/api/corridor-patterns` | Get corridor anomaly data |
| `POST` | `/api/corridor-context` | Get corridor context for a case |
| `GET` | `/api/form-options` | Get dropdown options for frontend form |
| `GET` | `/api/demo-content` | Full demo bundle (feed + RAG + patterns) |

---

## Tech Stack

### Backend
- **FastAPI** — REST API framework with CORS middleware
- **Python 3.13** — core language
- **Pydantic** — request body validation (`TransactionCase` model)
- **Rule-based risk engine** — deterministic scoring with FATF/OFAC/PBOC/HKMA logic
- **Keyword-matched RAG** — regulatory corpus retrieval with synthesised answers
- **numpy / pandas / scikit-learn** — data processing and anomaly detection utilities

### Frontend
- **HTML / CSS / JavaScript** — single `index.html` file, no build step
- **Vanilla JS fetch API** — all backend calls via `API` constant pointing to Railway

### Infrastructure
- **Vercel** — frontend hosting (static `index.html`)
- **Railway** — backend hosting (`uvicorn main:app` on port 8080)

---

## Corridors Monitored

| Corridor | Risk Tier | Key Regulatory Triggers |
|---|---|---|
| HK → Mainland China | Medium | PBOC FX controls, CIPS |
| HK → Singapore | Low | MAS AML framework |
| HK → Vietnam | Medium | FATF grey list monitoring |
| HK → Malaysia | Low–Medium | BNM AML rules |
| HK → Indonesia | Medium | OJK framework |
| HK → Myanmar | **Very High** | OFAC sanctions, FATF black list |
| HK → Cambodia | **High** | FATF grey list, structuring risk |
| HK → Thailand | Low–Medium | BOT regulations |

Supported destination aliases in `case_normalizer.py`: China / PRC / Mainland China, Burma / Myanmar, DPRK / North Korea, HK / Hong Kong.

---

## Getting Started

### Prerequisites
- Python 3.10+
- pip

### Backend Setup

```bash
# Clone the repository
git clone https://github.com/your-team/clearflow-demo
cd clearflow-demo/backend

# Install dependencies
pip install -r requirements.txt

# Run the backend
uvicorn main:app --reload --port 8080
```

### Frontend Setup

```bash
# No build step needed — open directly or serve locally
cd frontend
python -m http.server 8081
# Visit http://localhost:8081
```

The frontend `API` constant in `index.html` must point to your backend URL:
```javascript
const API = "https://clearflow-backend-production-020a.up.railway.app";
// or for local dev:
const API = "http://localhost:8080";
```

### Environment Variables

No API keys required for the core demo. The explanation layer uses template-driven generation in `risk_engine.py` — no external LLM calls at runtime.

---

## Project Structure

```
clearflow-demo/
├── frontend/
│   └── index.html              # Single-page dashboard (all three panels)
├── backend/
│   ├── main.py                 # FastAPI app, CORS, all API routes
│   ├── risk_engine.py          # Rule-based scorer, tokenization, explanation generation
│   ├── anomaly_detection.py    # Z-score corridor analysis, anomaly narratives
│   ├── regulatory_service.py   # Feed matching, hardcoded destination IDs, RAG Q&A
│   ├── case_normalizer.py      # Destination alias resolution, PII tokenization, defaults
│   ├── data/
│   │   ├── transactions.json       # Demo transaction cases
│   │   ├── corridor_patterns.json  # 8-corridor baseline + anomaly data
│   │   └── regulatory_feed.json    # HKMA/PBOC/FATF/OFAC regulatory updates
│   └── requirements.txt
├── pyproject.toml
└── README.md
```

---

## Design Decisions

### Rule-based engine, not ML model
The risk scorer in `risk_engine.py` is fully deterministic — weighted rules firing against FATF/OFAC/PBOC/HKMA signal thresholds. This ensures:
- **Auditability** — every score is fully traceable to specific rule weights
- **Demo reliability** — no model training data or inference dependencies
- **Regulatory defensibility** — each triggered rule maps to a real, citable document

In production, this layer would be replaced or augmented with an XGBoost model trained on BOCHK's internal SAR dataset.

### Template-driven explanation, not free LLM generation
Compliance explanations in `generate_explanation()` are built from case-specific data inserted into structured templates — not free-form LLM output. This eliminates hallucination risk for regulatory citations while still producing natural, readable output.

### Tokenization before explanation
`tokenize_transaction()` replaces all PII with tokens before the explanation module runs. The explanation layer only ever sees `Customer_ABCTRA`, `Account_088346`, `Transaction_46F3` — never the original values.

### Hardcoded feed priority per destination
`DESTINATION_FEED_IDS` in `regulatory_service.py` guarantees that known high-risk destinations (Myanmar, Cambodia, Mainland China, Singapore) always surface the most relevant regulatory cards — ensuring demo reliability regardless of query matching quality.

---

## Business Case

| Metric | Value | Source |
|---|---|---|
| HKMA AML fines (2025) | HKD 17.8M | HKMA press releases |
| HK cross-border fraud losses (2025) | HKD 8.1B | JFIU annual report |
| Annual alerts (JFIU-derived) | 22,000 | JFIU statistics |
| False positive reduction (conservative) | 40% | McKinsey AML benchmark |
| Annual investigation cost saving | HKD 409,200 | 22,000 × HKD 465 × 40% |
| Annual escalation hours saving | HKD 762,300 | 3,300 cases × 6hrs × HKD 385 |

**Academic validation:** Hosseini et al. (2024) demonstrated 40–60% false positive reduction using similar ML pipeline architecture. ClearFlow extends this with a GenAI explainability layer and SME-facing customer portal that existing research prototypes do not include.

---

## Team

Built for **BOCHK Hackathon 2026**

| Member | Role |
|---|---|
| Fahim | Backend, frontend dashboard, fdeployment (Vercel + Railway) |
| Sneha | Business case, revenue forecast |
| Logan | Pain points, dashboard design |
| Vini | Target market, customer analysis |
| Finn | Cost-benefit analysis |

---

## References

- Hosseini, F., Costa, L., & Carter, E. (2024). AI/ML-Powered Anti-Money Laundering Pipelines: Architecting Real-Time Risk Detection Systems Using Hadoop, PySpark, and Distributed Graph-Based Algorithms. *American Journal of Technology Advancement*, 1(7), 75–91.
- HKMA AML Guideline 4.3.2 — Enhanced due diligence for high-risk jurisdictions
- FATF Public Statement — March 2025
- OFAC SDN List Update — May 2025
- PBOC SAFE Circular 2025-07

---

*ClearFlow is a hackathon prototype. Transaction data is synthetic. Regulatory references are real but may not reflect the most current versions. Not for production use.*
