# Bradbury Benchmark Suite

Benchmarks 7 GenLayer Intelligent Contracts on the Bradbury testnet (Chain ID `4221`).

Each contract tests a different equivalence principle — `strict_eq`, `prompt_comparative`, `prompt_non_comparative`, and `custom` via `gl.vm.run_nondet`. The suite runs them, collects on-chain data, and shows the results in a dashboard.

See [`doc.md`](./doc.md) for why `eq_principle_passed` shows 0% and what that actually means.

---

## Layout

```
backend/
  contracts/      7 Intelligent Contracts
  src/            executor, collector, exporter, client
  data/           snapshots + deployed_manifest.json
  reports/        generated reports + CSVs
  api.py          Flask API for the dashboard
  main.py         CLI entry point

frontend/
  src/components/ Dashboard, Heatmap, etc.

doc.md            portal submission note
.env.example      copy this to .env
```

---

## Requirements

- Python 3.11+
- Node 18+
- GenLayer CLI: `npm install -g genlayer`
- A funded Bradbury wallet — get GEN from the [faucet](https://testnet-faucet.genlayer.foundation)

---

## Setup

```bash
cp .env.example .env
# edit .env and set PRIVATE_KEY=0x...

python -m venv venv
venv\Scripts\activate        # Windows
pip install -r backend/requirements.txt

cd frontend && npm install && cd ..
```

---

## Run the benchmark

```bash
python backend/main.py deploy
python backend/main.py run --iterations 5 --label final
python backend/main.py collect --label final
python backend/main.py report --label final
```

Output goes to `backend/data/` and `backend/reports/`.

---

## Dashboard

```bash
# terminal 1
python backend/api.py

# terminal 2
cd frontend && npm run dev
```

Open http://localhost:3000.

| Metric | What it is |
|---|---|
| Tx Acceptance | transaction reached `ACCEPTED` status |
| Consensus Convergence | validators agreed unanimously |
| Eq. Principle Passed | `txExecutionResultName == SUCCESS` |
| Avg Latency | full round-trip including consensus |

---

## Reference run

Snapshot and report from 9 May 2026 are committed under `backend/data/` and `backend/reports/`.
Deployed contract addresses are in `backend/data/deployed_manifest.json`, verifiable on the [Bradbury Explorer](https://explorer-bradbury.genlayer.com/).

---

## Notes

- Don't commit `.env` — it's in `.gitignore`
- The keystore password in `src/client.py` is hardcoded for testnet only, don't reuse it

---

MIT
