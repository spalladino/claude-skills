---
name: ethereum-clients
description: Source checkouts and API/behaviour maps of every production Ethereum client — execution (Geth, Nethermind, Besu, Erigon, Reth, ethrex) and consensus (Lighthouse, Prysm, Teku, Nimbus, Lodestar, Grandine) — cloned under ~/Projects/ethereum/. Use whenever you need to know how an Ethereum EL or CL client behaves or responds: JSON-RPC / Engine API / Beacon API errors and status codes, limits and defaults (gas cap, getLogs range, batch size, txpool replacement rules), block tags, pruned-data responses, blob/data-column availability, syncing/optimistic behaviour, or why two clients answer the same request differently.
---

# Ethereum clients: where the code is and how they behave

All production Ethereum clients are checked out under `~/Projects/ethereum/<dir>`. When someone asks how a client behaves, answer from its source, not from memory. Start from the reference file for that client. It gives you the files, symbols, defaults and quirks, then confirm in code.

## Clients

| Layer | Client | Dir | Lang | Repo | Branch checked out | Reference |
|---|---|---|---|---|---|---|
| EL | Geth | `geth` | Go | ethereum/go-ethereum | master | [geth](references/geth.md) |
| EL | Nethermind | `nethermind` | C# | NethermindEth/nethermind | master | [nethermind](references/nethermind.md) |
| EL | Besu | `besu` | Java | besu-eth/besu (ex hyperledger) | main | [besu](references/besu.md) |
| EL | Erigon (+ Caplin CL) | `erigon` | Go | erigontech/erigon | main | [erigon](references/erigon.md) |
| EL | Reth | `reth` | Rust | paradigmxyz/reth | main (**stale + dirty, see below**) | [reth](references/reth.md) |
| EL | ethrex | `ethrex` | Rust | lambdaclass/ethrex | main | [ethrex](references/ethrex.md) |
| CL | Lighthouse | `lighthouse` | Rust | sigp/lighthouse | stable (dev: unstable) | [lighthouse](references/lighthouse.md) |
| CL | Prysm | `prysm` | Go | OffchainLabs/prysm (ex prysmaticlabs) | develop | [prysm](references/prysm.md) |
| CL | Teku | `teku` | Java | Consensys/teku | master | [teku](references/teku.md) |
| CL | Nimbus | `nimbus` | Nim | status-im/nimbus-eth2 | stable (dev: unstable) | [nimbus](references/nimbus.md) |
| CL | Lodestar | `lodestar` | TypeScript | ChainSafe/lodestar | unstable | [lodestar](references/lodestar.md) |
| CL | Grandine | `grandine` | Rust | grandinetech/grandine | develop | [grandine](references/grandine.md) |

Rough mainnet share in late 2026: EL is Geth about 50%, Nethermind about 25%, Besu about 10%, Reth about 8%, Erigon about 7%, and ethrex is tiny. CL is Lighthouse about 43–51%, Prysm about 31%, Teku about 14%, and Nimbus, Lodestar and Grandine share the rest. Aztec's own Sepolia L1 runs reth and lighthouse.

Each reference file has the same sections:

1. Orientation and where the CLI flags and defaults live.
2. Where the RPC/REST server and routes are registered, and where each namespace's handlers live.
3. The Engine API, either server side (EL) or client side (CL).
4. Behaviour with concrete defaults: error codes, limits, block tags or state ids, pruning, the txpool or blobs.
5. Quirks.
6. Where the tests are.
7. How to find the real release tag.

## Workflow

1. **Read the reference file** for each client involved. Load only the ones you need, since each is about 30 KB.
2. **Pick the version that matters.** The checkouts track dev branches, which often already contain unreleased forks such as Gloas/Heze or Amsterdam/Bogota engine methods. A deployed node runs a release. Find the release tag with the command in the reference header, because `git describe` and newest-by-semver are wrong for several repos. Then read code at that tag without touching the working tree:
   ```bash
   cd ~/Projects/ethereum/<dir>
   git fetch --tags origin
   git show <tag>:<path>              # read a file at the release
   git grep -n '<pattern>' <tag> -- '<pathspec>'
   ```
   The clones are blobless partial clones, so the first `git show` or `git grep` on an old revision downloads blobs on demand. That is normal.
3. **Confirm in code** by opening the file or symbol the reference points to, and check the tests it names. References say "(unverified)" where the analyst didn't confirm something.
4. **Cite** `client:path:symbol`, plus the tag or commit you read, when you report behaviour.
5. If a reference turns out to be wrong or stale, fix it in this skill (`~/Projects/claude-skills/ethereum-clients/references/`).

To refresh a checkout, run `git -C ~/Projects/ethereum/<dir> pull --ff-only`, and only when the working tree is clean.

**reth is special.** `~/Projects/ethereum/reth` has the user's uncommitted changes in `crates/prune/prune/` and an old HEAD (2026-04). Never checkout, reset, stash or pull it. Run `git fetch` and read `origin/main` or a tag through `git show` and `git grep`.

**nimbus** has `vendor/` submodules that are not initialized. Presto, the REST framework, and nim-web3, the engine RPC wrappers, are absent. Read them on GitHub if needed, or ask before running `git submodule update --init`.

## Cross-client cheat sheet (EL JSON-RPC)

These are defaults on the dev branch as of 2026-11. Verify against the release you care about.

| | Geth | Nethermind | Besu | Erigon | Reth | ethrex |
|---|---|---|---|---|---|---|
| Default HTTP namespaces | eth,net,web3 (HTTP off unless `--http`) | debug/admin/personal off | eth,net,web3 | **eth,erigon,engine** (net/web3/debug/trace off) | eth,net,web3 (HTTP/WS off; IPC all) | eth,net,web3 |
| RPC gas cap | 50M | 100M | 100M | 50M | 50M | 50M |
| eth_getLogs block range | unlimited | unlimited | 5000 | 1000 | 100k | 100k |
| eth_getLogs result cap | none | 20k | none | 20k | 20k (errors) | 20k |
| toBlock beyond head | — | — | error | error (-32602) | error | — |
| Batch limit | 1000 | 1024 | 1024 | **100** | jsonrpsee default (unverified) | 1000 |
| Tx fee cap | 1 ETH | only `eth_signTransaction` | 1 ETH | 1 ETH | 1 ETH | — |
| Replacement bump | 10% (blob 100%) | 10% (blob 2x) | 10% (blob 100%) | 10% tip+cap (blob 100%) | 10% (blob 100%) | 10% (blob 100%) |
| estimateGas | binary search, 1.5% tolerance | 150 bps margin | 1.5% tolerance | — | 1.5% tolerance | — |
| Revert error | code 3 + data | code 3 + data | code 3, `Execution reverted (reason)` | code 3 + data | code 3 + data | code 3 + data |
| Pruned history | 4444 | 4444 | — | — | 4444 | 4444 (state >128 blocks) |
| `pending` tag | local synthetic block from txpool (2s cache); pending logs rejected | = head | = latest | eth_call rejects it | — | = latest |

A dash means the reference doesn't state it, so check the reference or the code. Other things that are easy to get wrong:

- **Geth:** `earliest` resolves to the history-pruning cutoff, not genesis.
- **Geth:** the local tx tracker makes `eth_sendRawTransaction` succeed on temporary rejects such as underpriced, and the tx may never land.
- **Geth:** state history keeps 90k blocks.
- **Nethermind:** RPC-submitted txs skip the underpriced and nonce-gap pool filters.
- **Erigon:** `eth_sendRawTransaction` errors look like `INTERNAL_ERROR: nonce too low`.
- **Erigon:** `safe` and `finalized` return -39001 before the CL sets them.
- **Reth:** `safe` and `finalized` return -32001 before the CL sets them.
- **Besu:** an RLP decode failure on send returns -32602 "Invalid block param".
- **Besu:** nonce too low is -32001.
- **ethrex:** error strings are its own wording.
- **ethrex:** WS supports only `newHeads` and `newPendingTransactions`.
- **ethrex:** `txpool` queued is always empty.
- **Engine API:** every EL serves it on 8551 with an HS256 JWT and an `iat` window of about 60s. Erigon and Nethermind also expose an SSZ-REST engine transport.

## Cross-client cheat sheet (CL Beacon API)

| | Lighthouse | Prysm | Teku | Nimbus | Lodestar | Grandine |
|---|---|---|---|---|---|---|
| Default REST | 127.0.0.1:5052, off unless `--http` | 3500 | 127.0.0.1:5051 (keymanager 5052, TLS on) | 127.0.0.1:5052, **off unless `--rest`** | 127.0.0.1:9596 | 5052 |
| Error body | `{code,message,stacktraces}` | `{code,message}` (415/406 plain text) | `{code,message}`; `ChainDataUnavailable` gives **204** | `{code,message,stacktraces}` | `{code,message,…}` (plain `Error` gives 500) | `{code,message,failures?}` |
| 503 while syncing | validator endpoints only, head >2 epochs behind | validator and publish endpoints only | `NodeSyncingException` (block publish and duties; also when head/parent optimistic) | validator endpoints and optimistic block production | `notWhileSyncing`: head >1 epoch behind, except head/finalized/justified/genesis state ids | validator route groups only |
| `/node/health` while syncing | 206 (503 only if EL offline) | 206 | — | 206, never 503 | — | — |
| Old states | 404 below finalized unless `--archive` | replay, or state-diff with `--enable-archive` | `--data-storage-mode` MINIMAL for a fresh DB (PRUNE for an older one); need ARCHIVE | `--history=prune` by default | **500** unless `--serveHistoricalState` | rebuilt from snapshots every 32 epochs, plus replay |
| Post-Fulu `/blobs` | rebuilt from columns, needs ≥50% of them, else 400 | 404 if <64 columns | `200 []` unless supernode or `--rest-api-getblobs-sidecars-download-enabled` | `/blob_sidecars` returns **410**; `/blobs` rebuilt | 503 if <64 columns | `200 []` if <64 columns |
| Engine timeouts (newPayload/FCU/getPayload) | 8s/8s/2s | 8s/8s/1s | 8s/8s/2s | 8s/8s/1s | — | 8s/8s/1s |

Behaviours shared across CLs:

- **Blob serving.** After Fulu, serving blobs needs a supernode or semi-supernode, which custodies at least 64 of 128 columns. A default-custody node can't serve `/blobs`, and each client fails differently: Lighthouse 400, Prysm 404, Lodestar 503, and Teku and Grandine 200 with an empty list.
- **Engine responses.** On SYNCING or ACCEPTED from `newPayload`, every CL imports the block optimistically. On INVALID it invalidates the block and its descendants. No CL retries a failed engine call; at most they fall back to another EL.
- **Block publish.** Lighthouse and Grandine return 202 for a block that was broadcast but failed import, under the default `broadcast_validation=gossip`. Prysm never returns 202; Teku returns 500 for rejected blocks. Nimbus supports only `gossip`, and other values give 500.
- **State by root.** Prysm and Nimbus find a state root only if it is within the last 8192 `state_roots` of the head state.
- **Removed endpoints.** Prysm and Nimbus return 410 Gone, often with a hint to the replacement.
- **Builder defaults.** Lighthouse's validator client is local-only unless `--builder-proposals`. Lodestar's is `executiononly` unless `--builder`. Prysm applies a 10% local boost. Teku's `--builder-bid-compare-factor` is 90. Nimbus uses `--builder-boost-factor` 100.
- **Erigon's Caplin** embedded CL is on by default for mainnet, sepolia, hoodi and gnosis. Opt out with `--externalcl`. Its Beacon API is off unless `--beacon.api`, which listens on port 5555.

## Related

- `l1-rpc-cast`: query a live L1 node with `cast`, for when you'd rather observe the behaviour than read the code. Aztec's Sepolia reth and lighthouse endpoints are there.
