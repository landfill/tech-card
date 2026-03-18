import { useState, useEffect, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import PipelinePage from './PipelinePage'
import CardNews from './CardNews'
import LettersCalendar from './LettersCalendar'
import type { CardsData } from './CardNews'
import './App.css'

const API = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

type View = 'letters' | 'pipeline'

function App() {
  const [view, setView] = useState<View>('letters')
  const [dates, setDates] = useState<string[]>([])
  const [selected, setSelected] = useState<string | null>(null)
  const [content, setContent] = useState<string>('')
  const [createdAt, setCreatedAt] = useState<string | null>(null)
  const [hasCards, setHasCards] = useState<boolean | null>(null)
  const [hasCardBg, setHasCardBg] = useState<boolean | null>(null)
  const [sourcesUsed, setSourcesUsed] = useState<string[]>([])
  const [feedbackType, setFeedbackType] = useState('wrong_source')
  const [feedbackContent, setFeedbackContent] = useState('')
  const [feedbackSent, setFeedbackSent] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const [letterDetailView, setLetterDetailView] = useState<'letter' | 'cards'>('letter')
  const [cardsData, setCardsData] = useState<CardsData | null>(null)
  const [cardsError, setCardsError] = useState<string | null>(null)
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    if (typeof window === 'undefined') return 'light'
    const saved = localStorage.getItem('theme') as 'light' | 'dark' | null
    if (saved === 'light' || saved === 'dark') return saved
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  })

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('theme', theme)
  }, [theme])

  const toggleTheme = useCallback(() => {
    setTheme((t) => (t === 'light' ? 'dark' : 'light'))
  }, [])

  useEffect(() => {
    fetch(`${API}/api/letters`)
      .then(r => r.json())
      .then(setDates)
      .catch(() => setDates([]))
  }, [])

  useEffect(() => {
    if (!selected) return
    setContent('')
    setCreatedAt(null)
    setHasCards(null)
    setHasCardBg(null)
    setSourcesUsed([])
    setFeedbackSent(false)
    setLetterDetailView('letter')
    setCardsData(null)
    setCardsError(null)
    const forDate = selected
    fetch(`${API}/api/letters/${selected}`)
      .then(r => r.text())
      .then((text) => {
        if (forDate === selected) setContent(text)
      })
      .catch(() => {
        if (forDate === selected) setContent('')
      })
    fetch(`${API}/api/letters/${selected}/info`)
      .then(r => r.json())
      .then((data: { date?: string; created_at?: string; has_cards?: boolean; has_card_bg?: boolean; sources_used?: string[] }) => {
        if (forDate !== selected) return
        setCreatedAt(data.created_at ?? null)
        setHasCards(data.has_cards ?? false)
        setHasCardBg(data.has_card_bg ?? false)
        setSourcesUsed(Array.isArray(data.sources_used) ? data.sources_used : [])
      })
      .catch(() => {
        if (forDate === selected) {
          setCreatedAt(null)
          setHasCards(null)
          setHasCardBg(null)
          setSourcesUsed([])
        }
      })
  }, [selected])

  const formatCreatedAt = (iso: string) => {
    try {
      const d = new Date(iso)
      return d.toLocaleString('ko-KR', {
        dateStyle: 'medium',
        timeStyle: 'short',
        hour12: false,
      })
    } catch {
      return iso
    }
  }

  const sendFeedback = () => {
    if (!selected) return
    fetch(`${API}/api/feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        issue_date: selected,
        type: feedbackType,
        content: feedbackContent,
      }),
    })
      .then(() => setFeedbackSent(true))
      .catch(() => {})
  }

  const deleteLetter = () => {
    if (!selected) return
    if (!window.confirm(`${selected} 호를 삭제합니다. 레터·인덱스·체크포인트·피드백이 모두 삭제됩니다. 계속할까요?`)) return
    setDeleteError(null)
    fetch(`${API}/api/letters/${selected}`, { method: 'DELETE' })
      .then(r => {
        if (r.status === 409) {
          setDeleteError('파이프라인 실행 중에는 삭제할 수 없습니다.')
          return
        }
        if (!r.ok) throw new Error(r.statusText)
        setSelected(null)
        setContent('')
        setCreatedAt(null)
        fetch(`${API}/api/letters`)
          .then(res => res.json())
          .then(setDates)
          .catch(() => setDates([]))
      })
      .catch(e => setDeleteError(e.message || '삭제 실패'))
  }

  const defaultPipelineDate = dates.length > 0 ? dates[0] : new Date().toISOString().slice(0, 10)

  return (
    <div className="app">
      <header className="app-header">
        <h1 className="app-title">데일리 인텔리전스 뉴스레터</h1>
        <button
          type="button"
          className="app-theme-toggle"
          onClick={toggleTheme}
          title={theme === 'light' ? '다크 모드로 전환' : '라이트 모드로 전환'}
          aria-label={theme === 'light' ? '다크 모드로 전환' : '라이트 모드로 전환'}
        >
          {theme === 'light' ? '🌙' : '☀️'}
        </button>
      </header>
      <nav className="app-tabs">
        <button
          type="button"
          className={view === 'letters' ? 'active' : ''}
          onClick={() => setView('letters')}
        >
          발송 내역
        </button>
        <button
          type="button"
          className={view === 'pipeline' ? 'active' : ''}
          onClick={() => setView('pipeline')}
        >
          파이프라인
        </button>
      </nav>
      {view === 'letters' && (
        <div className="letters-view">
          <aside className="letters-view-calendar">
            <LettersCalendar
              dates={dates}
              selected={selected}
              onSelectDate={setSelected}
            />
          </aside>
          <main className="letter-detail">
            {selected && (
              <>
                <header className="letter-detail-header">
                  <h2 className="letter-detail-date">{selected}</h2>
                  {createdAt && (
                    <p className="letter-meta">문서 생성: {formatCreatedAt(createdAt)}</p>
                  )}
                  {sourcesUsed.length > 0 && (
                    <p className="letter-sources">
                      수집 출처: {sourcesUsed.join(', ')}
                    </p>
                  )}
                  {hasCards !== null && (
                    <div className="letter-workflow-status" role="status" aria-label="워크플로 완료 상태">
                      <span className="letter-workflow-item letter-workflow-done">레터 생성됨</span>
                      <span className="letter-workflow-sep">·</span>
                      {hasCards ? (
                        <>
                          <span className="letter-workflow-item letter-workflow-done">카드뉴스 생성됨</span>
                          <span className="letter-workflow-sep">·</span>
                          {hasCardBg ? (
                            <span className="letter-workflow-item letter-workflow-done">배경 이미지 생성됨</span>
                          ) : (
                            <span className="letter-workflow-item letter-workflow-partial">배경 이미지 미생성</span>
                          )}
                        </>
                      ) : (
                        <span className="letter-workflow-item letter-workflow-pending">카드뉴스 미생성</span>
                      )}
                    </div>
                  )}
                </header>
                {hasCards === false && (
                  <p className="letter-workflow-hint">
                    이 호는 카드뉴스가 생성되지 않았습니다. 파이프라인 탭에서 해당 날짜를 선택한 뒤 &quot;이어서 실행&quot; 또는 &quot;카드 생성&quot; 단계부터 실행하세요.
                  </p>
                )}
                <div className="letter-actions">
                  <button
                    type="button"
                    className="letter-btn-cards neo"
                    disabled={!hasCards}
                    title={!hasCards ? '카드뉴스가 생성된 후 이용할 수 있습니다.' : undefined}
                    onClick={() => {
                      if (!hasCards) return
                      setCardsError(null)
                      setCardsData(null)
                      fetch(`${API}/api/letters/${selected}/cards`)
                        .then((r) => {
                          if (!r.ok) throw new Error(r.status === 404 ? '이 호는 카드뉴스가 없습니다.' : r.statusText)
                          return r.json()
                        })
                        .then((data: CardsData) => {
                          setCardsData(data)
                          setLetterDetailView('cards')
                        })
                        .catch((e) => setCardsError(e.message || '카드 로드 실패'))
                    }}
                  >
                    카드로 보기
                  </button>
                  <button type="button" className="letter-btn-delete neo" onClick={deleteLetter}>
                    이 호 삭제
                  </button>
                </div>
                {cardsError && <p className="letter-error">{cardsError}</p>}
                {deleteError && <p className="letter-error">{deleteError}</p>}
                {letterDetailView === 'cards' && cardsData ? (
                  <CardNews
                    date={selected}
                    cards={cardsData.cards}
                    bgImage={cardsData.bgImage}
                    onBack={() => setLetterDetailView('letter')}
                  />
                ) : (
                  <>
                    <div className="letter-body">
                      <ReactMarkdown>{content || '로딩 중...'}</ReactMarkdown>
                    </div>
                    <section className="feedback">
                  <h3>이 호에 대한 피드백</h3>
                  <select value={feedbackType} onChange={e => setFeedbackType(e.target.value)}>
                    <option value="wrong_source">잘못된 대상 수집</option>
                    <option value="stale">오래된 정보</option>
                    <option value="missing_trend">누락된 트렌드</option>
                    <option value="add_source">추가할 소스</option>
                  </select>
                  <textarea
                    value={feedbackContent}
                    onChange={e => setFeedbackContent(e.target.value)}
                    placeholder="내용"
                    rows={3}
                  />
                  <button onClick={sendFeedback}>제출</button>
                  {feedbackSent && <p className="success">제출되었습니다.</p>}
                </section>
                  </>
                )}
              </>
            )}
            {!selected && dates.length === 0 && (
              <p className="letter-empty">발송된 레터가 없습니다. 파이프라인 탭에서 수집·생성을 실행하세요.</p>
            )}
            {!selected && dates.length > 0 && (
              <p className="letter-hint">위 목록에서 날짜를 선택하면 해당 호를 볼 수 있습니다.</p>
            )}
          </main>
        </div>
      )}
      {view === 'pipeline' && (
        <main>
          <PipelinePage initialDate={defaultPipelineDate} />
        </main>
      )}
    </div>
  )
}

export default App
