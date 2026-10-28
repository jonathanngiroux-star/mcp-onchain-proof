# mcp-onchain-proof

MCP server for **On-Chain Proof-of-Service Audit Trail** - every renewal, SLA credit, and
deliverable timestamped on-chain as auditor-grade evidence.

Buyers: crypto founders with LP oversight, DAOs with treasury exposure, regulated EU entities.
Pricing: $120-250/mo standalone; $49-99/mo add-on. Price-lock clause: fixed plan price in the
billing token at subscribe — on-chain price immutability.

No web3/eth-account library or network access is required: the server uses hashlib.sha256 and
HMAC from the Python standard library to build a real hash chain, signatures, and simulated
tx_hash/block numbers. It is explicit that attestations are off-chain signed with on-chain-ready
payloads.

## Tools

### `generate_attestation`
Generate and PERSIST a real attestation.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `service` | string | **required** | Service being attested |
| `subject` | string | **required** | Subject/account being attested |
| `period` | string | **required** | Attestation period (e.g. 2026-10) |
| `deliverable_counts` | object | - | Deliverable counts attested |
| `sla_compliance_summary` | object | - | SLA compliance summary |
| `persist` | boolean | `true` | Persist to state |

Returns the attestation with payload_hash, previous_hash (chain linkage), HMAC signature,
tx_hash, block number, timestamp, and chain position. Chains correctly across calls.

### `get_audit_trail`
Return the ordered chain for a subject/service.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `subject` | string | - | Filter by subject |
| `service` | string | - | Filter by service |
| `limit` | integer | 50 | Maximum entries (1-500) |

Returns each attestation's hash, previous_hash, signature, tx_hash, block number, timestamp,
plus a computed chain-integrity verdict (recomputed chain verification).

### `verify_attestation`
Verify an attestation by recomputing hashes and signatures.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `attestation_id` | string | - | Attestation ID; omits = most recent |

Returns per-check pass/fail: payload_hash_match, signature_valid, chain_link_valid,
chain_head_valid, overall_valid. Tampered payloads FAIL verification.

### `get_price_lock`
Return the immutable price lock captured at subscribe.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `subject` | string | **required** | Subject/account |
| `plan` | string | `standard` | Plan name |

Returns monthly price, annual equivalent (10x monthly less 17% discount), billing-token lock
record, content hash proving price immutability, and lock timestamp.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

State persisted in `./state/onchain_state.json`. Override with `MCP_ONCHAIN_PROOF_STATE_DIR`.

## Connecting to an MCP client

```json
{
  "mcpServers": {
    "onchain-proof": {
      "command": "python3",
      "args": ["/tmp/v3-services/mcp-onchain-proof/main.py"]
    }
  }
}
```

## License

MIT