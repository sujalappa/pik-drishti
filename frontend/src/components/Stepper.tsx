import type { Stage } from '../types'

const ICON: Record<Stage['status'], string> = {
  pending: '',
  running: '…',
  done: '✓',
  skipped: '–',
  failed: '!',
}

function duration(s: Stage): string {
  if (!s.started_at || !s.finished_at) return ''
  const sec = (new Date(s.finished_at).getTime() - new Date(s.started_at).getTime()) / 1000
  return sec < 1 ? '<1 s' : `${Math.round(sec)} s`
}

export default function Stepper({
  stages,
  selected,
  onSelect,
}: {
  stages: Stage[]
  selected: string | null
  onSelect: (id: string) => void
}) {
  return (
    <ol className="stepper">
      {stages.map((s, i) => (
        <li
          key={s.id}
          className={`step step-${s.status} ${selected === s.id ? 'selected' : ''}`}
          onClick={() => onSelect(s.id)}
        >
          <div className="step-icon">{ICON[s.status] || i + 1}</div>
          <div>
            <div className="step-title">
              <span>{s.name}</span>
              <span className="dur">{s.status === 'running' ? 'running' : duration(s)}</span>
            </div>
            {s.status === 'failed' && s.summary && <div className="step-summary">{s.summary}</div>}
          </div>
        </li>
      ))}
    </ol>
  )
}
