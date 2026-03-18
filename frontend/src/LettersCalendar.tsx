import { useState, useMemo, useEffect } from 'react'

const WEEKDAYS = ['일', '월', '화', '수', '목', '금', '토']

function pad(n: number) {
  return n < 10 ? `0${n}` : String(n)
}

function toDateKey(year: number, month: number, day: number) {
  return `${year}-${pad(month)}-${pad(day)}`
}

type Props = {
  dates: string[]
  selected: string | null
  onSelectDate: (date: string) => void
}

export default function LettersCalendar({ dates, selected, onSelectDate }: Props) {
  const dateSet = useMemo(() => new Set(dates), [dates])

  const [viewYear, viewMonth] = useMemo(() => {
    if (selected && dateSet.has(selected)) {
      const [y, m] = selected.split('-').map(Number)
      return [y, m]
    }
    if (dates.length === 0) {
      const now = new Date()
      return [now.getFullYear(), now.getMonth() + 1]
    }
    const latest = dates[0]
    const [y, m] = latest.split('-').map(Number)
    return [y, m]
  }, [dates, selected, dateSet])

  const [currentYear, setCurrentYear] = useState(viewYear)
  const [currentMonth, setCurrentMonth] = useState(viewMonth)

  useEffect(() => {
    setCurrentYear(viewYear)
    setCurrentMonth(viewMonth)
  }, [viewYear, viewMonth])

  const { firstDay, daysInMonth } = useMemo(() => {
    const d = new Date(currentYear, currentMonth - 1, 1)
    const firstDay = d.getDay()
    const daysInMonth = new Date(currentYear, currentMonth, 0).getDate()
    return { firstDay, daysInMonth }
  }, [currentYear, currentMonth])

  const cells = useMemo(() => {
    const list: { type: 'empty' | 'day'; day?: number; dateKey?: string }[] = []
    for (let i = 0; i < firstDay; i++) list.push({ type: 'empty' })
    for (let day = 1; day <= daysInMonth; day++) {
      list.push({
        type: 'day',
        day,
        dateKey: toDateKey(currentYear, currentMonth, day),
      })
    }
    return list
  }, [firstDay, daysInMonth, currentYear, currentMonth])

  const goPrev = () => {
    if (currentMonth === 1) {
      setCurrentMonth(12)
      setCurrentYear((y) => y - 1)
    } else {
      setCurrentMonth((m) => m - 1)
    }
  }

  const goNext = () => {
    if (currentMonth === 12) {
      setCurrentMonth(1)
      setCurrentYear((y) => y + 1)
    } else {
      setCurrentMonth((m) => m + 1)
    }
  }

  const todayKey = (() => {
    const t = new Date()
    return toDateKey(t.getFullYear(), t.getMonth() + 1, t.getDate())
  })()

  return (
    <section className="letters-calendar">
      <div className="letters-calendar-header">
        <button
          type="button"
          className="letters-calendar-nav"
          onClick={goPrev}
          aria-label="이전 달"
        >
          ‹
        </button>
        <h2 className="letters-calendar-title">
          {currentYear}년 {currentMonth}월
        </h2>
        <button
          type="button"
          className="letters-calendar-nav"
          onClick={goNext}
          aria-label="다음 달"
        >
          ›
        </button>
      </div>
      <p className="letters-calendar-desc">발행된 날짜를 누르면 해당 호를 볼 수 있습니다.</p>
      <div className="letters-calendar-grid">
        {WEEKDAYS.map((wd) => (
          <div key={wd} className="letters-calendar-weekday">
            {wd}
          </div>
        ))}
        {cells.map((cell, i) =>
          cell.type === 'empty' ? (
            <div key={`e-${i}`} className="letters-calendar-day letters-calendar-day--empty" />
          ) : (
            <button
              key={cell.dateKey}
              type="button"
              className={`letters-calendar-day letters-calendar-day--clickable ${
                dateSet.has(cell.dateKey!) ? 'letters-calendar-day--has-letter' : ''
              } ${selected === cell.dateKey! ? 'letters-calendar-day--selected' : ''} ${
                cell.dateKey === todayKey ? 'letters-calendar-day--today' : ''
              }`}
              disabled={!dateSet.has(cell.dateKey!)}
              onClick={() => dateSet.has(cell.dateKey!) && onSelectDate(cell.dateKey!)}
              title={dateSet.has(cell.dateKey!) ? `${cell.dateKey} 호 보기` : undefined}
            >
              {cell.day}
            </button>
          )
        )}
      </div>
      {dates.length > 0 && (
        <div className="letters-calendar-legend">
          <span className="letters-calendar-legend-dot letters-calendar-legend-dot--has" />
          발행일
          <span className="letters-calendar-legend-dot letters-calendar-legend-dot--selected" />
          선택
        </div>
      )}
    </section>
  )
}
