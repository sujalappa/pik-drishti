import { useState } from 'react'
import type { EventLevel, JobEvent, Stage } from '../types'

type Filter = 'all' | EventLevel

export default function EventLog({ events, stages }: { events: JobEvent[]; stages: Stage[] }) {
  const [filter, setFilter] = useState<Filter>('all')
  const stageName = Object.fromEntries(stages.map((s) => [s.id, s.name]))
  const shown = events.filter((e) => filter === 'all' || e.level === filter).slice().reverse()

  return (
    <div className="panel">
      <div className="panel-head">
        <h2>Event log</h2>
        <div className="filters">
          {(['all', 'warning', 'error', 'info'] as Filter[]).map((f) => (
            <button key={f} className={filter === f ? 'on' : ''} onClick={() => setFilter(f)}>
              {f}
            </button>
          ))}
        </div>
      </div>
      <div className="events">
        {shown.length === 0 && <div className="event muted">No events.</div>}
        {shown.map((e, i) => (
          <div key={i} className="event">
            <div className="event-top">
              <span className={`chip chip-${e.level}`}>{e.level}</span>
              <span className="event-code">{e.code}</span>
              <span className="event-time">{new Date(e.time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
            </div>
            <div>{e.message}</div>
            {e.action && <div className="event-action">→ {e.action}</div>}
            {e.stage && <div className="event-stage">{stageName[e.stage] ?? e.stage}</div>}
          </div>
        ))}
      </div>
    </div>
  )
}
