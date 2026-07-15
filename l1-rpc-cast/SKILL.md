---
name: l1-rpc-cast
description: Query an Ethereum L1 RPC endpoint with Foundry's `cast` — block numbers, blocks, chain id, eth_call, storage slots, logs, balances, tx/receipt lookups, and raw JSON-RPC. Use whenever you need to read L1 (mainnet or Sepolia) state for Aztec work, e.g. inspecting the rollup/registry contracts, checking L1 block timestamps, or debugging L1 tx submission. Covers where to get endpoints and common cast recipes.
argument-hint: [what to query, e.g. "sepolia block number" or "call rollup getPendingBlockNumber"]
---

# Query L1 (Ethereum) over RPC with `cast`

`cast` is Foundry's CLI for talking to an Ethereum node. Use it to read L1 state — the fastest
way to inspect the rollup/registry contracts, L1 block timestamps, balances, and raw
JSON-RPC — without writing a script.

## First: pick an endpoint and health-check it

L1 RPC URLs embed API keys, so they are **not** stored in this skill. They live in
`~/.claude/secrets/l1-rpc.env` (chmod 600). Source it:

```bash
. ~/.claude/secrets/l1-rpc.env
```

This exports, among others:

| Variable | Network | Provider |
|---|---|---|
| `L1_MAINNET_INFURA`, `L1_MAINNET_ALCHEMY`, `L1_MAINNET_QUICKNODE` | mainnet | Infura / Alchemy / QuickNode |
| `L1_SEPOLIA_INFURA`, `L1_SEPOLIA_QUICKNODE` | Sepolia | Infura / QuickNode |
| `ETH_RPC_URL_MAINNET`, `ETH_RPC_URL_SEPOLIA` | defaults per network | — |

Health-check (chain id confirms the endpoint and which network it is — `1` = mainnet,
`11155111` = Sepolia):

```bash
cast chain-id --rpc-url "$ETH_RPC_URL_SEPOLIA"     # -> 11155111
cast block-number --rpc-url "$ETH_RPC_URL_MAINNET" # -> 23...
```

### Setting a default endpoint

`cast` reads `ETH_RPC_URL` when `--rpc-url` is omitted. Export it once to avoid repeating the
flag:

```bash
export ETH_RPC_URL="$ETH_RPC_URL_SEPOLIA"
cast block-number
```

### Other endpoint sources

- **Team/deployment L1 URLs** used by the networks live in GCP Secret Manager (project
  `testnet-440309`): `gcloud secrets versions access latest --secret=mainnet-rpc-urls` and
  `--secret=sepolia-rpc-urls`. Aztec testnet runs on **Sepolia**; mainnet runs on **mainnet**.
- If a provider rate-limits (HTTP 429), switch to another variable from the env file
  (Infura → Alchemy → QuickNode) rather than hammering one.

## Common recipes

```bash
. ~/.claude/secrets/l1-rpc.env
RPC="$ETH_RPC_URL_SEPOLIA"   # or $ETH_RPC_URL_MAINNET

# --- chain / blocks ---
cast block-number --rpc-url "$RPC"
cast block latest --rpc-url "$RPC"                       # full latest block
cast block latest -f timestamp --rpc-url "$RPC"          # one field (timestamp)
cast block 9000000 -f timestamp --rpc-url "$RPC"         # timestamp of a specific block
cast age 9000000 --rpc-url "$RPC"                        # human-readable block time
cast gas-price --rpc-url "$RPC"
cast base-fee --rpc-url "$RPC"

# --- accounts ---
cast balance 0xADDR --rpc-url "$RPC"                     # wei
cast balance 0xADDR --ether --rpc-url "$RPC"
cast nonce 0xADDR --rpc-url "$RPC"
cast code 0xADDR --rpc-url "$RPC"                        # deployed bytecode (0x = EOA/empty)

# --- reading a contract (eth_call) ---
cast call 0xCONTRACT "getPendingBlockNumber()(uint256)" --rpc-url "$RPC"
cast call 0xCONTRACT "balanceOf(address)(uint256)" 0xADDR --rpc-url "$RPC"
cast call 0xCONTRACT "owner()(address)" --block 9000000 --rpc-url "$RPC"   # historical state
cast storage 0xCONTRACT 0 --rpc-url "$RPC"               # raw storage slot 0

# --- transactions ---
cast tx 0xTXHASH --rpc-url "$RPC"
cast receipt 0xTXHASH --rpc-url "$RPC"
cast receipt 0xTXHASH status --rpc-url "$RPC"            # 1 = success, 0 = revert
cast run 0xTXHASH --rpc-url "$RPC"                       # trace/replay a tx

# --- logs ---
cast logs --from-block 9000000 --to-block latest \
  --address 0xCONTRACT "Transfer(address,address,uint256)" --rpc-url "$RPC"

# --- raw JSON-RPC (anything cast has no subcommand for) ---
cast rpc eth_getBlockByNumber latest false --rpc-url "$RPC"
cast rpc eth_syncing --rpc-url "$RPC"
```

## Tips

- ABI-decode return types inline: append the signature return, e.g.
  `"totalSupply()(uint256)"`. Without it, `cast call` prints raw hex.
- `cast --to-dec`, `cast --to-hex`, `cast --to-unit <wei> ether`, `cast keccak "<str>"`,
  `cast 4byte <selector>` are handy for munging values offline (no RPC needed).
- For Aztec L1 contract addresses, ask an Aztec node: `aztec_getL1ContractAddresses`
  (see the `aztec-node-rpc` skill), then `cast call` those addresses here.
