import { useEffect, useState } from 'react'
import { apiUrl } from '../api'

type Model = {
  name: string
  accuracy: number
  latency: number
}

const fallbackModels: Model[] = [
  { name: 'openai/gpt-4', accuracy: 94.2, latency: 2450 },
  { name: 'anthropic/claude-3-opus', accuracy: 91.7, latency: 3120 },
  { name: 'meta/llama-3-70b', accuracy: 83.5, latency: 1890 },
]

export default function ModelMatrix() {
  const [models, setModels] = useState<Model[]>(fallbackModels)

  useEffect(() => {
    fetch(apiUrl('/api/models'))
      .then(r => r.ok ? r.json() : Promise.reject(r.status))
      .then(data => { if (Array.isArray(data) && data.length > 0) setModels(data) })
      .catch(() => {})
  }, [])

  return (
    <div className="model-matrix">
      <div className="matrix-row header">
        <div className="mcell">Model</div>
        <div className="mcell">Accuracy</div>
        <div className="mcell">Latency</div>
      </div>
      {models.map(m => (
        <div className="matrix-row" key={m.name}>
          <div className="mcell model-name">{m.name}</div>
          <div className="mcell accuracy">{m.accuracy}%</div>
          <div className="mcell latency">{m.latency} ms</div>
        </div>
      ))}
    </div>
  )
}
