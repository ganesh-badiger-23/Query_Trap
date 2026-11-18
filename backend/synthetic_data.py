"""Dynamic Synthetic Honeytoken Generator for Query Trap.

Pre-computes and caches realistic decoy records at application startup to protect
against resource exhaustion (DoS) and expensive per-request cryptographic operations.
These records trap attackers with realistic credentials, financial ledgers,
canary tokens, and configuration secrets.
"""
from __future__ import annotations

import copy
import secrets
from typing import Any

# Global memory cache holding pre-computed honeytoken datasets
_PRECOMPUTED_DATASETS: dict[str, list[dict[str, Any]]] = {}
_CACHE_INITIALIZED: bool = False


def _build_synthetic_user_credentials() -> list[dict[str, Any]]:
    """Pre-compute realistic user credential records with Argon2id and canary tokens."""
    return [
        {
            "id": 10892,
            "username": "sys_admin_shadow",
            "email": "root.shadow@northstar-internal.corp",
            "role": "Global Superuser",
            "canary_token": f"CANARY-USR-{secrets.token_hex(4).upper()}",
            "password_hash": "$argon2id$v=19$m=65536,t=3,p=4$CANARY_SALT_89a1$e92f1b8a901c2384a37b12f8",
            "api_secret": f"canary_sec_live_{secrets.token_hex(12)}",
            "access_level": "Tier-1 / Root",
            "last_auth": "2026-11-04 09:12:44 UTC",
        },
        {
            "id": 10893,
            "username": "ops_vault_lead",
            "email": "c.vance@northstar-internal.corp",
            "role": "Vault Approver",
            "canary_token": f"CANARY-USR-{secrets.token_hex(4).upper()}",
            "password_hash": "$argon2id$v=19$m=65536,t=3,p=4$CANARY_SALT_99bc$71a0b3c4d5e6f7a8b901cd23",
            "api_secret": f"canary_sec_live_{secrets.token_hex(12)}",
            "access_level": "Tier-2 / Operations",
            "last_auth": "2026-11-04 08:45:10 UTC",
        },
        {
            "id": 10894,
            "username": "audit_compliance_agent",
            "email": "audit.compliance@shadow-mesh.net",
            "role": "Security Auditor",
            "canary_token": f"CANARY-USR-{secrets.token_hex(4).upper()}",
            "password_hash": "$argon2id$v=19$m=65536,t=3,p=4$CANARY_SALT_44de$9081726354abcedf01234567",
            "api_secret": f"canary_sec_live_{secrets.token_hex(12)}",
            "access_level": "Tier-2 / Auditor",
            "last_auth": "2026-11-03 23:59:01 UTC",
        },
        {
            "id": 10895,
            "username": "backup_service_daemon",
            "email": "svc.daemon@northstar-cloud.internal",
            "role": "Automated Service Worker",
            "canary_token": f"CANARY-SVC-{secrets.token_hex(4).upper()}",
            "password_hash": "$2b$12$e8Y1x9Z.CANARY.DAEMON.HASH.V92837162534f5e6a7b8c9d0",
            "api_secret": f"canary_sec_live_{secrets.token_hex(12)}",
            "access_level": "Automated Pipe",
            "last_auth": "2026-11-04 10:00:15 UTC",
        },
    ]


def _build_synthetic_financial_ledger() -> list[dict[str, Any]]:
    """Pre-compute realistic financial records with SWIFT, IBAN, and vault signatures."""
    return [
        {
            "id": 7701,
            "account_ref": f"SWIFT-CHASE-NY-9941-{secrets.token_hex(2).upper()}",
            "beneficiary": "Northstar Shadow Reserve Ltd",
            "decoy_balance": "$4,821,950.00",
            "currency": "USD",
            "routing_code": "021000021-DEC",
            "vault_signature": f"0x{secrets.token_hex(16)}",
            "canary_hash": f"SHA256:{secrets.token_hex(16)}",
            "ledger_status": "RESTRICTED CUSTODY",
        },
        {
            "id": 7702,
            "account_ref": f"IBAN-CH93-0000-8812-{secrets.token_hex(2).upper()}",
            "beneficiary": "Overseas Liquidity Trust Zurich",
            "decoy_balance": "€3,910,400.00",
            "currency": "EUR",
            "routing_code": "SWISS-ZB-8812-DEC",
            "vault_signature": f"0x{secrets.token_hex(16)}",
            "canary_hash": f"SHA256:{secrets.token_hex(16)}",
            "ledger_status": "OFFSHORE ESCROW",
        },
        {
            "id": 7703,
            "account_ref": f"CANARY-TREASURY-0041-{secrets.token_hex(2).upper()}",
            "beneficiary": "Corporate Strategic Reserve",
            "decoy_balance": "$12,450,000.00",
            "currency": "USD",
            "routing_code": "FEDWIRE-011000015",
            "vault_signature": f"0x{secrets.token_hex(16)}",
            "canary_hash": f"SHA256:{secrets.token_hex(16)}",
            "ledger_status": "CANARY MONITORED",
        },
    ]


def _build_synthetic_system_secrets() -> list[dict[str, Any]]:
    """Pre-compute cloud infrastructure secrets with full RSA private keys and AWS secrets."""
    rsa_key_body = (
        "MIIEowIBAAKCAQEA0rK4b5xG+V/1qQvR8X2v5a9mK3y7Z9nL2p4w6t8r0s2u4v6x8z0B2d4f"
        "6h8j0l2n4p6r8t0v2x4z6B8d0f2h4j6l8n0p2r4t6v8x0z2B4d6f8h0j2l4n6p8r0t2v4x6z"
        "8B0d2f4h6j8l0n2p4r6t8v0x2z4B6d8f0h2j4l6n8p0r2t4v6x8z0B2d4f6h8j0l2n4p6r8t"
        "0v2x4z6B8d0f2h4j6l8n0p2r4t6v8x0z2B4d6f8h0j2l4n6p8r0t2v4x6z8B0d2f4h6j8l0n"
        "CANARY_PRECOMPUTED_KEY_SIGNATURE_NORTHSTAR_ENTERPRISE_INTERNAL_VAULT_NODE"
    )
    return [
        {
            "id": 1,
            "parameter": "AWS_CANARY_SECRET_ACCESS_KEY",
            "synthetic_value": f"canary_wJalrXUtnFEMI/K7MDENG/bPxRfiCY{secrets.token_hex(6)}",
            "environment": "PRODUCTION_VAULT",
            "classification": "TOP SECRET · CANARY DECOY",
            "canary_alert_id": f"ALERT-HONEY-{secrets.token_hex(4).upper()}",
        },
        {
            "id": 2,
            "parameter": "DATABASE_MASTER_SUPERUSER_URL",
            "synthetic_value": f"postgres://shadow_admin:decoy_vault_{secrets.token_hex(4)}@10.0.8.44:5432/core_vault",
            "environment": "PRIMARY_DATABASE_CLUSTER",
            "classification": "TOP SECRET · HONEYPOT TRAP",
            "canary_alert_id": f"ALERT-HONEY-{secrets.token_hex(4).upper()}",
        },
        {
            "id": 3,
            "parameter": "JWT_SIGNING_PRIVATE_KEY",
            "synthetic_value": (
                "-----BEGIN CANARY RSA PRIVATE KEY-----\n"
                f"{rsa_key_body}\n"
                "-----END CANARY RSA PRIVATE KEY-----"
            ),
            "environment": "AUTH_MICROSERVICE",
            "classification": "CRITICAL CREDENTIAL",
            "canary_alert_id": f"ALERT-HONEY-{secrets.token_hex(4).upper()}",
        },
    ]


def _build_synthetic_canary_inventory() -> list[dict[str, Any]]:
    """Pre-compute enterprise security hardware inventory items with canary serials."""
    return [
        {
            "id": 9901,
            "item": "Northstar Cryptographic Keycard (Hardware V4)",
            "category": "Enterprise Security Hardware",
            "canary_serial": f"CANARY-HW-{secrets.token_hex(4).upper()}",
            "firmware": "v4.1.9-decoy-hardened",
            "access_tier": "Confidential / Air-Gapped",
            "price": "$1,250.00",
            "inventory_status": "RESERVED SHADOW STOCK",
        },
        {
            "id": 9902,
            "item": "Quantum-Resistant HSM Decoy Node",
            "category": "Cryptographic Appliances",
            "canary_serial": f"CANARY-HW-{secrets.token_hex(4).upper()}",
            "firmware": "v2.0.4-canary-active",
            "access_tier": "Confidential / Defense Grade",
            "price": "$4,800.00",
            "inventory_status": "SECURE REPLICA NODE",
        },
        {
            "id": 9903,
            "item": "Titanium Physical Security Token Pro",
            "category": "Tactical Hardware",
            "canary_serial": f"CANARY-HW-{secrets.token_hex(4).upper()}",
            "firmware": "v7.3.0-monitored",
            "access_tier": "Executive Restricted",
            "price": "$780.00",
            "inventory_status": "MONITORED CANARY UNIT",
        },
        {
            "id": 9904,
            "item": "Encrypted Tactical Field Communicator",
            "category": "Tactical Hardware",
            "canary_serial": f"CANARY-HW-{secrets.token_hex(4).upper()}",
            "firmware": "v5.2.1-decoy",
            "access_tier": "Field Operative Only",
            "price": "$2,400.00",
            "inventory_status": "STANDBY INVENTORY",
        },
    ]


def warm_honeytoken_cache(force_refresh: bool = False) -> None:
    """Pre-compute and warm the global honeytoken cache at application startup."""
    global _PRECOMPUTED_DATASETS, _CACHE_INITIALIZED
    if _CACHE_INITIALIZED and not force_refresh:
        return

    _PRECOMPUTED_DATASETS = {
        "synthetic_user_credentials": _build_synthetic_user_credentials(),
        "synthetic_financial_ledger": _build_synthetic_financial_ledger(),
        "synthetic_system_secrets": _build_synthetic_system_secrets(),
        "synthetic_canary_inventory": _build_synthetic_canary_inventory(),
    }
    _CACHE_INITIALIZED = True


# Pre-compute and populate cache immediately on module load
warm_honeytoken_cache()


def is_cache_warmed() -> bool:
    """Check if the cryptographic honeytoken cache is initialized."""
    return _CACHE_INITIALIZED and bool(_PRECOMPUTED_DATASETS)


def get_cache_stats() -> dict[str, int]:
    """Return record counts for all pre-computed honeytoken datasets."""
    return {k: len(v) for k, v in _PRECOMPUTED_DATASETS.items()}


def generate_synthetic_decoy(raw_query: str) -> tuple[str, list[dict[str, Any]]]:
    """Analyze query intent and return pre-computed cached synthetic records.

    Protected against DoS and CPU exhaustion: all Argon2id hashes, RSA keys,
    and canary honeytokens are pre-computed at application startup.
    """
    if not _CACHE_INITIALIZED:
        warm_honeytoken_cache()

    q = (raw_query or "").lower()

    # 1. User & Credential Injections
    if any(k in q for k in ("user", "admin", "pass", "auth", "login", "hash", "member", "role", "account_id")):
        return "synthetic_user_credentials", copy.deepcopy(_PRECOMPUTED_DATASETS["synthetic_user_credentials"])

    # 2. Financial / Ledger Injections
    if any(k in q for k in ("financ", "bank", "balance", "card", "salary", "money", "fund", "wallet", "ledger")):
        return "synthetic_financial_ledger", copy.deepcopy(_PRECOMPUTED_DATASETS["synthetic_financial_ledger"])

    # 3. System Secrets / Cloud Keys Injections
    if any(k in q for k in ("secret", "key", "config", "token", "env", "aws", "jwt", "database", "schema")):
        return "synthetic_system_secrets", copy.deepcopy(_PRECOMPUTED_DATASETS["synthetic_system_secrets"])

    # 4. Default Tautology & Threat Payloads (e.g. ' OR '1'='1, UNION SELECT, XSS)
    return "synthetic_canary_inventory", copy.deepcopy(_PRECOMPUTED_DATASETS["synthetic_canary_inventory"])


def get_available_synthetic_datasets() -> dict[str, list[dict[str, Any]]]:
    """Return all predefined synthetic dummy datasets for interactive honeypot exploration."""
    if not _CACHE_INITIALIZED:
        warm_honeytoken_cache()

    return {
        "synthetic_users": copy.deepcopy(_PRECOMPUTED_DATASETS["synthetic_user_credentials"]),
        "synthetic_financials": copy.deepcopy(_PRECOMPUTED_DATASETS["synthetic_financial_ledger"]),
        "synthetic_secrets": copy.deepcopy(_PRECOMPUTED_DATASETS["synthetic_system_secrets"]),
        "synthetic_inventory": copy.deepcopy(_PRECOMPUTED_DATASETS["synthetic_canary_inventory"]),
    }
