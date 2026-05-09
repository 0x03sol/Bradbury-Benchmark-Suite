import { useEffect, useState } from 'react'

type TimelineEntry = {
  hour: string
  txs: number
  appeals: number
}

const fallbackTimeline: TimelineEntry[] = [
  { hour: '00:00', appeals: 2, txs: 120 },
  { hour: '01:00', appeals: 1, txs: 98 },
  { hour: '02:00', appeals: 0, txs: 85 },
  { hour: '03:00', appeals: 3, txs: 110 },
  { hour: '04:00', appeals: 1, txs: 130 },
  { hour: '05:00', appeals: 4, txs: 145 },
  { hour: '06:00', appeals: 2, txs: 160 },
  { hour: '07:00', appeals: 5, txs: 190 },
  { hour: '08:00', appeals: 3, txs: 210 },
  { hour: '09:00', appeals: 6, txs: 230 },
  { hour: '10:00', appeals: 4, txs: 250 },
  { hour: '11:00', appeals: 2, txs: 240 },
]

export default function AppealTimeline() {
  const [timeline, setTimeline] = useState<TimelineEntry[]>(fallbackTimeline)

  useEffect(() => {
    fetch('/api/appeals')
      .then(r => r.ok ? r.json() : Promise.reject(r.status))
      .then(data => { if (Array.isArray(data) && data.length > 0) setTimeline(data) })
      .catch(() => {})
  }, [])

  const maxTxs = Math.max(...timeline.map(t => t.txs))

  return (
    <div className="timeline">
      {timeline.map(t => {
        const h = (t.txs / maxTxs) * 120
        return (
          <div className="timeline-slot" key={t.hour} title={`${t.hour}: ${t.txs} txs, ${t.appeals} appeals`}>
            <div className="bar-stack">
              <div className="tx-bar" style={{ height: `${h}px` }} />
              <div className="appeal-dot" style={{ bottom: `${h + 4}px` }} />
            </div>
            <div className="time-label">{t.hour}</div>
          </div>
        )
      })}
    </div>
  )
}
