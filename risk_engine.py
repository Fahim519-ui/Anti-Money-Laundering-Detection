"""ClearFlow Transaction Risk Scorer — rule-based engine with explainable output."""

from __future__ import annotations

from typing import Any

# FATF jurisdiction lists (demo data aligned with BOCHK challenge brief)
FATF_BLACKLIST = {"North Korea", "Iran", "Myanmar"}
FATF_GREYLIST = {"Laos", "Nepal", "Vietnam", "Papua New Guinea", "Cambodia"}

PBOC_FX_THRESHOLD_HKD = 500_000
HK_REPORTING_THRESHOLD_HKD = 60_000

CORRIDOR_BASE_RISK = {
    "HK → Myanmar": 30,
    "HK → Cambodia": 25,
    "HK → Vietnam": 18,
    "HK → Mainland China": 12,
    "HK → Singapore": 8,
    "HK → Malaysia": 10,
    "HK → Indonesia": 12,
    "HK → Thailand": 8,
    "Hong Kong → Myanmar": 30,
    "Hong Kong → Cambodia": 25,
    "Hong Kong → Vietnam": 18,
    "Hong Kong → Mainland China": 12,
    "Hong Kong → Singapore": 8,
    "Hong Kong → Malaysia": 10,
    "Hong Kong → Indonesia": 12,
    "Hong Kong → Thailand": 8,
}

DESTINATION_BASE_RISK = {
    "Myanmar": 30,
    "Cambodia": 25,
    "Vietnam": 18,
    "North Korea": 35,
    "Iran": 35,
    "Mainland China": 12,
    "Singapore": 8,
    "Malaysia": 10,
    "Indonesia": 12,
    "Thailand": 8,
    "Laos": 20,
    "Nepal": 20,
    "Papua New Guinea": 18,
}


def tokenize_transaction(txn: dict[str, Any]) -> dict[str, str]:
    return {
        "customer": txn.get("customer_token", "Customer_?"),
        "account": txn.get("account_token", "Account_?"),
        "amount": txn.get("amount_token", "Transaction_?"),
        "counterparty": txn.get("counterparty_token", "Counterparty_?"),
    }


def score_transaction(txn: dict[str, Any]) -> dict[str, Any]:
    score = 0.0
    triggered_rules: list[dict[str, Any]] = []
    risk_factors: list[dict[str, Any]] = []

    corridor = txn.get("corridor", "")
    destination = txn.get("destination_country", "")
    amount = float(txn.get("amount_hkd", 0))

    # Corridor / destination baseline risk
    base = CORRIDOR_BASE_RISK.get(corridor) or DESTINATION_BASE_RISK.get(destination, 10)
    score += base
    risk_factors.append(
        {
            "factor": "corridor_risk",
            "weight": round(base / 100, 2),
            "detail": f"Base corridor risk for {corridor}",
        }
    )

    # FATF blacklist
    if destination in FATF_BLACKLIST:
        delta = 24
        score += delta
        triggered_rules.append(
            {
                "source": "FATF",
                "rule": "High-risk jurisdiction (black list)",
                "reference": "FATF Public Statement — March 2025",
                "severity": "critical",
            }
        )
        triggered_rules.append(
            {
                "source": "OFAC",
                "rule": "Sanctions screening required — SDN-corridor watch list",
                "reference": "OFAC SDN List Update — May 2025",
                "severity": "critical",
            }
        )
        risk_factors.append(
            {
                "factor": "country_risk",
                "weight": 0.34,
                "detail": f"{destination} on FATF black list",
            }
        )

    # FATF grey list (if not already blacklisted)
    elif destination in FATF_GREYLIST:
        delta = 18
        score += delta
        triggered_rules.append(
            {
                "source": "FATF",
                "rule": "Jurisdiction under increased monitoring (grey list)",
                "reference": "FATF Grey List — March 2025",
                "severity": "high",
            }
        )
        risk_factors.append(
            {
                "factor": "country_risk",
                "weight": 0.22,
                "detail": f"{destination} on FATF grey list",
            }
        )

    # PBOC FX threshold
    if amount > PBOC_FX_THRESHOLD_HKD:
        ratio = amount / PBOC_FX_THRESHOLD_HKD
        delta = min(18, 6 + (ratio - 1) * 2.5)
        score += delta
        triggered_rules.append(
            {
                "source": "PBOC",
                "rule": "Individual FX reporting threshold exceeded",
                "reference": "SAFE Circular 2025-07 / PBOC FX controls",
                "severity": "high" if ratio > 3 else "medium",
            }
        )
        risk_factors.append(
            {
                "factor": "amount_threshold",
                "weight": 0.28,
                "detail": f"HKD {amount:,.0f} exceeds PBOC threshold by {ratio:.1f}x",
            }
        )

    # Structuring pattern (just below reporting threshold)
    if HK_REPORTING_THRESHOLD_HKD * 0.75 <= amount < HK_REPORTING_THRESHOLD_HKD:
        delta = 15
        score += delta
        triggered_rules.append(
            {
                "source": "FATF",
                "rule": "Potential structuring below HKD 60k reporting threshold",
                "reference": "FATF Typology ML-2024-07",
                "severity": "high",
            }
        )
        risk_factors.append(
            {
                "factor": "structuring_pattern",
                "weight": 0.25,
                "detail": f"Amount HKD {amount:,.0f} clustered below reporting threshold",
            }
        )

    # No prior counterparty history
    if not txn.get("prior_counterparty_history", True):
        delta = 12
        score += delta
        triggered_rules.append(
            {
                "source": "HKMA",
                "rule": "Enhanced due diligence — no prior counterparty relationship",
                "reference": "HKMA AML Guideline 4.3.2",
                "severity": "medium",
            }
        )
        risk_factors.append(
            {
                "factor": "counterparty_flag",
                "weight": 0.21,
                "detail": "Counterparty has no prior transaction history with BOCHK",
            }
        )

    # High transaction frequency (BoC Pay / velocity)
    freq = txn.get("transaction_frequency_30d", 0)
    if freq > 50:
        delta = 10
        score += delta
        triggered_rules.append(
            {
                "source": "HKMA",
                "rule": "High-velocity digital payment pattern",
                "reference": "HKMA BoC Pay monitoring circular — May 2025",
                "severity": "medium",
            }
        )
        risk_factors.append(
            {
                "factor": "velocity",
                "weight": 0.15,
                "detail": f"{freq} transactions in 30 days on digital payment rails",
            }
        )

    # Off-hours transaction
    hour = txn.get("hour_of_day", 12)
    if hour < 6 or hour > 22:
        delta = 6
        score += delta
        risk_factors.append(
            {
                "factor": "timing_anomaly",
                "weight": 0.08,
                "detail": f"Transaction at {hour:02d}:00 — outside normal business hours",
            }
        )

    # Historical compliance flags
    flags = txn.get("historical_compliance_flags", 0)
    if flags > 0:
        delta = flags * 5
        score += delta
        risk_factors.append(
            {
                "factor": "compliance_history",
                "weight": 0.1,
                "detail": f"{flags} prior compliance flag(s) on account",
            }
        )

    final_score = min(100, max(0, round(score)))

    has_critical = any(r.get("severity") == "critical" for r in triggered_rules)
    if destination in FATF_BLACKLIST:
        final_score = max(final_score, 82)
    if has_critical and amount > PBOC_FX_THRESHOLD_HKD:
        final_score = max(final_score, 85)
    if destination in FATF_BLACKLIST and not txn.get("prior_counterparty_history", True):
        final_score = max(final_score, 87)

    if final_score >= 70 or has_critical:
        risk_level = "High"
    elif final_score >= 40:
        risk_level = "Medium"
    else:
        risk_level = "Low"

    tokens = tokenize_transaction(txn)
    explanation = generate_explanation(txn, final_score, triggered_rules, tokens)
    sme_explanation = generate_sme_explanation(txn, final_score, triggered_rules, tokens)

    return {
        "transaction_id": txn["id"],
        "risk_score": final_score,
        "risk_level": risk_level,
        "triggered_rules": triggered_rules,
        "risk_factors": risk_factors,
        "tokenized_view": tokens,
        "explanation_compliance_officer": explanation,
        "explanation_sme": sme_explanation,
        "recommended_action": get_recommended_action(final_score, triggered_rules),
    }


def generate_explanation(
    txn: dict[str, Any],
    score: int,
    rules: list[dict[str, Any]],
    tokens: dict[str, str],
) -> str:
    """GenAI-style compliance officer narrative with case-specific detail."""
    destination = txn.get("destination_country", "unknown jurisdiction")
    amount = float(txn.get("amount_hkd", 0))
    corridor = txn.get("corridor", "")
    parts: list[str] = []

    severity_word = "high" if score >= 70 else "moderate" if score >= 40 else "low"
    parts.append(
        f"This transaction is {severity_word} risk (score {score}/100) on the {corridor} corridor."
    )

    if destination in FATF_BLACKLIST:
        parts.append(
            f"The destination jurisdiction ({destination}) appears on the FATF black list "
            f"as of March 2025 and is subject to OFAC sanctions screening."
        )
    elif destination in FATF_GREYLIST:
        parts.append(
            f"The destination jurisdiction ({destination}) appears on the FATF grey list "
            f"as of March 2025 and is under increased monitoring."
        )

    if amount > PBOC_FX_THRESHOLD_HKD:
        ratio = amount / PBOC_FX_THRESHOLD_HKD
        parts.append(
            f"The amount (HKD {amount:,.0f}) exceeds PBOC's individual FX threshold "
            f"(HKD {PBOC_FX_THRESHOLD_HKD:,}) by {ratio:.1f}x."
        )

    if not txn.get("prior_counterparty_history", True):
        parts.append(
            f"The counterparty ({tokens['counterparty']}) has no prior transaction history with BOCHK."
        )

    hour = txn.get("hour_of_day", 12)
    if hour < 6 or hour > 22:
        parts.append(
            f"The transaction was initiated at {hour:02d}:00 — outside normal business hours, "
            f"which elevates typology risk for this corridor."
        )

    freq = txn.get("transaction_frequency_30d", 0)
    if freq > 30:
        parts.append(
            f"Elevated velocity detected: {freq} transactions in the past 30 days on this payment rail."
        )

    hkma_rules = [r for r in rules if r["source"] == "HKMA"]
    if hkma_rules:
        parts.append(
            f"Under {hkma_rules[0]['reference']}, enhanced due diligence is required before proceeding."
        )
    elif score >= 70 or any(r.get("severity") == "critical" for r in rules):
        parts.append(
            "Enhanced due diligence is required under HKMA AML Guideline 4.3.2 before this transaction can be released."
        )

    if rules:
        sources = sorted({r["source"] for r in rules})
        parts.append(f"Triggered regulatory frameworks: {', '.join(sources)}.")

    return " ".join(parts)


def generate_sme_explanation(
    txn: dict[str, Any],
    score: int,
    rules: list[dict[str, Any]],
    tokens: dict[str, str],
) -> str:
    """Customer-facing plain-English explanation."""
    if score < 40:
        return (
            "Your transaction is being processed normally. No additional documentation is required at this time."
        )

    docs: list[str] = []
    if any(r["source"] == "PBOC" for r in rules):
        docs.append("proof of the underlying trade contract or invoice")
    if any(r["source"] == "FATF" for r in rules):
        docs.append("beneficial ownership documentation for the recipient")
    if any(r["source"] == "HKMA" for r in rules):
        docs.append("a brief explanation of the business purpose for this transfer")

    doc_text = ", ".join(docs) if docs else "supporting business documentation"

    return (
        f"Your transfer of HKD {txn.get('amount_hkd', 0):,.0f} to {txn.get('destination_country', 'the destination')} "
        f"requires a brief compliance review before it can be released. This is a standard check for cross-border "
        f"payments — not an indication of wrongdoing. To speed up processing, please provide: {doc_text}. "
        f"Reference: {txn.get('id', 'N/A')}."
    )


def get_recommended_action(score: int, rules: list[dict[str, Any]]) -> str:
    if score >= 70 or any(r.get("severity") == "critical" for r in rules):
        return "Escalate to senior compliance review — hold transaction pending enhanced due diligence"
    if score >= 40:
        return "Assign to compliance analyst for standard review within 4 business hours"
    return "Auto-clear — continue standard monitoring"
