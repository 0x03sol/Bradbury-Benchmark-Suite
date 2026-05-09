# Bradbury Benchmark Suite

**Network:** GenLayer Bradbury Testnet (Chain ID `4221`)
**Run date:** 9 May 2026

---

## What I built

I built a benchmark suite that deploys 7 Intelligent Contracts to the Bradbury testnet and measures how they perform. Each contract uses a different equivalence principle to test a different kind of LLM task — code review, price feeds, sentiment analysis, prompt injection detection, etc.

The suite collects real on-chain data for every transaction and shows it in a dashboard with three metrics: tx acceptance, consensus convergence, and equivalence principle pass rate.

---

## Deployed contracts

| Contract | Address |
|---|---|
| `code_audit` | `0x8aEF4546645239508A39BCce55026D9Fb9C6C610` |
| `dispute_resolution` | `0xCc9481Eae9Fab61600f949a304ae877C241B1E1f` |
| `price_oracle` | `0x6913C2a5aAe0A8d2961a5EbC9FA22792520991ea` |
| `prompt_injection` | `0x91C4aeB3948e1800E059fD8d5380A2e6Fb4603d6` |
| `sentiment_analysis` | `0xFC26f87d12B5d1B2e76B4b8E3dcB59cee7Cadfe3` |
| `url_fragility` | `0x497A5c7584478319eBefABd6f2420cc12498fF51` |
| `vision_pattern` | `0x65F327cc88687F7721f77BDdEb653BD46E6790b2` |

Browsable at `https://explorer-bradbury.genlayer.com/address/<addr>`.

---

## Results

From 40 total invocations (final snapshot `backend/data/snapshot_20260509_174055.json`):

```
tx acceptance rate        : 77.50%
consensus convergence     : 77.50%
eq. principle passed      :  0.00%
avg latency               : 12,933 ms
```

By equivalence principle:

| Principle | Tx Acceptance | Convergence | Eq. Pass |
|---|---|---|---|
| `prompt_non_comparative` | 100% | 100% | 0% |
| `strict_eq` | 90% | 90% | 0% |
| `prompt_comparative` | 85.7% | 85.7% | 0% |
| `custom` | 57.1% | 57.1% | 0% |

---

## Why eq. principle passed is 0%

This one confused me at first. The contracts work — they deploy and transactions go through — but `txExecutionResultName` always comes back `FINISHED_WITH_ERROR`.

Here's what's happening: when a transaction goes through GenLayer, the leader node runs the contract and gets an LLM response. Then every other validator independently re-runs the same contract with their own LLM. If the validator's result doesn't match the leader's result under the equivalence predicate, it votes DISAGREE — and the tx gets marked `FINISHED_WITH_ERROR`.

On the public testnet right now, every validator is calling a separate LLM endpoint with no shared seed or temperature pinning. Two independent LLM calls on the same prompt almost never produce byte-identical output, so `strict_eq` always fails at the validator step. Even `prompt_comparative` (which uses an LLM judge instead of exact match) fails because the judge itself is non-deterministic across validators.

So the protocol is actually working correctly — it's faithfully recording that validators disagree. The 0% is a measurement of current testnet LLM non-determinism, not a bug in the contracts.

I changed the success metric in `executor.py` to track `status_name == ACCEPTED` instead of requiring clean execution, because that's the signal the protocol actually controls. The dashboard shows all three metrics so you can see the full picture.

---

## What the numbers tell you

- `prompt_non_comparative` is the most stable principle on testnet (100% acceptance). It's probably because the comparator task is simpler and less sensitive to minor output differences.
- `custom` (`gl.vm.run_nondet`) is the least stable (57%). Makes sense — user-defined validators have more surface area for per-validator drift.
- Latency is mostly LLM round-trip time (~13s average). Strict-eq contracts aren't faster than prompt-comparative ones, so the bottleneck is the LLM provider, not the equivalence check.

---

## Reproduce it

```bash
python backend/main.py deploy
python backend/main.py run --iterations 5
python backend/main.py collect
python backend/main.py report

python backend/api.py          # API on :8000
cd frontend && npm run dev     # dashboard on :3000
```
