import { useEffect, useState } from 'react'

type UrlEntry = {
  contract_address: string
  total: number
  success_rate: number
  cloudflare_blocks: number
  paywall_count: number
  not_found: number
}

const fallbackUrls: UrlEntry[] = [
  { contract_address: 'api.coingecko.com', total: 100, success_rate: 98, cloudflare_blocks: 0, paywall_count: 0, not_found: 2 },
  { contract_address: 'docs.genlayer.com', total: 100, success_rate: 100, cloudflare_blocks: 0, paywall_count: 0, not_found: 0 },
  { contract_address: 'github.com', total: 100, success_rate: 99, cloudflare_blocks: 0, paywall_count: 0, not_found: 1 },
  { contract_address: 'etherscan.io', total: 100, success_rate: 87, cloudflare_blocks: 10, paywall_count: 0, not_found: 3 },
  { contract_address: 'medium.com', total: 100, success_rate: 76, cloudflare_blocks: 20, paywall_count: 0, not_found: 4 },
  { contract_address: 'twitter.com', total: 100, success_rate: 45, cloudflare_blocks: 50, paywall_count: 0, not_found: 5 },
  { contract_address: 'reddit.com', total: 100, success_rate: 92, cloudflare_blocks: 5, paywall_count: 0, not_found: 3 },
  { contract_address: 'news.ycombinator.com', total: 100, success_rate: 100, cloudflare_blocks: 0, paywall_count: 0, not_found: 0 },
]

export default function URLHealth() {
  const [urls, setUrls] = useState<UrlEntry[]>(fallbackUrls)

  useEffect(() => {
    fetch('/api/url-health')
      .then(r => r.ok ? r.json() : Promise.reject(r.status))
      .then(data => { if (Array.isArray(data) && data.length > 0) setUrls(data) })
      .catch(() => {})
  }, [])

  return (
    <div className="url-health">
      <div className="url-row header">
        <div className="ucell domain">Domain</div>
        <div className="ucell">200 Rate</div>
        <div className="ucell">Blocked</div>
        <div className="ucell">Fail</div>
        <div className="ucell bar-cell">Health</div>
      </div>
      {urls.map(u => {
        const health = u.success_rate
        const color = health > 95 ? 'var(--accent-2)' : health > 75 ? 'var(--accent-3)' : 'var(--accent-4)'
        return (
          <div className="url-row" key={u.contract_address}>
            <div className="ucell domain">{u.contract_address}</div>
            <div className="ucell">{u.success_rate}%</div>
            <div className="ucell">{u.cloudflare_blocks}%</div>
            <div className="ucell">{u.not_found}%</div>
            <div className="ucell bar-cell">
              <div className="bar-bg">
                <div className="bar-fill" style={{ width: `${health}%`, background: color }} />
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
