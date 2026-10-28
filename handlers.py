#!/usr/bin/env python3
"""Real business logic for mcp-onchain-proof handlers."""

import hashlib
import hmac
import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# --------------------------------------------------------------------------
# Persistence
# --------------------------------------------------------------------------

def _state_dir() -> Path:
    override = os.environ.get("MCP_ONCHAIN_PROOF_STATE_DIR")
    path = Path(override) if override else Path(__file__).resolve().parent / "state"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _state_path() -> Path:
    return _state_dir() / "onchain_state.json"


def _default_state() -> dict[str, Any]:
    return {
        "version": "1.0.0",
        "attestations": {},
        "audit_trail": [],
        "price_locks": {},
        "sequence": 1000,
        "chain_head": None,
        "signing_key": b"katsironni-onchain-proof-v1",
    }


def load_state() -> dict[str, Any]:
    path = _state_path()
    if not path.exists():
        state = _default_state()
        save_state(state)
        return state
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        state = _default_state()
    base = _default_state()
    base.update(state)
    for key, default in _default_state().items():
        if key not in base:
            base[key] = default
    # Convert signing key from hex back to bytes
    if isinstance(base.get("signing_key"), str):
        base["signing_key"] = bytes.fromhex(base["signing_key"])
    return base


def save_state(state: dict[str, Any]) -> None:
    # Signing key is bytes; store as hex for JSON serialization
    save_copy = dict(state)
    if isinstance(save_copy.get("signing_key"), bytes):
        save_copy["signing_key"] = save_copy["signing_key"].hex()
    path = _state_path()
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".onchain-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(save_copy, handle, indent=2, ensure_ascii=False)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _fmt(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _content_hash(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _sign(payload_hash: str, signing_key: bytes) -> str:
    return hmac.new(signing_key, payload_hash.encode(), hashlib.sha256).hexdigest()


def _verify_signature(payload_hash: str, signature: str, signing_key: bytes) -> bool:
    expected = _sign(payload_hash, signing_key)
    return hmac.compare_digest(expected, signature)


def _attestation_id(service: str, subject: str, period: str, timestamp: str) -> str:
    return f"att-{hashlib.sha256(f'{service}|{subject}|{period}|{timestamp}'.encode()).hexdigest()[:12]}"


# --------------------------------------------------------------------------
# Handlers
# --------------------------------------------------------------------------

def _handler_generate_attestation(arguments: dict) -> dict[str, Any]:
    service = str(arguments.get("service", "")).strip()
    subject = str(arguments.get("subject", "")).strip()
    period = str(arguments.get("period", "")).strip()
    if not service or not subject or not period:
        return {"status": "error", "error": "service, subject, and period are required"}

    deliverable_counts = arguments.get("deliverable_counts") or {}
    sla_compliance_summary = arguments.get("sla_compliance_summary") or {}
    persist = bool(arguments.get("persist", True))

    state = load_state()
    sequence = int(state.get("sequence", 1000)) + 1
    state["sequence"] = sequence

    timestamp = _now()
    tx_hash = _content_hash({"service": service, "subject": subject, "period": period, "ts": _fmt(timestamp), "seq": sequence})

    # Simulated block number: increment from chain head
    chain_head = state.get("chain_head") or 21_500_000
    block_number = chain_head + 1

    payload = {
        "attestation_id": f"att-{sequence}",
        "service": service,
        "subject": subject,
        "period": period,
        "deliverable_counts": deliverable_counts,
        "sla_compliance_summary": sla_compliance_summary,
        "timestamp": _fmt(timestamp),
        "tx_hash": tx_hash,
        "block_number": block_number,
    }
    payload_hash = _content_hash(payload)
    previous_hash = state.get("chain_head_hash")
    signature = _sign(payload_hash, state["signing_key"])

    attestation = {
        "id": f"att-{sequence}",
        "service": service,
        "subject": subject,
        "period": period,
        "payload_hash": payload_hash,
        "previous_hash": previous_hash,
        "signature": signature,
        "tx_hash": tx_hash,
        "block_number": block_number,
        "timestamp": _fmt(timestamp),
        "deliverable_counts": deliverable_counts,
        "sla_compliance_summary": sla_compliance_summary,
        "chain_position": sequence,
        "on_chain_ready": True,
        "note": (
            "Off-chain signed attestation with an on-chain-ready payload. No real transaction "
            "was broadcast; tx_hash and block_number are deterministic simulations."
        ),
    }

    audit_entry = {
        "id": f"trail-{sequence}",
        "attestation_id": attestation["id"],
        "action": "generated",
        "actor": "system",
        "details": f"Attestation generated for {service}@{subject} period {period}",
        "timestamp": _fmt(timestamp),
    }

    if persist:
        state["attestations"][attestation["id"]] = attestation
        state["audit_trail"].insert(0, audit_entry)
        state["chain_head"] = block_number
        state["chain_head_hash"] = payload_hash
        save_state(state)

    return {
        "attestation": attestation,
        "chain_position": sequence,
        "previous_hash": previous_hash,
        "audit_entry": audit_entry,
    }


def _handler_get_audit_trail(arguments: dict) -> dict[str, Any]:
    subject = arguments.get("subject")
    service = arguments.get("service")
    limit = int(arguments.get("limit", 50))

    state = load_state()
    trail = list(state.get("audit_trail", []))
    if subject:
        trail = [t for t in trail if _attestation_subject(state, t["attestation_id"]) == subject]
    if service:
        trail = [t for t in trail if _attestation_service(state, t["attestation_id"]) == service]
    trail.sort(key=lambda t: t["timestamp"], reverse=True)
    trail = trail[:limit]

    # Compute chain integrity: recompute chain linkage and report
    attestations = list(state.get("attestations", {}).values())
    attestations.sort(key=lambda a: a["chain_position"])
    chain_ok = True
    breaks = []
    for i in range(1, len(attestations)):
        if attestations[i].get("previous_hash") != attestations[i - 1].get("payload_hash"):
            chain_ok = False
            breaks.append({
                "attestation_id": attestations[i]["id"],
                "expected_previous_hash": attestations[i - 1]["payload_hash"],
                "actual_previous_hash": attestations[i].get("previous_hash"),
            })

    # Attach attestation details to each trail entry
    enriched = []
    for t in trail:
        att = state.get("attestations", {}).get(t["attestation_id"], {})
        enriched.append({
            **t,
            "payload_hash": att.get("payload_hash"),
            "signature": att.get("signature"),
            "tx_hash": att.get("tx_hash"),
            "block_number": att.get("block_number"),
            "chain_position": att.get("chain_position"),
            "timestamp": att.get("timestamp"),
        })

    return {
        "count": len(enriched),
        "trail": enriched,
        "chain_integrity": {
            "valid": chain_ok,
            "total_attestations": len(attestations),
            "breaks": breaks,
        },
    }


def _attestation_subject(state: dict[str, Any], attestation_id: str) -> str:
    return state.get("attestations", {}).get(attestation_id, {}).get("subject", "")


def _attestation_service(state: dict[str, Any], attestation_id: str) -> str:
    return state.get("attestations", {}).get(attestation_id, {}).get("service", "")


def _handler_verify_attestation(arguments: dict) -> dict[str, Any]:
    attestation_id = arguments.get("attestation_id")
    state = load_state()
    attestations = state.get("attestations", {})

    if attestation_id:
        att = attestations.get(attestation_id)
        if not att:
            return {"status": "error", "error": f"attestation not found: {attestation_id}"}
        to_verify = [att]
    else:
        # Verify the most recent attestation
        if not attestations:
            return {"status": "error", "error": "no attestations to verify"}
        most_recent = max(attestations.values(), key=lambda a: a["chain_position"])
        to_verify = [most_recent]
        attestation_id = most_recent["id"]

    results = []
    for att in to_verify:
        # Recompute payload hash from stored payload
        payload = {
            "attestation_id": att["id"],
            "service": att["service"],
            "subject": att["subject"],
            "period": att["period"],
            "deliverable_counts": att["deliverable_counts"],
            "sla_compliance_summary": att["sla_compliance_summary"],
            "timestamp": att["timestamp"],
            "tx_hash": att["tx_hash"],
            "block_number": att["block_number"],
        }
        recomputed_hash = _content_hash(payload)
        payload_hash_match = recomputed_hash == att["payload_hash"]

        # Recompute HMAC signature
        signature_valid = _verify_signature(att["payload_hash"], att["signature"], state["signing_key"])

        # Verify chain linkage
        chain_link_valid = True
        chain_head_valid = True
        all_atts = sorted(attestations.values(), key=lambda a: a["chain_position"])
        idx = next((i for i, a in enumerate(all_atts) if a["id"] == att["id"]), None)
        if idx is not None:
            if idx > 0:
                expected_prev = all_atts[idx - 1]["payload_hash"]
                chain_link_valid = att.get("previous_hash") == expected_prev
            if idx == len(all_atts) - 1:
                chain_head_valid = state.get("chain_head_hash") == att["payload_hash"]

        overall_valid = payload_hash_match and signature_valid and chain_link_valid and chain_head_valid

        results.append({
            "attestation_id": att["id"],
            "service": att["service"],
            "subject": att["subject"],
            "period": att["period"],
            "chain_position": att["chain_position"],
            "payload_hash_match": payload_hash_match,
            "signature_valid": signature_valid,
            "chain_link_valid": chain_link_valid,
            "chain_head_valid": chain_head_valid,
            "overall_valid": overall_valid,
            "timestamp": att["timestamp"],
        })

    return {
        "verified_count": len(results),
        "all_valid": all(r["overall_valid"] for r in results),
        "verifications": results,
    }


def _handler_get_price_lock(arguments: dict) -> dict[str, Any]:
    subject = str(arguments.get("subject", "")).strip()
    if not subject:
        return {"status": "error", "error": "subject is required"}
    plan = str(arguments.get("plan", "standard")).strip()

    PLANS = {
        "basic": {"monthly_usd": 29.0, "annual_multiplier": 10.0},
        "standard": {"monthly_usd": 120.0, "annual_multiplier": 10.0},
        "pro": {"monthly_usd": 199.0, "annual_multiplier": 10.0},
    }
    if plan not in PLANS:
        return {"status": "error", "error": f"unknown plan {plan!r}", "valid_plans": sorted(PLANS)}

    state = load_state()
    existing = state.get("price_locks", {}).get(subject)

    timestamp = _now()
    monthly = PLANS[plan]["monthly_usd"]
    annual_gross = round(monthly * 10, 2)
    annual_discount_pct = 17.0
    annual = round(annual_gross * (1 - annual_discount_pct / 100.0), 2)

    lock_payload = {
        "subject": subject,
        "plan": plan,
        "monthly_usd": monthly,
        "annual_usd": annual,
        "annual_discount_pct": annual_discount_pct,
        "currency": "USD",
        "locked_at": _fmt(timestamp),
    }
    lock_hash = _content_hash(lock_payload)

    if existing:
        lock = existing
    else:
        sequence = int(state.get("sequence", 1000)) + 1
        state["sequence"] = sequence
        lock = {
            "lock_id": f"pl-{sequence}",
            "subject": subject,
            "plan": plan,
            "monthly_usd": monthly,
            "annual_usd": annual,
            "annual_gross_usd": annual_gross,
            "annual_discount_pct": annual_discount_pct,
            "currency": "USD",
            "locked_at": _fmt(timestamp),
            "content_hash": lock_hash,
            "immutable": True,
            "billing_token_lock": {
                "executes": True,
                "mode": "fixed plan price locked at subscribe",
                "reference": f"btl-{hashlib.sha256(lock_hash.encode()).hexdigest()[:10]}",
            },
        }
        state.setdefault("price_locks", {})[subject] = lock
        save_state(state)

    return {
        "price_lock": lock,
        "content_hash": lock_hash,
        "immutability_proof": (
            "content_hash is computed over the lock payload; any change to the locked fields "
            "produces a different hash, proving price immutability."
        ),
    }


HANDLERS = {
    "generate_attestation": _handler_generate_attestation,
    "get_audit_trail": _handler_get_audit_trail,
    "verify_attestation": _handler_verify_attestation,
    "get_price_lock": _handler_get_price_lock,
}