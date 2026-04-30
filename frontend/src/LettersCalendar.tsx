import { useMemo, useState } from 'react'

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

  const anchorDate = useMemo(() => {
    if (selected && dateSet.has(selected)) {
      const [year, month] = selected.split('-').map(Number)
      return { year, month }
    }
    if (dates.length > 0) {
      const [year, month] = dates[0].split('-').map(Number)
      return { year, month }
    }
    const now = new Date()
    return { year: now.getFullYear(), month: now.getMonth() + 1 }
  }, [dateSet, dates, selected])

  const anchorKey = `${anchorDate.year}-${anchorDate.month}`
  const [viewState, setViewState] = useState({ anchorKey, monthOffset: 0 })
  const monthOffset = viewState.anchorKey === anchorKey ? viewState.monthOffset : 0

  const currentMonthDate = useMemo(
    () => new Date(anchorDate.year, anchorDate.month - 1 + monthOffset, 1),
    [anchorDate.month, anchorDate.year, monthOffset],
  )
  const currentYear = currentMonthDate.getFullYear()
  const currentMonth = currentMonthDate.getMonth() + 1

  const { firstDay, daysInMonth } = useMemo(() => {
    const firstDate = new Date(currentYear, currentMonth - 1, 1)
    return {
      firstDay: firstDate.getDay(),
      daysInMonth: new Date(currentYear, currentMonth, 0).getDate(),
    }
  }, [currentMonth, currentYear])

  const cells = useMemo(() => {
    const list: { type: 'empty' | 'day'; day?: number; dateKey?: string; hasLetter?: boolean }[] = []
    for (let index = 0; index < firstDay; index += 1) {
      list.push({ type: 'empty' })
    }
    for (let day = 1; day <= daysInMonth; day += 1) {
      const dateKey = toDateKey(currentYear, currentMonth, day)
      list.push({
        type: 'day',
        day,
        dateKey,
        hasLetter: dateSet.has(dateKey),
      })
    }
    return list
  }, [currentMonth, currentYear, dateSet, daysInMonth, firstDay])

  const goPrev = () => {
    setViewState({ anchorKey, monthOffset: monthOffset - 1 })
  }

  const goNext = () => {
    setViewState({ anchorKey, monthOffset: monthOffset + 1 })
  }

  const todayKey = (() => {
    const today = new Date()
    return toDateKey(today.getFullYear(), today.getMonth() + 1, today.getDate())
  })()

  return (
    <section className="letters-calendar">
      <div className="letters-calendar-header">
        <button type="button" className="letters-calendar-nav" onClick={goPrev} aria-label="이전 달">
          ‹
        </button>
        <h2 className="letters-calendar-title">
          {currentYear}년 {currentMonth}월
        </h2>
        <button type="button" className="letters-calendar-nav" onClick={goNext} aria-label="다음 달">
          ›
        </button>
      </div>
      <p className="letters-calendar-desc">발행된 날짜를 누르면 해당 호를 볼 수 있습니다.</p>
      <div className="letters-calendar-grid">
        {WEEKDAYS.map((weekday) => (
          <div key={weekday} className="letters-calendar-weekday">
            {weekday}
          </div>
        ))}
        {cells.map((cell, index) =>
          cell.type === 'empty' ? (
            <div key={`e-${index}`} className="letters-calendar-day letters-calendar-day--empty" />
          ) : (
            <button
              key={cell.dateKey}
              type="button"
              className={`letters-calendar-day ${
                cell.hasLetter
                  ? 'letters-calendar-day--clickable letters-calendar-day--has-letter'
                  : 'letters-calendar-day--inactive'
              } ${selected === cell.dateKey ? 'letters-calendar-day--selected' : ''} ${
                cell.dateKey === todayKey ? 'letters-calendar-day--today' : ''
              }`}
              disabled={!cell.hasLetter}
              onClick={() => cell.hasLetter && cell.dateKey && onSelectDate(cell.dateKey)}
              title={cell.hasLetter ? `${cell.dateKey} 호 보기` : undefined}
            >
              {cell.day}
            </button>
          ),
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
