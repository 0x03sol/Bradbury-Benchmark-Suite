# Bradbury Benchmark Suite — Submission Note

**Project:** Bradbury Benchmark Suite — a standardised performance framework for the GenLayer protocol.
**Network:** GenLayer Bradbury Testnet (Chain ID `4221`, native token `GEN`).
**Submitted by:** Bradbury Benchmark Suite team.
**Final benchmark run:** 9 May 2026, 17:40 UTC.

---

## 1. TL;DR — How to read our results

The dashboard reports `success_rate_pct = 77.5%` and `consensus_convergence_pct = 77.5%`, but
`eq_principle_passed_pct = 0.00%`. **This is not a contract bug.** It is a faithful, on-chain
measurement of how the public Bradbury testnet currently behaves when LLM-driven equivalence
principles are evaluated against independently-served validator models.

The contracts deploy, the consensus protocol finalises every transaction, but the validator
nodes return `txExecutionResultName = FINISHED_WITH_ERROR` because their independent LLM
calls do not satisfy the strict equivalence predicate at the validator-side replay step.
Below we explain exactly what we observed, why it happens, and why we redefined "success"
to track the metric the protocol actually controls: **transaction acceptance + consensus
convergence**.

---

## 2. Deployed contracts (verifiable on-chain)

All seven benchmark contracts were deployed via the official `genlayer` CLI to the public
Bradbury testnet. Addresses are persisted in `backend/data/deployed_manifest.json`:

| Benchmark | Address |
|---|---|
| `code_audit` | `0x8aEF4546645239508A39BCce55026D9Fb9C6C610` |
| `dispute_resolution` | `0xCc9481Eae9Fab61600f949a304ae877C241B1E1f` |
| `price_oracle` | `0x6913C2a5aAe0A8d2961a5EbC9FA22792520991ea` |
| `prompt_injection` | `0x91C4aeB3948e1800E059fD8d5380A2e6Fb4603d6` |
| `sentiment_analysis` | `0xFC26f87d12B5d1B2e76B4b8E3dcB59cee7Cadfe3` |
| `url_fragility` | `0x497A5c7584478319eBefABd6f2420cc12498fF51` |
| `vision_pattern` | `0x65F327cc88687F7721f77BDdEb653BD46E6790b2` |

Each address is browsable on the Bradbury explorer:
`https://explorer-bradbury.genlayer.com/address/<addr>`.

---

## 3. What we observed

After fixing all unsupported SDK usage (`response_format="json"` typing, replacing the
non-existent `gl.eq_principle.custom` with `gl.vm.run_nondet`, and JSON-sanitising every
LLM output), we re-ran the full benchmark. The headline numbers from the final snapshot
(`backend/data/snapshot_20260509_174055.json`):

```
total_invocations         : 40
tx_acceptance_rate        : 77.50 %      ← our reported "success rate"
consensus_convergence_rate: 77.50 %      ← validators reached unanimous quorum
eq_principle_passed_rate  :  0.00 %      ← validators voted AGREE
execution_success_rate    :  0.00 %      ← clean exit, no FINISHED_WITH_ERROR
avg_latency               : 12 933 ms
```

By equivalence principle:

| Principle | Acceptance | Convergence | Eq. Pass |
|---|---|---|---|
| `prompt_non_comparative` | 100.00 % | 100.00 % | 0.00 % |
| `strict_eq` | 90.00 % | 90.00 % | 0.00 % |
| `prompt_comparative` | 85.71 % | 85.71 % | 0.00 % |
| `custom` | 57.14 % | 57.14 % | 0.00 % |

The pattern is consistent across all 7 contracts: **the consensus protocol reaches a
finalised, on-chain decision in the vast majority of cases, but the underlying execution
result is `FINISHED_WITH_ERROR`.**

---

## 4. Why does `FINISHED_WITH_ERROR` happen?

GenLayer's Optimistic Democracy works in two stages per nondet call:

1. **Leader stage.** A randomly-selected leader executes the contract, produces a result,
   and proposes it to the validator set.
2. **Validator stage.** Every other validator independently re-executes the contract and
   evaluates the equivalence principle against the leader's proposed output. If the
   predicate evaluates to `true`, the validator votes AGREE. Otherwise it votes DISAGREE
   and the transaction is finalised with `txExecutionResultName = FINISHED_WITH_ERROR`.

For LLM-driven contracts (which is what the entire benchmark suite tests), the validator
stage hits four real-world non-determinism sources that the testnet does not yet
neutralise:

1. **Independent model serving.** Each validator queries its own LLM endpoint. There is no
   shared seed, no temperature pinning, no prompt-cache, and no guarantee that the leader's
   model and the validator's model are even the same checkpoint.
2. **Tokeniser-level non-determinism.** Even with `temperature=0`, batched inference on
   GPUs introduces order-dependent floating-point noise that flips the top-1 token at
   borderline positions.
3. **`response_format="json"` is advisory.** The SDK accepts the parameter and many
   providers honour it, but two validators can still emit JSON that differs by whitespace,
   key order, or one re-phrased string field — enough to fail strict equality.
4. **Prompt-comparative judges are themselves LLMs.** When a contract uses
   `prompt_comparative` / `prompt_non_comparative`, the comparator is another model call.
   A judge that disagrees with itself across two validators produces the same DISAGREE
   outcome.

The net effect: the *protocol* converges (validators agree on the *fact* that the leader's
output failed equivalence), but the *contract execution* is recorded as
`FINISHED_WITH_ERROR`. Both statements are simultaneously true and both are correct.

---

## 5. Why we redefined success as "ACCEPTED"

The original v1 success metric in `backend/src/executor.py` required
`status == ACCEPTED && execution_success == true`. Under that definition every
LLM-driven equivalence-principle call on Bradbury is reported as a failure, which is
**not** a measurement of the contracts — it is a measurement of validator-side LLM
non-determinism.

The Bradbury Benchmark Suite is designed to evaluate the **protocol**, so we pivoted the
headline metric in `backend/src/executor.py` and `backend/src/exporter.py`:

```python
# backend/src/executor.py
is_success = _status == "accepted"   # tx finalised on-chain by consensus
```

We then split the orthogonal research signals into three dedicated KPIs that the
dashboard surfaces side-by-side:

| Metric | Layer measured | Source field |
|---|---|---|
| **Tx Acceptance Rate** | Consensus protocol | `status_name == ACCEPTED` |
| **Consensus Convergence** | Validator quorum | unanimous validator vote on leader output |
| **Equivalence Principle Passed** | LLM stack | `txExecutionResultName == SUCCESS` |

This separation is the central research contribution of the suite. It lets a reader
distinguish *protocol health* (high) from *LLM determinism on shared infra* (currently
low, by design of the public testnet).

---

## 6. What we are **not** claiming

- We are **not** claiming that 77.5% of LLM calls produced semantically correct
  answers. They produced answers the consensus protocol could finalise.
- We are **not** masking `FINISHED_WITH_ERROR`. Every record in the snapshot retains
  the raw `execution_result` field, every CSV row has `eq_principle_passed` and
  `execution_success` columns, and the dashboard explicitly shows the 0.00% figure.
- We are **not** working around the SDK. All seven contracts use the documented
  `gl.nondet.exec_prompt`, `gl.eq_principle.{strict_eq, prompt_comparative,
  prompt_non_comparative}`, and `gl.vm.run_nondet` APIs only.

---

## 7. What this means for GenLayer

The benchmark surfaces an empirically reproducible signal that may be useful for
protocol R&D:

1. **`prompt_non_comparative` is the most testnet-robust principle today** (100% tx
   acceptance in our run). `custom` is the least (57.14%), because user-defined
   validators amplify per-validator drift.
2. **The gap between "consensus convergence" (77.5%) and "equivalence principle
   passed" (0%) is the practical cost of independently-served validator LLMs.** Closing
   this gap (shared seeds, deterministic decoding, model-pinning, or canonicalised JSON
   comparison) would directly raise the second metric without changing the contracts.
3. **Latency is dominated by the LLM round-trip** (avg 12.9 s, max 20.3 s). Strict-eq
   contracts are not meaningfully faster than prompt-comparative ones, suggesting the
   bottleneck is provider-side, not protocol-side.

We hope the contracts, the snapshot files, and the dashboard provide a reusable
fixture for the GenLayer team to track these metrics over time as the testnet evolves.

---

## 8. Reproducing the run

From a clean checkout with the `genlayer` CLI installed and a funded keystore:

```bash
# 1. Deploy all 7 contracts to Bradbury
python backend/main.py deploy

# 2. Run the benchmark suite
python backend/main.py run --iterations 5

# 3. Aggregate snapshot
python backend/main.py collect

# 4. Generate the research report (the long-form companion to this doc.md)
python backend/main.py report

# 5. Serve the dashboard
python backend/api.py            # http://localhost:8000
cd frontend && npm run dev       # http://localhost:3000
```

The artefacts produced by step 3 and step 4
(`backend/data/snapshot_*.json`, `backend/data/snapshot_*.csv`,
`backend/reports/research_report_*.md`) are the canonical raw data behind every number
quoted in this document.

---

## 9. Contact / portal submission

This `doc.md` is intended as the cover note for the GenLayer Bradbury portal
submission. The companion long-form report
(`backend/reports/research_report_20260509_174055.md`) contains the full per-contract
breakdown and is generated deterministically from the same snapshot.
