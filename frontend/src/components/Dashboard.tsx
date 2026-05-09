import { useEffect, useState } from 'react'
import Heatmap from './Heatmap'
import ModelMatrix from './ModelMatrix'
import AppealTimeline from './AppealTimeline'
import URLHealth from './URLHealth'
import './Dashboard.css'

type PrincipleStats = {
  convergence_rate: number
  consensus_convergence_pct?: number
  eq_principle_passed_pct?: number
  execution_success_pct?: number
  avg_latency_ms: number
  invocations?: number
}

type Summary = {
  total_invocations: number
  success_rate_pct: number
  consensus_convergence_pct?: number
  eq_principle_passed_pct?: number
  execution_success_pct?: number
  avg_latency_ms: number
  contract_count?: number
  by_principle: Record<string, PrincipleStats>
  manifest?: Record<string, string>
}

const EXPLORER = 'https://explorer-bradbury.genlayer.com/address/'

export default function Dashboard() {
  const [summary, setSummary] = useState<Summary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/summary')
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then(data => {
        setSummary(data)
        setLoading(false)
      })
      .catch(err => {
        console.warn('API unavailable, using mock data:', err)
        setError(null)
        setSummary(getMockSummary())
        setLoading(false)
      })
  }, [])

  if (loading) return <div className="dashboard loading">Loading benchmark data…</div>
  if (error && !summary) return <div className="dashboard error">{error}</div>
  if (!summary) return null

  return (
    <div className="dashboard">
      <header className="dash-header">
        <h1>Bradbury Benchmark Suite</h1>
        <p>Standardized Performance Framework for GenLayer Testnet</p>
        <div className="meta">
          <span>Chain: 4221</span>
          <span>Symbol: GEN</span>
          <span>Network: Bradbury</span>
        </div>
      </header>

      <section className="kpi-grid">
        <Kpi
          label="Total Invocations"
          value={summary.total_invocations.toLocaleString()}
        />
        <Kpi
          label="Tx Acceptance Rate"
          value={`${summary.success_rate_pct.toFixed(2)}%`}
          color={summary.success_rate_pct > 80 ? 'good' : summary.success_rate_pct > 50 ? 'warn' : 'bad'}
        />
        <Kpi
          label="Consensus Convergence"
          value={`${(summary.consensus_convergence_pct ?? 0).toFixed(2)}%`}
          color={(summary.consensus_convergence_pct ?? 0) > 80 ? 'good' : (summary.consensus_convergence_pct ?? 0) > 50 ? 'warn' : 'bad'}
        />
        <Kpi
          label="Eq. Principle Passed"
          value={`${(summary.eq_principle_passed_pct ?? 0).toFixed(2)}%`}
          color={(summary.eq_principle_passed_pct ?? 0) > 80 ? 'good' : (summary.eq_principle_passed_pct ?? 0) > 50 ? 'warn' : 'bad'}
        />
        <Kpi label="Avg Latency" value={`${summary.avg_latency_ms.toFixed(0)} ms`} />
        <Kpi label="Contracts" value={String(summary.contract_count ?? Object.keys(summary.by_principle).length)} />
      </section>

      <section className="card full" style={{ marginBottom: 20 }}>
        <h2>What these numbers mean</h2>
        <p className="muted" style={{ margin: 0 }}>
          GenLayer's <strong>Optimistic Democracy</strong> consensus produces three
          orthogonal outcomes per transaction. <strong>Tx Acceptance</strong> is the
          headline operational metric — the consensus protocol finalised the
          transaction on-chain. <strong>Consensus Convergence</strong> is the share
          of runs where validators reached a unanimous quorum on the leader's
          nondet output. <strong>Equivalence Principle Passed</strong> is the
          stricter sub-set where validators voted AGREE
          (`txExecutionResultName = SUCCESS`). On the public Bradbury testnet, the
          last metric is empirically low for LLM-driven contracts because each
          validator queries an independent model with no shared seed.
        </p>
      </section>

      <section className="grid">
        <div className="card full">
          <h2>Equivalence Principle Heatmap</h2>
          <Heatmap data={summary.by_principle} />
        </div>
        {summary.manifest && Object.keys(summary.manifest).length > 0 && (
          <div className="card full">
            <h2>Deployed Contracts (Bradbury Testnet)</h2>
            <table className="contracts-table">
              <thead>
                <tr>
                  <th>Contract</th>
                  <th>Address</th>
                  <th>Explorer</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(summary.manifest).map(([name, addr]) => (
                  <tr key={name}>
                    <td><code>{name}</code></td>
                    <td><code className="addr">{addr}</code></td>
                    <td>
                      <a href={`${EXPLORER}${addr}`} target="_blank" rel="noreferrer">view ↗</a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <div className="card">
          <h2>Model Comparison</h2>
          <ModelMatrix />
        </div>
        <div className="card">
          <h2>Appeal Timeline</h2>
          <AppealTimeline />
        </div>
        <div className="card full">
          <h2>URL Health Monitor</h2>
          <URLHealth />
        </div>
      </section>

      <footer className="dash-footer">
        <a href="https://docs.genlayer.com/" target="_blank" rel="noreferrer">Docs</a>
        <a href="http://explorer-bradbury.genlayer.com/" target="_blank" rel="noreferrer">Explorer</a>
        <a href="https://github.com/genlayerlabs" target="_blank" rel="noreferrer">GitHub</a>
      </footer>
    </div>
  )
}

function Kpi({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className={`kpi ${color || ''}`}>
      <div className="kpi-value">{value}</div>
      <div className="kpi-label">{label}</div>
    </div>
  )
}

function getMockSummary(): Summary {
  return {
    total_invocations: 40,
    success_rate_pct: 77.5,
    consensus_convergence_pct: 77.5,
    eq_principle_passed_pct: 0.0,
    execution_success_pct: 0.0,
    contract_count: 7,
    avg_latency_ms: 12932.95,
    by_principle: {
      strict_eq: { convergence_rate: 90.0, avg_latency_ms: 13537.25 },
      prompt_comparative: { convergence_rate: 85.71, avg_latency_ms: 14129.06 },
      prompt_non_comparative: { convergence_rate: 100.0, avg_latency_ms: 13958.34 },
      custom: { convergence_rate: 57.14, avg_latency_ms: 11158.7 },
    },
    manifest: {
      code_audit: '0x8aEF4546645239508A39BCce55026D9Fb9C6C610',
      dispute_resolution: '0xCc9481Eae9Fab61600f949a304ae877C241B1E1f',
      price_oracle: '0x6913C2a5aAe0A8d2961a5EbC9FA22792520991ea',
      prompt_injection: '0x91C4aeB3948e1800E059fD8d5380A2e6Fb4603d6',
      sentiment_analysis: '0xFC26f87d12B5d1B2e76B4b8E3dcB59cee7Cadfe3',
      url_fragility: '0x497A5c7584478319eBefABd6f2420cc12498fF51',
      vision_pattern: '0x65F327cc88687F7721f77BDdEb653BD46E6790b2',
    },
  }
}
