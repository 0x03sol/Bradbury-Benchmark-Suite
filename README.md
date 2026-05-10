# Bradbury Benchmark Suite

**Live dashboard → [bradbury-benchmark-suite.vercel.app](https://bradbury-benchmark-suite.vercel.app/)**

---

Most blockchains execute code. GenLayer executes *intelligence*.

Instead of validators checking whether two hash values match, GenLayer validators each run an LLM, compare their outputs under a configurable equivalence rule, and reach consensus on what the result *means*. That's what they call Optimistic Democracy — and it's the first time a blockchain has been able to answer questions like "is this code vulnerable?" or "is this price feed reasonable?" directly on-chain, without trusting a centralized oracle.

The Bradbury testnet is where that idea runs live. Chain 4221, symbol GEN, 5 validators — all independently calling real LLMs on every transaction.

I built the Bradbury Benchmark Suite to stress-test that system. Seven Intelligent Contracts deployed to the testnet, each representing a real-world task that an LLM is good at: auditing code, resolving disputes, fetching prices, detecting prompt injection, analyzing sentiment, checking URL reliability, and recognizing patterns. Every contract runs against all four of GenLayer's equivalence principles so you can see which ones hold up under live conditions.

---

## Results — 9 May 2026

40 transactions across 7 contracts. All data is live on-chain and verifiable on the explorer.

| Metric | Result |
|---|---|
| Total invocations | 40 |
| Tx acceptance rate | **77.5%** (31 / 40) |
| Avg consensus latency | **12,933 ms** |
| Validators per tx | 5 |

By equivalence principle:

| Principle | Acceptance | Avg Latency |
|---|---|---|
| `prompt_non_comparative` | 100.0% | 13,958 ms |
| `strict_eq` | 90.0% | 13,537 ms |
| `prompt_comparative` | 85.7% | 14,129 ms |
| `custom` | 57.1% | 11,159 ms |

The full breakdown — every tx, every hash, every latency — is in the [live dashboard](https://bradbury-benchmark-suite.vercel.app/).

---

## Deployed contracts

All 7 contracts live on Bradbury Testnet (Chain 4221). Click the address to browse on the explorer.

| Contract | Address |
|---|---|
| `code_audit` | [0x8aEF4546645239508A39BCce55026D9Fb9C6C610](https://explorer-bradbury.genlayer.com/address/0x8aEF4546645239508A39BCce55026D9Fb9C6C610) |
| `dispute_resolution` | [0xCc9481Eae9Fab61600f949a304ae877C241B1E1f](https://explorer-bradbury.genlayer.com/address/0xCc9481Eae9Fab61600f949a304ae877C241B1E1f) |
| `price_oracle` | [0x6913C2a5aAe0A8d2961a5EbC9FA22792520991ea](https://explorer-bradbury.genlayer.com/address/0x6913C2a5aAe0A8d2961a5EbC9FA22792520991ea) |
| `prompt_injection` | [0x91C4aeB3948e1800E059fD8d5380A2e6Fb4603d6](https://explorer-bradbury.genlayer.com/address/0x91C4aeB3948e1800E059fD8d5380A2e6Fb4603d6) |
| `sentiment_analysis` | [0xFC26f87d12B5d1B2e76B4b8E3dcB59cee7Cadfe3](https://explorer-bradbury.genlayer.com/address/0xFC26f87d12B5d1B2e76B4b8E3dcB59cee7Cadfe3) |
| `url_fragility` | [0x497A5c7584478319eBefABd6f2420cc12498fF51](https://explorer-bradbury.genlayer.com/address/0x497A5c7584478319eBefABd6f2420cc12498fF51) |
| `vision_pattern` | [0x65F327cc88687F7721f77BDdEb653BD46E6790b2](https://explorer-bradbury.genlayer.com/address/0x65F327cc88687F7721f77BDdEb653BD46E6790b2) |

---

## Recent transactions

Last benchmark call per contract, verifiable on-chain:

| Contract | TX |
|---|---|
| `code_audit` | [0xda027a80…](https://explorer-bradbury.genlayer.com/tx/0xda027a804918d03369bb1f0c11c0dc17e9cc38e5a6e47fd522552a54115d520a) |
| `dispute_resolution` | [0x2f09fe2a…](https://explorer-bradbury.genlayer.com/tx/0x2f09fe2ab1585499c9ef35081de0bd99262a5e39014fc97bc0f17339ec45364a) |
| `price_oracle` | [0x033848…](https://explorer-bradbury.genlayer.com/tx/0x033848552f3da5a9e322ba7d92c5a92be8b8f0afd985512fb995c2c3b7ab5d0b) |
| `prompt_injection` | [0x6b8865…](https://explorer-bradbury.genlayer.com/tx/0x6b88651c4d7e3b4a4a75b2e36e72bfd6adab675e0c6e595e4186ce352065bdd1) |
| `sentiment_analysis` | [0x76eae5…](https://explorer-bradbury.genlayer.com/tx/0x76eae5690182b71e452ec4206c71526c2b8ca095bd6cb03403c3f6d527be3aa7) |
| `url_fragility` | [0x7b4fcc…](https://explorer-bradbury.genlayer.com/tx/0x7b4fccde5c3ede88e9f56a53e95b31473631ab214c46f3f768b41a5279d3f2df) |
| `vision_pattern` | [0xe280ef…](https://explorer-bradbury.genlayer.com/tx/0xe280efd9680fc65ffbebecc9ca19a1604e29f4d108cdc28307075ca8e0b2a7d9) |

---

## What the results actually show

`prompt_non_comparative` hit 100% acceptance. That makes sense — it asks the LLM a question where "yes or no" type outputs from different validators are easier to reconcile. `custom` dropped to 57% because user-defined validation logic has more room for per-validator drift when each validator is independently calling a different LLM.

All transactions show `FINISHED_WITH_ERROR` on the explorer even when marked accepted. That's not a bug — it means validators reached consensus that the LLM outputs disagreed with each other. On a public testnet with no shared seed or temperature pinning, five independent LLM calls on the same prompt will almost never produce identical output. The protocol is recording exactly what happened. See [`doc.md`](./doc.md) for the full explanation.

---

## Links

- **Live dashboard** — [bradbury-benchmark-suite.vercel.app](https://bradbury-benchmark-suite.vercel.app/)
- **Bradbury Explorer** — [explorer-bradbury.genlayer.com](https://explorer-bradbury.genlayer.com/)
- **GenLayer Docs** — [docs.genlayer.com](https://docs.genlayer.com/)
- **GenLayer Studio** — [studio.genlayer.com](https://studio.genlayer.com/)
- **Builders Portal** — [portal.genlayer.foundation](https://portal.genlayer.foundation/#/builders)
- **Testnet Faucet** — [testnet-faucet.genlayer.foundation](https://testnet-faucet.genlayer.foundation)

---

MIT
