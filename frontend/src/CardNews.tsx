import { useState, useEffect, useCallback } from 'react'

const API = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

export type CardItem = {
  type: string
  title: string
  body: string[]
}

export type CardsData = {
  date: string
  cards: CardItem[]
  bgImage?: string | null
}

type CardNewsProps = {
  date: string
  cards: CardItem[]
  bgImage?: string | null
}

function CardNews({ date, cards, bgImage }: CardNewsProps) {
  const [current, setCurrent] = useState(0)
  const [bgLoaded, setBgLoaded] = useState(false)
  const [touchStart, setTouchStart] = useState<number | null>(null)

  const total = cards.length
  const card = cards[current]

  const goNext = useCallback(() => {
    setCurrent((c) => (c + 1) % total)
  }, [total])

  const goPrev = useCallback(() => {
    setCurrent((c) => (c - 1 + total) % total)
  }, [total])

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight') goNext()
      if (e.key === 'ArrowLeft') goPrev()
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [goNext, goPrev])

  const handleTouchStart = (e: React.TouchEvent) => setTouchStart(e.touches[0].clientX)
  const handleTouchEnd = (e: React.TouchEvent) => {
    if (touchStart === null) return
    const dx = e.changedTouches[0].clientX - touchStart
    if (dx > 40) goPrev()
    if (dx < -40) goNext()
    setTouchStart(null)
  }

  const handleCardClick = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect()
    const x = e.clientX - rect.left
    const ratio = x / rect.width
    if (ratio < 0.35) goPrev()
    else if (ratio > 0.65) goNext()
  }

  const bgUrl = bgImage ? `${API}/api/letters/${date}/card-bg` : null

  if (total === 0) {
    return (
      <div className="card-news card-news-empty">
        <p>표시할 카드가 없습니다.</p>
      </div>
    )
  }

  return (
    <div className="card-news">
      <div
        className="card-news-container"
        style={{ aspectRatio: '9/16' }}
        onTouchStart={handleTouchStart}
        onTouchEnd={handleTouchEnd}
        onClick={handleCardClick}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'ArrowLeft') goPrev()
          if (e.key === 'ArrowRight') goNext()
        }}
        aria-label={`카드 ${current + 1} of ${total}. 왼쪽 클릭 이전, 오른쪽 클릭 다음.`}
      >
        <div className="card-news-progress" style={{ width: `${((current + 1) / total) * 100}%` }} />
        <div className="card-news-slide">
          {bgUrl && (
            <img
              src={bgUrl}
              alt=""
              aria-hidden
              className="card-news-bg"
              style={{ opacity: bgLoaded ? 1 : 0 }}
              onLoad={() => setBgLoaded(true)}
            />
          )}
          {!bgUrl && <div className="card-news-bg card-news-bg-fallback" />}
          <div className="card-news-overlay" />
          <div className="card-news-nav-zones" aria-hidden="true">
            {total > 1 && <span className="card-news-zone card-news-zone-prev" />}
            {total > 1 && <span className="card-news-zone card-news-zone-next" />}
          </div>
          <div className="card-news-content">
            <p className="card-news-meta">{current + 1} / {total}</p>
            <h3 className="card-news-title">{card.title}</h3>
            <div className="card-news-body">
              {card.body.map((line, i) => (
                <p key={i}>{line}</p>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default CardNews
