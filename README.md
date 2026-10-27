# mcp-onchain-proof

MCP server for On-Chain Proof-of-Service Audit - generate attestations, audit trail, verification, price locks.

## Tools

### generate_attestation
Generate on-chain attestation for agent service.

**Parameters:**
- `agent_id` (string, required): Agent identifier
- `service_type` (string, required): "trading", "monitoring", "analytics", or "execution"
- `period_start` (string, required): Period start (ISO format)
- `period_end` (string, required): Period end (ISO format)
- `metrics` (object, required): Service metrics
- `chain` (string, optional): "ethereum", "polygon", "arbitrum", "optimism", "base" (default: "ethereum")

### get_audit_trail
Get audit trail for attestations.

**Parameters:**
- `attestation_id` (string, optional): Attestation ID
- `agent_id` (string, optional): Agent ID
- `limit` (integer, optional): Max entries (default: 50)

### verify_attestation
Verify an on-chain attestation.

**Parameters:**
- `attestation_id` (string, required): Attestation ID
- `tx_hash` (string, optional): Transaction hash

### get_price_lock
Get price lock terms for service type.

**Parameters:**
- `service_type` (string, required): Service type

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

## Connecting to Claude Desktop

```json
{
  "mcpServers": {
    "onchain-proof": {
      "command": "python",
      "args": ["/path/to/mcp-onchain-proof/main.py"],
      "cwd": "/path/to/mcp-onchain-proof"
    }
  }
}
```

## License

MIT