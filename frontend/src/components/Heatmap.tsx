type Props = {
  data: Record<string, { convergence_rate: number; avg_latency_ms: number }>
}

export default function Heatmap({ data }: Props) {
  const principles = Object.keys(data)
  if (principles.length === 0) return <p className="muted">No data available.</p>

  const maxRate = Math.max(...Object.values(data).map(d => d.convergence_rate), 100)

  return (
    <div className="heatmap">
      <div className="heatmap-row header">
        <div className="cell">Principle</div>
        <div className="cell">Tx Acceptance</div>
        <div className="cell">Avg Latency</div>
        <div className="cell bar-cell">Distribution</div>
      </div>
      {principles.map(p => {
        const rate = data[p].convergence_rate
        const lat = data[p].avg_latency_ms
        const width = `${(rate / maxRate) * 100}%`
        const color = rate > 80 ? 'var(--accent-2)' : rate > 50 ? 'var(--accent-3)' : 'var(--accent-4)'
        return (
          <div className="heatmap-row" key={p}>
            <div className="cell principle">{p}</div>
            <div className="cell rate">{rate.toFixed(1)}%</div>
            <div className="cell latency">{lat.toFixed(0)} ms</div>
            <div className="cell bar-cell">
              <div className="bar-bg">
                <div className="bar-fill" style={{ width, background: color }} />
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
