import { useState, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'

const API = import.meta.env.VITE_API_BASE || 'http://localhost:8000'
const WEEKLY_POLL_INTERVAL_MS = 1500
const WEEKLY_POLL_MAX_ATTEMPTS = 80

interface TrendItem {
  topic: string
  days: string[]
  impact: string
  direction: string
}

interface Top5Item {
  title: string
  url: string
  mentions: number
  impact: string
}

interface WeeklyMeta {
  week: string
  date_range: string[]
  total_items: number
  filtered_items: number
  trend_map: TrendItem[]
  category_stats: Record<string, { count: number; high_count: number }>
  top5: Top5Item[]
  daily_counts: Record<string, number>
}

interface WeeklyRunResponse {
  message: string
  week_id: string
  started_at: string
}

interface WeeklyStatus {
  week_id: string
  exists: boolean
  status: 'running' | 'completed'
  letter_ready: boolean
  letter_updated_at: number | null
  meta_ready: boolean
  meta_updated_at: number | null
  cards_ready: boolean
  cards_updated_at: number | null
  publish_result: { sent: boolean; recipients: number; error: string | null } | null
}

const WEEKDAYS = ['월', '화', '수', '목', '금', '토', '일']

const directionLabel: Record<string, string> = {
  sustained: '지속',
  rising: '상승',
  steady: '유지',
  fading: '소강',
}

const impactBar: Record<string, string> = {
  high: '■■■',
  medium: '■■',
  low: '■',
}

export default function WeeklyPage() {
  const [weeks, setWeeks] = useState<string[]>([])
  const [selected, setSelected] = useState<string | null>(null)
  const [meta, setMeta] = useState<WeeklyMeta | null>(null)
  const [letter, setLetter] = useState<string>('')
  const [detailView, setDetailView] = useState<'letter' | 'trend'>('trend')
  const [running, setRunning] = useState(false)
  const [reloadNonce, setReloadNonce] = useState(0)

  useEffect(() => {
    void fetchWeeks().then(setWeeks).catch(() => setWeeks([]))
  }, [])

  useEffect(() => {
    if (!selected) return
    fetch(`${API}/api/weekly/${selected}`).then(r => r.text()).then(setLetter).catch(() => setLetter(''))
    fetch(`${API}/api/weekly/${selected}/meta`).then(r => r.json()).then(setMeta).catch(() => setMeta(null))
  }, [selected, reloadNonce])

  useEffect(() => {
    if (weeks.length > 0 && !selected) setSelected(weeks[0])
  }, [weeks, selected])

  const idx = selected ? weeks.indexOf(selected) : -1

  const runWeekly = async () => {
    setRunning(true)
    try {
      const response = await fetch(`${API}/api/weekly/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ force: true }),
      })
      if (!response.ok) throw new Error(`weekly_run_failed:${response.status}`)

      const result = await response.json() as WeeklyRunResponse
      await waitForWeeklyArtifacts(result.week_id, result.started_at)

      const nextWeeks = await fetchWeeks()
      setWeeks(nextWeeks)
      setSelected(result.week_id)
      setReloadNonce((value) => value + 1)
    } catch {
      // Leave current week view intact when the run request fails or times out.
    } finally {
      setRunning(false)
    }
  }

  const weekDates = meta?.date_range
    ? _getWeekDaysFromRange(meta.date_range[0], meta.date_range[1])
    : []

  return (
    <div className="weekly-page">
      <div className="weekly-nav">
        <button disabled={idx <= 0} onClick={() => setSelected(weeks[idx - 1])}>◀</button>
        <span className="weekly-nav-label">{selected || '주간 리뷰 없음'}</span>
        <button disabled={idx < 0 || idx >= weeks.length - 1} onClick={() => setSelected(weeks[idx + 1])}>▶</button>
        <button className="neo weekly-run-btn" onClick={runWeekly} disabled={running}>
          {running ? '생성 중...' : '주간 레터 생성'}
        </button>
      </div>

      {meta && (
        <>
          <div className="weekly-summary">
            <span>{meta.date_range[0]} ~ {meta.date_range[1]}</span>
            <span>전체 {meta.total_items}건 중 {meta.filtered_items}건 분석</span>
          </div>

          <div className="weekly-tabs">
            <button className={detailView === 'trend' ? 'active' : ''} onClick={() => setDetailView('trend')}>트렌드 분석</button>
            <button className={detailView === 'letter' ? 'active' : ''} onClick={() => setDetailView('letter')}>주간 레터</button>
          </div>

          {detailView === 'trend' && (
            <div className="weekly-trend">
              {/* 트렌드맵 */}
              <h3>주간 트렌드맵</h3>
              <table className="trend-table">
                <thead>
                  <tr>
                    <th>트렌드</th>
                    {WEEKDAYS.map(d => <th key={d}>{d}</th>)}
                    <th>강도</th>
                    <th>흐름</th>
                  </tr>
                </thead>
                <tbody>
                  {meta.trend_map.map((t, i) => (
                    <tr key={i}>
                      <td className="trend-topic">{t.topic}</td>
                      {weekDates.map((wd, j) => (
                        <td key={j} className="trend-dot">
                          {t.days.some(d => wd.endsWith(d)) ? '●' : ''}
                        </td>
                      ))}
                      <td className="trend-impact">{impactBar[t.impact] || '■'}</td>
                      <td className="trend-direction">{directionLabel[t.direction] || t.direction}</td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {/* 카테고리 비중 */}
              <h3>카테고리 비중</h3>
              <div className="category-bars">
                {Object.entries(meta.category_stats).map(([cat, s]) => {
                  const total = meta.filtered_items || 1
                  const pct = Math.round((s.count / total) * 100)
                  return (
                    <div key={cat} className="category-bar-row">
                      <span className="category-bar-label">{cat}</span>
                      <div className="category-bar-track">
                        <div className="category-bar-fill" style={{ width: `${pct}%` }} />
                      </div>
                      <span className="category-bar-value">{s.count}건 ({pct}%)</span>
                    </div>
                  )
                })}
              </div>

              {/* Top 5 */}
              <h3>Top 5 하이라이트</h3>
              <ol className="top5-list">
                {meta.top5.map((item, i) => (
                  <li key={i}>
                    <a href={item.url} target="_blank" rel="noreferrer">{item.title}</a>
                    <span className="top5-meta"> — {item.mentions}회 언급, {item.impact}</span>
                  </li>
                ))}
              </ol>

              {/* 일별 항목 수 */}
              <h3>일별 분석 항목</h3>
              <div className="daily-counts">
                {Object.entries(meta.daily_counts || {}).sort().map(([d, c]) => (
                  <span key={d} className="daily-count-chip">{d.slice(5)} : {c}건</span>
                ))}
              </div>
            </div>
          )}

          {detailView === 'letter' && (
            <div className="weekly-letter-body">
              <ReactMarkdown>{letter || '레터를 불러오는 중...'}</ReactMarkdown>
            </div>
          )}
        </>
      )}

      {!meta && selected && <p className="weekly-empty">이 주차의 주간 리뷰가 아직 생성되지 않았습니다.</p>}
      {!selected && weeks.length === 0 && <p className="weekly-empty">아직 생성된 주간 리뷰가 없습니다. '주간 레터 생성' 버튼을 누르세요.</p>}
    </div>
  )
}

async function fetchWeeks(): Promise<string[]> {
  const response = await fetch(`${API}/api/weekly`)
  if (!response.ok) throw new Error(`weekly_list_failed:${response.status}`)
  return response.json() as Promise<string[]>
}

async function waitForWeeklyArtifacts(weekId: string, startedAt: string): Promise<WeeklyStatus> {
  const startedAtMs = new Date(startedAt).getTime()
  for (let attempt = 0; attempt < WEEKLY_POLL_MAX_ATTEMPTS; attempt += 1) {
    const response = await fetch(`${API}/api/weekly/${weekId}/status`)
    if (response.ok) {
      const status = await response.json() as WeeklyStatus
      const letterUpdated = status.letter_updated_at ?? 0
      const metaUpdated = status.meta_updated_at ?? 0
      if (
        status.exists &&
        status.letter_ready &&
        status.meta_ready &&
        letterUpdated * 1000 >= startedAtMs &&
        metaUpdated * 1000 >= startedAtMs
      ) {
        return status
      }
    }
    await delay(WEEKLY_POLL_INTERVAL_MS)
  }
  throw new Error(`weekly_timeout:${weekId}`)
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms)
  })
}

function _getWeekDaysFromRange(start: string, end: string): string[] {
  const dates: string[] = []
  const s = new Date(start)
  const e = new Date(end)
  for (let d = new Date(s); d <= e; d.setDate(d.getDate() + 1)) {
    dates.push(d.toISOString().slice(5, 10)) // MM-DD
  }
  return dates
}
