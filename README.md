# Bradbury Benchmark Suite

A standardized performance and consensus-quality benchmark for the
[GenLayer](https://docs.genlayer.com/) Bradbury testnet (Chain ID `4221`,
symbol `GEN`).

The suite deploys 7 Intelligent Contracts that exercise every supported
**equivalence principle** (`strict_eq`, `prompt_comparative`,
`prompt_non_comparative`, and a hand-rolled `custom` validator via
`gl.vm.run_nondet`), runs them through the GenLayer CLI against the public
testnet, and produces:

- **`backend/data/snapshot_*.json/.csv`** — raw per-invocation records
- **`backend/reports/research_report_*.md`** — human-readable analysis
- **A live React dashboard** served from `backend/api.py` + `frontend/`

The design principle for the metrics is documented in
[`doc.md`](./doc.md): we separate **transaction acceptance**, **consensus
convergence**, and **equivalence-principle pass** as three orthogonal signals,
which is necessary to interpret `FINISHED_WITH_ERROR` results on the public
testnet correctly.

---

## Repository layout

```
.
├── backend/
│   ├── contracts/        # 7 Intelligent Contracts (GenLayer SDK)
│   ├── src/              # CLI client, executor, collector, exporter
│   ├── data/             # snapshots + deployed_manifest.json
│   ├── reports/          # generated research reports + CSVs
│   ├── api.py            # Flask API consumed by the dashboard
│   ├── main.py           # CLI: deploy / run / collect / report
│   └── requirements.txt
├── frontend/
│   ├── src/components/   # Dashboard, Heatmap, ModelMatrix, ...
│   └── package.json
├── doc.md                # Submission cover note (FINISHED_WITH_ERROR explainer)
├── .env.example          # Copy → .env, fill PRIVATE_KEY
└── README.md
```

---

## Prerequisites

1. **Node 18+** and **npm** (for the `genlayer` CLI and the dashboard).
2. **Python 3.11+**.
3. The official GenLayer CLI:
   ```bash
   npm install -g genlayer
   ```
4. A funded Bradbury testnet wallet. Get GEN from the
   [Bradbury faucet](https://testnet-faucet.genlayer.foundation).

---

## Setup

```bash
# 1. Clone & enter
git clone <this repo>
cd "Bradbury Benchmark Suite"

# 2. Configure secrets
cp .env.example .env
#   then edit .env and set PRIVATE_KEY=0x...

# 3. Python deps
python -m venv venv
venv\Scripts\activate              # Windows
# source venv/bin/activate         # macOS/Linux
pip install -r backend/requirements.txt

# 4. Frontend deps
cd frontend && npm install && cd ..
```

---

## Running the benchmark

All commands are run from the repo root.

```bash
# Deploy the 7 contracts to Bradbury (writes backend/data/deployed_manifest.json)
python backend/main.py deploy

# Run the suite (defaults to BENCHMARK_ITERATIONS from .env)
python backend/main.py run --iterations 5 --label final

# Aggregate snapshot (CSV + JSON)
python backend/main.py collect --label final

# Generate the Markdown research report + per-row CSV
python backend/main.py report --label final
```

Outputs land in `backend/data/` and `backend/reports/`.

---

## Running the dashboard

Two terminals:

```bash
# Terminal 1 — Flask API on http://localhost:8000
python backend/api.py

# Terminal 2 — Vite dev server on http://localhost:3000 (proxies /api → :8000)
cd frontend
npm run dev
```

Open <http://localhost:3000>. KPIs surfaced:

| Metric | What it measures |
|---|---|
| Tx Acceptance Rate | `status_name == ACCEPTED` (consensus protocol finalised the tx) |
| Consensus Convergence | Validators reached unanimous quorum on leader's nondet output |
| Eq. Principle Passed | Validators voted AGREE (`txExecutionResultName = SUCCESS`) |
| Avg Latency | Round-trip including consensus finalisation |

See [`doc.md`](./doc.md) for the full methodology and a discussion of why
`Eq. Principle Passed` is empirically low on the public testnet.

---

## Final published run

A reproducible reference run is committed under
`backend/data/snapshot_final_*.json/.csv` and
`backend/reports/research_report_20260509_174055.md`.

The 7 deployed contracts are recorded in
`backend/data/deployed_manifest.json` and verifiable via the
[Bradbury Explorer](https://explorer-bradbury.genlayer.com/).

---

## Security notes

- Never commit `.env`. The provided `.gitignore` excludes it.
- The keystore password (`benchmark`) used by `src/client.py` is suitable
  only for an ephemeral testnet account. Do not reuse for mainnet keys.
- The CLI imports your private key into the local `genlayer` keystore on
  first use — it never leaves your machine.

---

## License

MIT.
