"""ClearFlow Demo API — BOCHK cross-border compliance dashboard."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from anomaly_detection import enrich_corridor_patterns, get_anomaly_summary, get_case_corridor_context
from case_normalizer import get_form_options, normalize_transaction
from regulatory_service import (
    DEMO_RAG_ANSWER,
    DEMO_RAG_QUESTION,
    filter_feed,
    get_default_demo_feed,
    get_feed_for_case,
)
from risk_engine import score_transaction

DATA_DIR = Path(__file__).parent / "data"
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

app = FastAPI(title="ClearFlow", description="BOCHK Cross-Border Compliance Dashboard Demo")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def load_json(name: str) -> Any:
    with open(DATA_DIR / name, encoding="utf-8") as f:
        return json.load(f)


class RegulatoryQuery(BaseModel):
    question: str


class TransactionCase(BaseModel):
    id: str | None = None
    customer: str
    account: str | None = None
    amount_hkd: float
    currency: str | None = "HKD"
    destination_country: str
    origin_country: str | None = "Hong Kong"
    corridor: str | None = None
    payment_purpose: str | None = None
    counterparty: str | None = None
    industry: str | None = None
    company_size: str | None = None
    account_age_months: int | None = 12
    risk_rating: str | None = None
    transaction_frequency_30d: int | None = 1
    hour_of_day: int | None = 12
    prior_counterparty_history: bool | None = True
    historical_compliance_flags: int | None = 0


@app.get("/api/health")
def health():
    return {"status": "ok", "product": "ClearFlow", "version": "demo-1.0"}


@app.get("/api/transactions")
def list_transactions():
    return load_json("transactions.json")


@app.get("/api/transactions/{txn_id}/score")
def get_transaction_score(txn_id: str):
    transactions = load_json("transactions.json")
    txn = next((t for t in transactions if t["id"] == txn_id), None)
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return score_transaction(txn)


@app.get("/api/transactions/demo-case")
def get_demo_case():
    transactions = load_json("transactions.json")
    demo = next((t for t in transactions if t.get("is_demo_case")), transactions[0])
    result = score_transaction(demo)
    return {"transaction": demo, "assessment": result}


@app.get("/api/form-options")
def form_options():
    return get_form_options()


@app.post("/api/score")
def score_custom_case(body: TransactionCase):
    try:
        txn = normalize_transaction(body.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    assessment = score_transaction(txn)
    patterns = enrich_corridor_patterns(load_json("corridor_patterns.json"))
    corridor_context = get_case_corridor_context(txn, patterns)
    feed = get_feed_for_case(load_json("regulatory_feed.json"), txn)

    return {
        "transaction": txn,
        "assessment": assessment,
        "relevant_regulations": feed,
        "corridor_context": corridor_context,
        "demo_rag": {"question": DEMO_RAG_QUESTION, "answer": DEMO_RAG_ANSWER},
    }


@app.get("/api/regulatory-feed")
def get_regulatory_feed(
    source: str | None = None,
    tag: str | None = None,
    corridor: str | None = None,
    destination: str | None = None,
    demo: bool = False,
):
    feed = load_json("regulatory_feed.json")
    if demo:
        return get_default_demo_feed(feed)
    return filter_feed(feed, source=source, tag=tag, corridor=corridor, destination=destination)


@app.get("/api/demo-content")
def demo_content():
    feed = load_json("regulatory_feed.json")
    patterns = enrich_corridor_patterns(load_json("corridor_patterns.json"))
    cambodia = next((p for p in patterns if p["corridor"] == "HK → Cambodia" and p.get("anomaly_flag")), None)
    return {
        "regulatory_feed": get_default_demo_feed(feed),
        "rag": {"question": DEMO_RAG_QUESTION, "answer": DEMO_RAG_ANSWER},
        "cambodia_briefing": cambodia,
        "demo_case": {
            "customer": "ABC Trading Ltd",
            "amount_hkd": 2300000,
            "destination_country": "Myanmar",
            "counterparty": "XYZ Ltd",
            "payment_purpose": "Trade settlement",
            "industry": "Retail",
            "prior_counterparty_history": False,
            "hour_of_day": 2,
            "transaction_frequency_30d": 12,
        },
    }


@app.post("/api/regulatory-query")
def regulatory_query(body: RegulatoryQuery):
    """RAG-style demo — keyword matching over regulatory corpus."""
    feed = load_json("regulatory_feed.json")
    q = body.question.lower()
    keywords = [w for w in q.replace("?", "").split() if len(w) > 3]

    scored: list[tuple[int, dict]] = []
    for item in feed:
        text = " ".join(
            [item["title"], item["summary"], " ".join(item["tags"]), " ".join(item["affected_corridors"])]
        ).lower()
        match_score = sum(1 for kw in keywords if kw in text)
        if "southeast asia" in q or "sea" in q:
            if any("→" in c and c.split("→")[1].strip() in ("Vietnam", "Cambodia", "Thailand", "Malaysia", "Indonesia", "Myanmar") for c in item["affected_corridors"]):
                match_score += 2
        if "100k" in q or "100,000" in q or "usd" in q:
            if "threshold" in text or "reporting" in text:
                match_score += 2
        if "30 days" in q or "last month" in q:
            match_score += 1
        if match_score > 0:
            scored.append((match_score, item))

    scored.sort(key=lambda x: x[0], reverse=True)
    matches = [item for _, item in scored[:3]]

    if not matches:
        answer = (
            "No specific regulatory changes in the last 30 days match your query. "
            "Consider reviewing FATF grey-list updates and HKMA AML Guideline 4.3.2 for general cross-border guidance."
        )
    else:
        bullets = [f"• [{m['source']}, {m['date']}] {m['title']}" for m in matches]
        answer = (
            f"Based on the ingested regulatory corpus, the following updates are relevant to your question:\n\n"
            + "\n".join(bullets)
            + "\n\n"
            + matches[0]["summary"]
        )

    return {
        "question": body.question,
        "answer": answer,
        "sources": [{"id": m["id"], "source": m["source"], "title": m["title"], "date": m["date"]} for m in matches],
    }


@app.get("/api/corridor-patterns")
def get_corridor_patterns(anomalies_only: bool = False, highlight_corridor: str | None = None):
    patterns = enrich_corridor_patterns(load_json("corridor_patterns.json"))
    if anomalies_only:
        patterns = [p for p in patterns if p.get("anomaly_flag")]
    summary = get_anomaly_summary(patterns if not anomalies_only else load_json("corridor_patterns.json"))
    if highlight_corridor:
        for p in patterns:
            p["highlighted"] = p["corridor"] == highlight_corridor
    return {"summary": summary, "patterns": patterns}


@app.post("/api/corridor-context")
def corridor_context_for_case(body: TransactionCase):
    try:
        txn = normalize_transaction(body.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    patterns = enrich_corridor_patterns(load_json("corridor_patterns.json"))
    return get_case_corridor_context(txn, patterns)


if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
