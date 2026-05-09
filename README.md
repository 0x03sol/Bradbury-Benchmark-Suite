# Bradbury Benchmark Suite

A standardized performance framework for **GenLayer Intelligent Contracts** on the Bradbury Testnet (Chain ID `4221`, symbol `GEN`).

The suite deploys 7 Intelligent Contracts that exercise all four equivalence principles — `strict_eq`, `prompt_comparative`, `prompt_non_comparative`, and `custom` (via `gl.vm.run_nondet`) — runs them on-chain, collects validator-level consensus data, and visualizes the results in a live React dashboard.

> **Why this matters.** GenLayer's *Optimistic Democracy* consensus produces three orthogonal outcomes per transaction: protocol acceptance, validator consensus convergence, and equivalence-principle pass. This suite measures all three across realistic workloads so builders can reason about which principles are robust under live testnet conditions. See [`doc.md`](./doc.md) for a discussion of the empirical `eq_principle_passed = 0%` finding.

---

## Features

- **7 Intelligent Contracts** covering code audit, dispute resolution, price oracle, prompt injection, sentiment analysis, URL fragility, and vision pattern recognition
- **All 4 equivalence principles** exercised across the contracts
- **Real on-chain execution** via the official `genlayer` CLI — no mocks
- **Validator-level metrics** parsed from CLI output (per-validator AGREE/DISAGREE votes)
- **Live dashboard** — React + Vite frontend backed by a Flask + gunicorn API
- **Reproducible snapshots** under `backend/data/` for portal verification
- **Unit-tested parsers** (`pytest` — 17 tests covering the CLI output heuristics)
- **One-click deploy** to Railway via [`railway.toml`](./railway.toml) / [`Procfile`](./Procfile)

---

## Layout

```
backend/
  contracts/      7 Intelligent Contracts (.py)
  src/            client, executor, collector, exporter, research
  data/           snapshots + deployed_manifest.json
  reports/        generated research reports + CSVs
  tests/          pytest suite for parsers and helpers
  api.py          Flask API serving the dashboard
  main.py         CLI: deploy / run / collect / report

frontend/
  src/            React dashboard (Vite + TypeScript)
  index.html      Vite entry

doc.md            portal submission notes
.env.example      copy to .env and fill in PRIVATE_KEY
railway.toml      Railway deploy config (gunicorn)
Procfile          Heroku-style deploy (gunicorn)
```

---

## Requirements

- Python 3.11+
- Node 18+
- GenLayer CLI: `npm install -g genlayer`
- A funded Bradbury testnet wallet — get GEN from the [faucet](https://testnet-faucet.genlayer.foundation)

---

## Setup

```bash
cp .env.example .env
# edit .env and set PRIVATE_KEY=0x...

python -m venv venv
# Windows:
venv\Scripts\activate
# macOS / Linux:
source venv/bin/activate

pip install -r backend/requirements.txt
cd frontend && npm install && cd ..
```

---

## Run the benchmark

```bash
python backend/main.py deploy                                 # deploys 7 contracts
python backend/main.py run --iterations 5 --label final       # executes the suite
python backend/main.py collect --label final                  # enriches with on-chain data
python backend/main.py report --label final                   # generates research report + CSV
```

Output is written to `backend/data/` (snapshots) and `backend/reports/` (research reports + CSVs).

---

## Dashboard (local development)

```bash
# terminal 1 — API
python backend/api.py

# terminal 2 — frontend
cd frontend && npm run dev
```

Open <http://localhost:3000>. Vite proxies `/api/*` → `http://localhost:8000`.

| Metric | Meaning |
|---|---|
| **Tx Acceptance Rate** | Transactions that reached `ACCEPTED` (or `FINALIZED` without execution error) |
| **Consensus Convergence** | Validators returned a unanimous result (`resultName = AGREE`) |
| **Eq. Principle Passed** | All validators voted AGREE on the equivalence check |
| **Avg Latency** | Submission → consensus, full round-trip in milliseconds |

---

## Production deployment (Railway / Heroku)

[`nixpacks.toml`](./nixpacks.toml) defines a **single-service deploy** that:

1. Installs Python deps from `backend/requirements.txt`
2. Runs `npm ci && npm run build` in `frontend/` to produce `frontend/dist/`
3. Starts **gunicorn** (2 workers, 120s timeout)

Flask serves the built React dashboard at `/` and the JSON API at `/api/*`, so the Railway URL shows the live dashboard with no separate frontend host needed.

Required env vars:

| Name | Purpose |
|---|---|
| `PORT` | Provided by the platform; falls back to `API_PORT` (default `8000`) locally |
| `FRONTEND_ORIGIN` | Comma-separated CORS allowlist; only needed if you split frontend onto a different host |
| `PRIVATE_KEY` | Only needed if the deployed instance runs benchmarks; not required to serve a precomputed snapshot |

If you prefer a split deploy (API on Railway, static frontend on Vercel/Netlify), build the frontend with `VITE_API_URL=https://api.example.com npm run build`.

---

## Tests

```bash
cd backend && python -m pytest
```

Covers the regex/substring CLI parsers in `src.client` (the most fragile code in the suite) and the research helpers in `src.research`.

---

## Reference run

A reference snapshot and report from 9 May 2026 are committed under `backend/data/` and `backend/reports/`. Deployed contract addresses live in `backend/data/deployed_manifest.json` and are independently verifiable on the [Bradbury Explorer](https://explorer-bradbury.genlayer.com/).

---

## Security notes

- **Never commit `.env`** — it's already in `.gitignore`
- The keystore password in `src/client.py` is hardcoded for testnet-only use; do not reuse it on mainnet
- API CORS defaults to localhost; set `FRONTEND_ORIGIN` to your deployed frontend before exposing the API publicly

---

## Resources

- [GenLayer Docs](https://docs.genlayer.com/)
- [Bradbury Explorer](https://explorer-bradbury.genlayer.com/)
- [Faucet](https://testnet-faucet.genlayer.foundation)
- [GenLayer Builders Portal](https://portal.genlayer.foundation/#/builders)

---

MIT
