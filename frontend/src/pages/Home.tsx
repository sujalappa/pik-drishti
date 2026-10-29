import { useEffect, useState } from 'react'
import { api } from '../api'
import StatusChip from '../components/StatusChip'
import TalukaSelect from '../components/TalukaSelect'
import type { JobListItem, UnitCollection } from '../types'

const THIS_YEAR = new Date().getFullYear()

function go(id: string) {
  window.location.hash = `#/jobs/${id}`
}

function jobLine(j: JobListItem): string {
  const s = j.summary ?? {}
  if (j.status !== 'completed') return ''
  if (s.kind === 'drought') {
    const c = s.counts
    return `${s.trigger_1} of ${s.units} ${s.unit}s at Trigger-1 · ${c?.severe ?? 0} severe, ${c?.moderate ?? 0} moderate`
  }
  if (s.kind === 'damage') return `${s.damaged_ha?.toLocaleString()} ha damaged · ${s.verify_first} ${s.verify_first === 1 ? 'village' : 'villages'} to verify first`
  return ''
}

export default function Home() {
  const [talukas, setTalukas] = useState<UnitCollection | null>(null)
  const [jobs, setJobs] = useState<JobListItem[]>([])
  const [droughtTaluka, setDroughtTaluka] = useState('')
  const [damageTaluka, setDamageTaluka] = useState('solapur--madha')
  const [eventDate, setEventDate] = useState('2025-09-27')
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    api.talukas().then(setTalukas).catch((e) => setError(e.message))
    const load = () => api.jobs().then(setJobs).catch(() => {})
    load()
    const t = setInterval(load, 5000)
    return () => clearInterval(t)
  }, [])

  const start = async (key: string, fn: () => Promise<{ id: string }>) => {
    setBusy(key)
    setError('')
    try {
      go((await fn()).id)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not start the assessment')
    } finally {
      setBusy('')
    }
  }

  return (
    <main>
      <section className="hero">
        <h1>Crop drought and damage, measured from space</h1>
        <p className="lead">
          Village-level evidence for drought declaration and crop-loss panchanama, from free satellite data,
          following the Government of India drought manual.
        </p>
      </section>

      <section className="page mode-compare">
        <div className="panel form-card mode-card">
          <div className="mode-tag">Drought watch · Kharif {THIS_YEAR}</div>
          <h2>Which talukas and villages are in drought?</h2>
          <p className="muted small">
            Trigger-1 from rainfall deficit and dry spells, Trigger-2 from crop condition, moisture and cropped
            area. Sources: CHIRPS, MODIS, ESA WorldCover.
          </p>
          <button className="btn btn-primary btn-block" disabled={!!busy}
            onClick={() => start('state', () => api.createDrought('state', THIS_YEAR))}>
            {busy === 'state' ? 'Starting…' : 'Assess all talukas of Maharashtra'}
          </button>
          <div className="form-row">
            <label htmlFor="drought-taluka">Or assess every village of one taluka</label>
            <div className="inline-row">
              <TalukaSelect id="drought-taluka" talukas={talukas} value={droughtTaluka} onChange={setDroughtTaluka} />
              <button className="btn" disabled={!droughtTaluka || !!busy}
                onClick={() => start('villages', () => api.createDrought(droughtTaluka, THIS_YEAR))}>
                {busy === 'villages' ? 'Starting…' : 'Assess villages'}
              </button>
            </div>
          </div>
        </div>

        <div className="panel form-card mode-card">
          <div className="mode-tag damage">Crop damage after an event</div>
          <h2>Which villages lost crops to flood or heavy rain?</h2>
          <p className="muted small">
            Flooded fields from radar (sees through cloud) and crop loss from greenness, per village, ranked for
            panchanama verification. Sources: Sentinel-1, Sentinel-2.
          </p>
          <div className="form-row">
            <label htmlFor="damage-taluka">Taluka</label>
            <TalukaSelect id="damage-taluka" talukas={talukas} value={damageTaluka} onChange={setDamageTaluka} />
          </div>
          <div className="form-row">
            <label htmlFor="event-date">Date of the flood or heavy rain</label>
            <input id="event-date" type="date" value={eventDate} min="2019-06-01"
              max={new Date().toISOString().slice(0, 10)} onChange={(e) => setEventDate(e.target.value)} />
          </div>
          <button className="btn btn-primary btn-block" disabled={!damageTaluka || !eventDate || !!busy}
            onClick={() => start('damage', () => api.createDamage(damageTaluka, eventDate))}>
            {busy === 'damage' ? 'Starting…' : 'Assess crop damage'}
          </button>
          <p className="muted small hint">Example: Madha, Solapur after the Sina river floods of 27 Sep 2025.</p>
        </div>
      </section>
      {error && <div className="page"><div className="error-box">{error}</div></div>}

      <section className="page" id="assessments">
        <div className="section-head"><h2>Assessments</h2></div>
        {jobs.length === 0 ? (
          <div className="empty muted">No assessments yet.</div>
        ) : (
          <div className="panel list-panel">
            <table className="job-list">
              <tbody>
                {jobs.map((j) => (
                  <tr key={j.id} className="clickable" onClick={() => go(j.id)}>
                    <td className="job-name">{j.name}</td>
                    <td className="muted">{jobLine(j)}</td>
                    <td><StatusChip status={j.status} /></td>
                    <td className="muted">{new Date(j.created_at).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  )
}
