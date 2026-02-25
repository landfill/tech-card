import { useState, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import './App.css'

const API = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

function App() {
  const [dates, setDates] = useState<string[]>([])
  const [selected, setSelected] = useState<string | null>(null)
  const [content, setContent] = useState<string>('')
  const [feedbackType, setFeedbackType] = useState('wrong_source')
  const [feedbackContent, setFeedbackContent] = useState('')
  const [feedbackSent, setFeedbackSent] = useState(false)

  useEffect(() => {
    fetch(`${API}/api/letters`)
      .then(r => r.json())
      .then(setDates)
      .catch(() => setDates([]))
  }, [])

  useEffect(() => {
    if (!selected) return
    fetch(`${API}/api/letters/${selected}`)
      .then(r => r.text())
      .then(setContent)
      .catch(() => setContent(''))
    setFeedbackSent(false)
  }, [selected])

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

  return (
    <div className="app">
      <h1>데일리 인텔리전스 뉴스레터</h1>
      <nav>
        <strong>발송 내역</strong>
        <ul>
          {dates.map(d => (
            <li key={d}>
              <button
                className={selected === d ? 'active' : ''}
                onClick={() => setSelected(d)}
              >
                {d}
              </button>
            </li>
          ))}
        </ul>
      </nav>
      <main>
        {selected && (
          <>
            <h2>{selected}</h2>
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
        {!selected && dates.length === 0 && <p>발송된 레터가 없습니다.</p>}
        {!selected && dates.length > 0 && <p>날짜를 선택하세요.</p>}
      </main>
    </div>
  )
}

export default App
