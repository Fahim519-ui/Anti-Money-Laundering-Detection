"""Normalize user-provided cases into a consistent transaction format."""

from __future__ import annotations

import re
import uuid
from typing import Any

DESTINATION_ALIASES: dict[str, str] = {
    "china": "Mainland China",
    "mainland china": "Mainland China",
    "prc": "Mainland China",
    "peoples republic of china": "Mainland China",
    "singapore": "Singapore",
    "vietnam": "Vietnam",
    "thailand": "Thailand",
    "malaysia": "Malaysia",
    "indonesia": "Indonesia",
    "myanmar": "Myanmar",
    "burma": "Myanmar",
    "cambodia": "Cambodia",
    "laos": "Laos",
    "nepal": "Nepal",
    "iran": "Iran",
    "north korea": "North Korea",
    "dprk": "North Korea",
    "korea": "North Korea",
    "papua new guinea": "Papua New Guinea",
    "hong kong": "Hong Kong",
    "hk": "Hong Kong",
}

KNOWN_DESTINATIONS = {
    "Mainland China",
    "Singapore",
    "Vietnam",
    "Thailand",
    "Malaysia",
    "Indonesia",
    "Myanmar",
    "Cambodia",
    "Laos",
    "Nepal",
    "Iran",
    "North Korea",
    "Papua New Guinea",
}


def _slug_token(prefix: str, value: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9]", "", value)[:6].upper() or "X"
    return f"{prefix}_{clean}"


def normalize_destination(value: str) -> str:
    key = value.strip().lower()
    return DESTINATION_ALIASES.get(key, value.strip().title())


def normalize_transaction(raw: dict[str, Any]) -> dict[str, Any]:
    """Fill defaults, aliases, corridor, and tokens for any user-provided case."""
    destination = normalize_destination(str(raw.get("destination_country", "")))
    if not destination:
        raise ValueError("destination_country is required")

    origin = normalize_destination(str(raw.get("origin_country", "Hong Kong") or "Hong Kong"))
    origin_short = "HK" if origin == "Hong Kong" else origin
    corridor = raw.get("corridor") or f"{origin_short} → {destination}"

    customer = str(raw.get("customer", "")).strip() or "Unknown Customer"
    counterparty = str(raw.get("counterparty", "")).strip() or "Unknown Counterparty"
    account = str(raw.get("account", "")).strip() or str(abs(hash(customer)) % 10_000_000).zfill(8)

    amount = float(raw.get("amount_hkd", 0))
    if amount <= 0:
        raise ValueError("amount_hkd must be greater than 0")

    txn_id = str(raw.get("id", "")).strip() or f"TXN-{uuid.uuid4().hex[:8].upper()}"

    return {
        "id": txn_id,
        "customer": customer,
        "customer_token": raw.get("customer_token") or _slug_token("Customer", customer),
        "account": account,
        "account_token": raw.get("account_token") or _slug_token("Account", account),
        "amount_hkd": amount,
        "amount_token": raw.get("amount_token") or f"Transaction_{txn_id[-4:]}",
        "currency": raw.get("currency") or "HKD",
        "destination_country": destination,
        "origin_country": origin,
        "corridor": corridor,
        "payment_purpose": raw.get("payment_purpose") or "Cross-border transfer",
        "counterparty": counterparty,
        "counterparty_token": raw.get("counterparty_token") or _slug_token("Counterparty", counterparty),
        "industry": raw.get("industry") or "General",
        "company_size": raw.get("company_size") or "SME",
        "account_age_months": int(raw.get("account_age_months", 12)),
        "risk_rating": raw.get("risk_rating") or "Medium",
        "transaction_frequency_30d": int(raw.get("transaction_frequency_30d", 1)),
        "hour_of_day": int(raw.get("hour_of_day", 12)),
        "prior_counterparty_history": bool(raw.get("prior_counterparty_history", True)),
        "historical_compliance_flags": int(raw.get("historical_compliance_flags", 0)),
    }


def get_form_options() -> dict[str, Any]:
    return {
        "destinations": sorted(KNOWN_DESTINATIONS),
        "industries": [
            "Retail",
            "Electronics",
            "Manufacturing",
            "Financial Services",
            "Logistics",
            "Commodities",
            "Trade",
            "Hospitality",
            "General",
        ],
        "company_sizes": ["SME", "Corporate", "Enterprise"],
        "risk_ratings": ["Low", "Medium", "High"],
        "currencies": ["HKD", "RMB", "USD"],
        "payment_purposes": [
            "Trade settlement",
            "BoC Pay merchant settlement",
            "Wealth management transfer",
            "Goods procurement",
            "Remittance",
            "Cross-border transfer",
        ],
    }
