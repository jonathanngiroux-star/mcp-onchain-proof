#!/usr/bin/env python3
"""Tool definitions for mcp-onchain-proof."""

from mcp.types import Tool

TOOLS = [
    Tool(
        name="generate_attestation",
        description=(
            "Generate and PERSIST a real attestation: computes a payload hash over a canonical "
            "JSON payload, links it to the previous hash (chain), signs it with HMAC, derives a "
            "simulated tx_hash and block number, records the timestamp and attested facts, and "
            "returns the attestation plus its chain position. Chains correctly across calls."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "service": {
                    "type": "string",
                    "description": "Service being attested (e.g. mcp-agent-sla).",
                },
                "subject": {
                    "type": "string",
                    "description": "Subject/account being attested.",
                },
                "period": {
                    "type": "string",
                    "description": "Attestation period (e.g. 2026-10).",
                },
                "deliverable_counts": {
                    "type": "object",
                    "description": "Deliverable counts attested.",
                },
                "sla_compliance_summary": {
                    "type": "object",
                    "description": "SLA compliance summary.",
                },
                "persist": {"type": "boolean", "default": True},
            },
            "required": ["service", "subject", "period"],
        },
    ),
    Tool(
        name="get_audit_trail",
        description=(
            "Return the ordered chain for a subject/service with each attestation's hash, "
            "previous_hash, signature, tx_hash, block number, timestamp, and a computed "
            "chain-integrity verdict (recompute the chain and report whether it verifies)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "subject": {
                    "type": "string",
                    "description": "Filter by subject.",
                },
                "service": {
                    "type": "string",
                    "description": "Filter by service.",
                },
                "limit": {"type": "integer", "default": 50, "minimum": 1, "maximum": 500},
            },
            "required": [],
        },
    ),
    Tool(
        name="verify_attestation",
        description=(
            "Actually recompute the payload hash from the stored payload, recompute the HMAC "
            "signature, verify the chain linkage, and return a verification report with "
            "per-check pass/fail. Support verification of the most recent attestation when no "
            "attestation_id is supplied. If the payload was tampered with, verification FAILS."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "attestation_id": {
                    "type": "string",
                    "description": "Attestation ID; omits means the most recent.",
                },
            },
            "required": [],
        },
    ),
    Tool(
        name="get_price_lock",
        description=(
            "Return the immutable price lock captured at subscribe: plan price USD, monthly/"
            "annual equivalent (annual ~10x with ~17% discount), the billing-token lock record, "
            "a content hash proving price immutability, and the lock timestamp."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "subject": {
                    "type": "string",
                    "description": "Subject/account whose price lock to return.",
                },
                "plan": {
                    "type": "string",
                    "default": "standard",
                    "description": "Plan name.",
                },
            },
            "required": ["subject"],
        },
    ),
]