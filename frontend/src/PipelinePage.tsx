import { useState, useEffect, useCallback } from 'react'

const API = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

type StepStatus = 'pending' | 'running' | 'completed' | 'failed'

interface StepInfo {
  id: string
  name: string
  status: StepStatus
  detail: { chunk_index?: number; chunk_total?: number; error?: string }
}

interface PipelineStatus {
  date: string
  is_running: boolean
  run_status: { running?: boolean; error?: string | null }
  steps: StepInfo[]
}

function PipelinePage({ initialDate }: { initialDate?: string }) {
  const [date, setDate] = useState(initialDate || new Date().toISOString().slice(0, 10))
  const [status, setStatus] = useState<PipelineStatus | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [justStarted, setJustStarted] = useState(false)

  const fetchStatus = useCallback(() => {
    fetch(`${API}/api/pipeline/status?date=${encodeURIComponent(date)}`)
      .then(r => r.json())
      .then(setStatus)
      .catch(() => setStatus(null))
  }, [date])

  useEffect(() => {
    fetchStatus()
  }, [fetchStatus])

  useEffect(() => {
    if (!status?.is_running && !justStarted) return
    const t = setInterval(fetchStatus, 2000)
    return () => clearInterval(t)
  }, [status?.is_running, justStarted, fetchStatus])

  useEffect(() => {
    if (status && !status.is_running && justStarted) {
      setJustStarted(false)
    }
  }, [status?.is_running, justStarted])

  const runFull = (force: boolean) => {
    setError(null)
    fetch(`${API}/api/pipeline/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ date, force }),
    })
      .then(r => {
        if (r.status === 409) {
          setError('이미 실행 중입니다.')
          return
        }
        if (!r.ok) throw new Error(r.statusText)
        setJustStarted(true)
        fetchStatus()
      })
      .catch(e => setError(e.message || '실행 요청 실패'))
  }

  const runStep = (step: string, mode: 'only' | 'from') => {
    setError(null)
    fetch(`${API}/api/pipeline/run-step`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ date, step, mode }),
    })
      .then(r => {
        if (r.status === 409) {
          setError('이미 실행 중입니다.')
          return
        }
        if (!r.ok) throw new Error(r.statusText)
        setJustStarted(true)
        fetchStatus()
      })
      .catch(e => setError(e.message || '실행 요청 실패'))
  }

  const globalError = status?.run_status?.error || error

  return (
    <div className="pipeline-page">
      <h2>파이프라인</h2>

      {/* 실행 컨트롤: 날짜 + 두 가지 실행 방식 */}
      <section className="pipeline-controls">
        <div className="pipeline-controls-inner">
        <div className="pipeline-controls-date">
          <label>
            <span className="pipeline-controls-label">날짜</span>
            <input
              type="date"
              value={date}
              onChange={e => setDate(e.target.value)}
            />
          </label>
        </div>
        <div className="pipeline-controls-actions">
          <button
            type="button"
            className="pipeline-btn pipeline-btn-primary"
            onClick={() => runFull(false)}
            disabled={status?.is_running === true}
            title="완료된 단계는 건너뛰고 이어서 실행합니다."
          >
            이어서 실행
          </button>
          <span className="pipeline-controls-hint">완료된 단계는 건너뜀</span>
          <button
            type="button"
            className="pipeline-btn pipeline-btn-secondary"
            onClick={() => runFull(true)}
            disabled={status?.is_running === true}
            title="저장된 결과를 무시하고 수집부터 다시 실행합니다."
          >
            처음부터 다시 실행
          </button>
          <span className="pipeline-controls-hint">캐시 무시, 전 단계 재실행</span>
        </div>
        </div>
      </section>

      {globalError && (
        <p className="pipeline-error">{globalError}</p>
      )}
      {status?.is_running && (
        <p className="pipeline-running">실행 중…</p>
      )}

      {/* 액티비티 다이어그램: 가로 흐름 (가로 스크롤로 잘림 방지) */}
      <section className="pipeline-diagram" aria-label="파이프라인 단계 흐름">
        <p className="pipeline-diagram-caption">수집 → 분석 → 요약 → 중복 제거 → 레터 생성</p>
        <div className="pipeline-flow-wrap">
        <div className="pipeline-flow">
          {(status?.steps ?? []).map((step, index) => (
            <div key={step.id} className="pipeline-flow-segment">
              <div
                className={`pipeline-node pipeline-node--${step.status}`}
                aria-label={`${step.name}: ${step.status}`}
              >
                <div className="pipeline-node-head">
                  <span className="pipeline-node-num">{index + 1}</span>
                  <span className="pipeline-node-name">{step.name}</span>
                  <span className={`pipeline-node-badge pipeline-node-badge--${step.status}`}>
                    {step.status === 'pending' && '대기'}
                    {step.status === 'running' && '실행 중'}
                    {step.status === 'completed' && '완료'}
                    {step.status === 'failed' && '실패'}
                  </span>
                </div>
                {(step.detail?.chunk_index != null && step.detail?.chunk_total != null) && (
                  <div className="pipeline-node-progress">
                    청크 {step.detail.chunk_index}/{step.detail.chunk_total}
                  </div>
                )}
                {step.detail?.error && (
                  <div className="pipeline-node-error">{step.detail.error}</div>
                )}
                <div className="pipeline-node-actions">
                  <button
                    type="button"
                    className="pipeline-btn pipeline-btn-small"
                    onClick={() => runStep(step.id, 'only')}
                    disabled={status?.is_running === true}
                  >
                    이 단계만
                  </button>
                  <button
                    type="button"
                    className="pipeline-btn pipeline-btn-small"
                    onClick={() => runStep(step.id, 'from')}
                    disabled={status?.is_running === true}
                  >
                    이 단계부터
                  </button>
                </div>
              </div>
              {index < (status?.steps ?? []).length - 1 && (
                <div className="pipeline-connector" aria-hidden="true">
                  <span className="pipeline-connector-line" />
                  <span className="pipeline-connector-arrow">→</span>
                </div>
              )}
            </div>
          ))}
        </div>
        </div>
      </section>
    </div>
  )
}

export default PipelinePage
