"""Database-agnostic inspection and routing for application-layer integration.

The gateway deliberately accepts trusted operations as zero-argument callbacks.
Untrusted request text is inspected for risk but is never passed to either DB
callback and is never interpreted as SQL by this module.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Mapping

SIGNATURES = (
    ("XSS · script tag", re.compile(r"<\s*script\b", re.I), 35),
    ("XSS · javascript URL", re.compile(r"javascript\s*:", re.I), 25),
    ("XSS · event handler", re.compile(r"\bon(?:error|load|click|mouseover|submit|focus)\s*=", re.I), 25),
    ("XSS · embedded tag", re.compile(r"<\s*(?:iframe|object|embed|svg)\b", re.I), 25),
    ("SQLi · tautology", re.compile(r"(?:'\s*or\s*'?\s*1\s*'?\s*=\s*'?\s*1|(?:\b|'|\")\s*or\s+(?:\d+\s*=\s*\d+|'[^']*'\s*=\s*'?[^']*'?|\"[^\"]*\"\s*=\s*\"?[^\"]*\"?|''\s*=\s*'?'?|true\s*=\s*true))", re.I), 40),
    ("SQLi · UNION SELECT", re.compile(r"\bunion\s+(?:all\s+)?select\b", re.I), 35),
    ("SQLi · destructive statement", re.compile(r"(?:;\s*)?\b(?:drop\s+table|delete\s+from|truncate\s+table|alter\s+table)\b", re.I), 40),
    ("SQLi · comment terminator", re.compile(r"(?:--(?:\s|$)|/\*.*?\*/|#(?:\s|$))", re.I), 15),
    ("SQLi · time-based delay", re.compile(r"\b(?:sleep\s*\(|benchmark\s*\(|pg_sleep\s*\()", re.I), 35),
    ("Reconnaissance · unauthorized port probe", re.compile(r"(?:\b(?:port|dest_port)\s*=\s*(?:3000|5100|5300|22|23|3306|5432|8080|6379|27017|9200)\b|:(?:3000|5100|5300|22|23|3306|5432|8080|6379|27017|9200)(?:\b|/|\?)|(?:\b|&)(?:admin_port|dbg_port|internal_port)\b)", re.I), 40),
)

DEFAULT_SENSITIVITY = {
    "users": 40,
    "financial_records": 40,
    "public_catalog": 10,
}
DEFAULT_THRESHOLD = 31


@dataclass(frozen=True)
class RiskAssessment:
    threats: tuple[str, ...]
    payload_severity: int
    asset_sensitivity: int
    anomaly_score: int
    risk_score: int
    asset: str
    risk_band: str


@dataclass(frozen=True)
class GatewayOutcome:
    assessment: RiskAssessment
    route: str
    bucket: str
    result: Any
    event: dict[str, Any]


def _infer_asset(raw: str) -> str:
    for asset in DEFAULT_SENSITIVITY:
        if re.search(rf"\b{re.escape(asset)}\b", raw, re.I):
            return asset
    return "unknown"


def classify_query(raw: str, threats: tuple[str, ...] | list[str], asset: str, bucket: str) -> tuple[str, str, str]:
    """Return (query_type, db_target, action_taken) for security operations telemetry."""
    threat_str = " ".join(threats).lower()
    raw_lower = raw.lower().strip()

    if bucket == "safe":
        if asset == "public_catalog" or any(p in raw_lower for p in ("notebook", "lamp", "stationery", "mug", "catalog", "item", "product")):
            qtype = "Product Catalog Search"
            action = "200 OK · Bounded lookup on production.db"
        else:
            qtype = "Benign Parameter Search"
            action = "200 OK · Executed safely on production.db"
        db_target = "production.db [Catalog]"
        return qtype, db_target, action

    # Threat / Attack cases
    db_target = "honeypot.db / Canary Store"
    if "unauthorized port probe" in threat_str or "port=" in raw_lower:
        qtype = "Port Reconnaissance Probe"
        action = "302 Diverted · Deflected port scan away from internal service"
    elif "destructive statement" in threat_str or "drop table" in raw_lower or "delete from" in raw_lower:
        qtype = "SQLi · Destructive Drop/Delete"
        action = "302 Diverted · Shielded production tables from DROP/DELETE"
    elif "tautology" in threat_str or "'1'='1" in raw_lower or "'or'" in raw_lower:
        qtype = "SQLi · Tautology Bypass ('1'='1)"
        action = "302 Diverted · Trapped bypass attempt; served synthetic records"
    elif "union select" in threat_str or "union" in raw_lower:
        qtype = "SQLi · UNION Data Leak Probe"
        action = "302 Diverted · Fed synthetic columns with canary hashes"
    elif "time-based delay" in threat_str or "sleep" in raw_lower:
        qtype = "SQLi · Blind Delay Fingerprint"
        action = "302 Diverted · Zero thread stall; routed to honeypot"
    elif "script tag" in threat_str or "event handler" in threat_str or "xss" in threat_str or "<script" in raw_lower or "onerror=" in raw_lower:
        qtype = "Cross-Site Scripting (XSS)"
        action = "302 Diverted · Neutralized browser execution payload"
    elif "users" in asset.lower() or "users" in raw_lower or "admin" in raw_lower:
        qtype = "Credential Exfiltration (users table)"
        action = "302 Diverted · Fed fake admin accounts & Argon2id canary hashes"
    elif "financial" in asset.lower() or "financial" in raw_lower:
        qtype = "Financial Exfiltration (ledger)"
        action = "302 Diverted · Fed decoy offshore corporate accounts"
    else:
        qtype = "Suspicious Injection Attack"
        action = "302 Diverted · Transparently isolated to honeypot decoy"

    return qtype, db_target, action


def assess_payload(
    raw: str,
    *,
    asset: str | None = None,
    sensitivity_map: Mapping[str, int] | None = None,
) -> RiskAssessment:
    """Calculate the capped 0–100 score using an application-supplied asset."""
    if not isinstance(raw, str):
        raise TypeError("raw payload must be text")

    vectors = tuple(name for name, pattern, _ in SIGNATURES if pattern.search(raw))
    severity = min(40, sum(weight for _, pattern, weight in SIGNATURES if pattern.search(raw)))
    selected_asset = (asset or _infer_asset(raw)).strip().lower() or "unknown"
    sensitivity_by_asset = dict(DEFAULT_SENSITIVITY)
    if sensitivity_map:
        for name, value in sensitivity_map.items():
            if not isinstance(value, int) or not 0 <= value <= 40:
                raise ValueError("asset sensitivity values must be integers from 0 to 40")
            sensitivity_by_asset[name.strip().lower()] = value
    sensitivity = sensitivity_by_asset.get(selected_asset, 20)

    special_fraction = len(re.findall(r"[^\w\s]", raw)) / max(1, len(raw))
    anomaly = min(
        20,
        (8 if len(raw) > 180 else 0)
        + (7 if ";" in raw else 0)
        + (10 if special_fraction > 0.22 else 0)
        + (5 if raw.count("'") >= 2 else 0),
    )
    score = min(100, severity + sensitivity + anomaly)
    band = "critical" if score >= 70 else ("suspicious" if score >= DEFAULT_THRESHOLD else "safe")
    return RiskAssessment(vectors, severity, sensitivity, anomaly, score, selected_asset, band)


def inspect_and_route(
    raw: str,
    *,
    production_operation: Callable[[], Any],
    honeypot_operation: Callable[[], Any],
    asset: str | None = None,
    sensitivity_map: Mapping[str, int] | None = None,
    threshold: int = DEFAULT_THRESHOLD,
    client_ip: str = "unknown",
    site_context: str = "",
    audit: Callable[[dict[str, Any]], None] | None = None,
) -> GatewayOutcome:
    """Inspect text, audit, then invoke exactly one trusted DB operation.

    Production and honeypot operations should use their application's own
    repository/connection and bound parameters. The raw payload is never passed
    into either operation. If a durable audit callback is supplied, it runs
    before DB access so the host can enforce its own audit-failure policy.
    """
    if threshold < 1 or threshold > 100:
        raise ValueError("threshold must be between 1 and 100")
    assessment = assess_payload(raw, asset=asset, sensitivity_map=sensitivity_map)
    isolated = assessment.risk_score >= threshold
    route = "honeypot" if isolated else "production"
    bucket = "honeypot" if isolated else "safe"
    query_type, db_target, action_taken = classify_query(raw, assessment.threats, assessment.asset, bucket)
    event = {
        "id": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ"),
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "ip": client_ip,
        "query": raw[:2000],
        "threats": list(assessment.threats),
        "risk": assessment.risk_score,
        "risk_band": assessment.risk_band,
        "bucket": bucket,
        "route": route,
        "table": assessment.asset,
        "site_context": site_context[:300],
        "query_type": query_type,
        "db_target": db_target,
        "action_taken": action_taken,
    }
    if audit is not None:
        audit(event)

    # Exactly one repository callback is selected; no DB handle is swapped or
    # shared, which lets an existing app preserve its connection pool/config.
    operation = honeypot_operation if isolated else production_operation
    result = operation()
    return GatewayOutcome(assessment, route, bucket, result, event)
