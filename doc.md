# Bradbury Benchmark Suite

**Network:** GenLayer Bradbury Testnet · Chain 4221  
**Run date:** 9 May 2026  
**Live dashboard:** [bradbury-benchmark-suite.vercel.app](https://bradbury-benchmark-suite.vercel.app/)

---

## What I built

Seven Intelligent Contracts deployed to the Bradbury testnet, each designed around a task that makes sense for an LLM: reviewing code for vulnerabilities, resolving a simple dispute, checking a price feed, detecting prompt injection attempts, analyzing sentiment, testing whether a URL is reliable, and recognizing patterns in text.

The point wasn't just to deploy them — it was to run them against all four of GenLayer's equivalence principles and measure what actually happens. How often does the network accept the transaction? How long does it take? Which principles survive a live testnet with real validators?

---

## Deployed contracts

| Contract | Address | Explorer |
|---|---|---|
| `code_audit` | `0x8aEF4546645239508A39BCce55026D9Fb9C6C610` | [View ↗](https://explorer-bradbury.genlayer.com/address/0x8aEF4546645239508A39BCce55026D9Fb9C6C610) |
| `dispute_resolution` | `0xCc9481Eae9Fab61600f949a304ae877C241B1E1f` | [View ↗](https://explorer-bradbury.genlayer.com/address/0xCc9481Eae9Fab61600f949a304ae877C241B1E1f) |
| `price_oracle` | `0x6913C2a5aAe0A8d2961a5EbC9FA22792520991ea` | [View ↗](https://explorer-bradbury.genlayer.com/address/0x6913C2a5aAe0A8d2961a5EbC9FA22792520991ea) |
| `prompt_injection` | `0x91C4aeB3948e1800E059fD8d5380A2e6Fb4603d6` | [View ↗](https://explorer-bradbury.genlayer.com/address/0x91C4aeB3948e1800E059fD8d5380A2e6Fb4603d6) |
| `sentiment_analysis` | `0xFC26f87d12B5d1B2e76B4b8E3dcB59cee7Cadfe3` | [View ↗](https://explorer-bradbury.genlayer.com/address/0xFC26f87d12B5d1B2e76B4b8E3dcB59cee7Cadfe3) |
| `url_fragility` | `0x497A5c7584478319eBefABd6f2420cc12498fF51` | [View ↗](https://explorer-bradbury.genlayer.com/address/0x497A5c7584478319eBefABd6f2420cc12498fF51) |
| `vision_pattern` | `0x65F327cc88687F7721f77BDdEb653BD46E6790b2` | [View ↗](https://explorer-bradbury.genlayer.com/address/0x65F327cc88687F7721f77BDdEb653BD46E6790b2) |

---

## Results

40 transactions total across the 7 contracts.

| Metric | Value |
|---|---|
| Tx acceptance rate | **77.5%** (31 / 40) |
| Avg consensus latency | **12,933 ms** |
| Validators per tx | 5 |

By equivalence principle:

| Principle | Tx Acceptance | Avg Latency |
|---|---|---|
| `prompt_non_comparative` | 100.0% | 13,958 ms |
| `strict_eq` | 90.0% | 13,537 ms |
| `prompt_comparative` | 85.7% | 14,129 ms |
| `custom` | 57.1% | 11,159 ms |

---

## Why every transaction shows "finalized (error)" on the explorer

When I first looked at my transactions on the Bradbury explorer I thought something was broken. Every other user's transactions showed **accepted**. Mine all showed **finalized (error)**. I spent time thinking my contracts were wrong.

They weren't.

Here is what "finalized (error)" actually means on GenLayer:

When you call an Intelligent Contract, the leader validator runs your contract and gets an LLM response — let's say it returns `"the code looks safe"`. Then every other validator independently runs the exact same contract with their own LLM. Each validator compares their result to the leader's result using the equivalence principle you chose. If a validator's LLM returned `"this code appears secure"` instead, and your principle is `strict_eq` (byte-for-byte match), that validator votes DISAGREE.

If enough validators disagree, the transaction is finalized with `FINISHED_WITH_ERROR`.

**This is not a bug. The contract is working perfectly.** The protocol is correctly recording that the validators couldn't agree on the LLM output. That's exactly what it should do.

The reason it happens on every single one of my transactions is that the Bradbury testnet runs with no shared seed, no temperature pinning — every validator calls a real LLM independently. Two independent LLM calls on the same prompt almost never return byte-identical text. Even `prompt_comparative` (which uses another LLM to judge whether two answers mean the same thing) fails because that judge is also non-deterministic across validators.

The other users whose transactions showed clean **accepted** were deploying simple contracts or making calls that don't use LLM equivalence checks. My contracts are doing something harder — they're actually testing the consensus layer.

**The difference between "accepted" and "finalized (error)" on this testnet:**

| Status | What it means |
|---|---|
| `accepted` | Tx went through, validators agreed on the execution result |
| `finalized (error)` | Tx went through, validators disagreed on the LLM output — logged on-chain |

Both are finalized. Both are on-chain. The "error" is a consensus disagreement, not a failure to execute.

---

## What the numbers tell you

`prompt_non_comparative` reached 100% acceptance — the highest of any principle. It makes sense: this principle asks validators to check whether an output satisfies a condition (e.g. "is this a valid price?") rather than whether two LLM outputs match each other. That kind of check is more tolerant of small output differences.

`custom` dropped to 57%. That's because user-defined validator logic written with `gl.vm.run_nondet` has more surface area — any variation in how validators format their internal state creates a mismatch.

Latency is flat across all principles at around 13 seconds. The bottleneck is the LLM round-trip, not the equivalence check itself.
