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

## Production deployment

**Split-host architecture: backend → Railway, frontend → Cloudflare Pages.**

### Backend on Railway

[`nixpacks.toml`](./nixpacks.toml) builds a Python-only image and runs gunicorn (2 workers, 120s timeout). [`.railwayignore`](./.railwayignore) excludes `frontend/` so Nixpacks never auto-detects a Node provider.

Required Railway env vars:

| Name | Purpose |
|---|---|
| `PORT` | Provided by Railway automatically |
| `FRONTEND_ORIGIN` | Your Cloudflare Pages URL, e.g. `https://bradbury-benchmark.pages.dev` |
| `PRIVATE_KEY` | Only if the service runs benchmarks; not needed to serve a precomputed snapshot |

After deploy, expose the service publicly in Railway → Settings → Networking. Note the public URL (e.g. `https://bradbury-benchmark-production.up.railway.app`).

### Frontend on Cloudflare Pages

| Setting | Value |
|---|---|
| **Framework preset** | Vite |
| **Build command** | `npm ci && npm run build` |
| **Build output directory** | `dist` |
| **Root directory** | `frontend` |
| **Environment variable** | `VITE_API_URL=https://<your-railway-url>` |

[`frontend/public/_redirects`](./frontend/public/_redirects) provides the SPA fallback (`/* → /index.html 200`) so client-side routes resolve correctly on Cloudflare Pages.

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
