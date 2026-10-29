import { useEffect, useState } from 'react'
import { api, fileUrl } from '../api'
import EventLog from '../components/EventLog'
import ResultsTable from '../components/ResultsTable'
import { DownloadsView, SourcesView } from '../components/SourcesView'
import StatusChip from '../components/StatusChip'
import Stepper from '../components/Stepper'
import { DamageDetail, DroughtDetail } from '../components/UnitDetail'
import UnitMap from '../components/UnitMap'
import type { DamageResult, DroughtResult, Job, UnitCollection } from '../types'

type Tab = 'table' | 'sources' | 'downloads' | 'processing'

function Kpis({ job }: { job: Job }) {
  const s = job.summary
  const items: [string, string, string][] = job.mode === 'drought' ? [
    [`${s.trigger_1 ?? '–'} / ${s.units ?? '–'}`, `${s.unit}s at Trigger-1`, 'rainfall deficit + dry spells'],
    [`${s.counts?.severe ?? 0}`, 'severe drought', 'all 3 impact indicators severe'],
    [`${s.counts?.moderate ?? 0}`, 'moderate drought', '2 of 3 impact indicators'],
    [s.mean_rain_dev_pct == null ? '–' : `${s.mean_rain_dev_pct > 0 ? '+' : ''}${s.mean_rain_dev_pct}%`, 'mean rainfall deviation', `1 Jun – ${s.season?.rain_end ?? ''}`],
  ] : [
    [`${(s.damaged_ha ?? 0).toLocaleString()} ha`, 'damaged cropland', `${s.damaged_pct ?? '–'}% of ${(s.crop_ha ?? 0).toLocaleString()} ha`],
    [`${s.verify_first ?? 0}`, s.verify_first === 1 ? 'village to verify first' : 'villages to verify first', '33%+ damaged or 10%+ flooded'],
    [`${s.units ?? '–'}`, 'villages assessed', `${s.taluka ?? ''}, ${s.district ?? ''}`],
    [s.event_date ?? '–', 'event date', `radar after: ${job.acquisitions?.radar_after.join(', ') || 'none'}`],
  ]
  return (
    <div className="kpis">
      {items.map(([v, l, n]) => (
        <div key={l} className="kpi"><div className="value">{v}</div><div className="label">{l}</div><div className="note">{n}</div></div>
      ))}
    </div>
  )
}

export default function JobPage({ jobId }: { jobId: string }) {
  const [job, setJob] = useState<Job | null>(null)
  const [units, setUnits] = useState<UnitCollection | null>(null)
  const [error, setError] = useState('')
  const [selected, setSelected] = useState<string | null>(null)
  const [tab, setTab] = useState<Tab>('table')
  const [stage, setStage] = useState<string | null>(null)

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>
    let alive = true
    const load = async () => {
      try {
        const j = await api.job(jobId)
        if (!alive) return
        setJob(j)
        if (j.status === 'queued' || j.status === 'running') timer = setTimeout(load, 2500)
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Could not load the assessment')
      }
    }
    load()
    return () => { alive = false; clearTimeout(timer) }
  }, [jobId])

  const done = job?.status === 'completed'
  useEffect(() => {
    if (done && job?.outputs.layers.units && !units) api.unitsOf(job.id, job.outputs.layers.units.file).then(setUnits).catch(() => {})
  }, [done, job, units])

  if (error) return <main className="page"><div className="error-box">{error}</div></main>
  if (!job) return <main className="page"><p className="muted">Loading…</p></main>

  const result = selected ? job.results?.[selected] : null
  const s = job.summary
  const subtitle = job.mode === 'drought'
    ? `Kharif ${job.season?.year ?? ''} · rainfall to ${job.season?.rain_end ?? '…'}, crops to ${job.season?.veg_end ?? '…'}`
    : `Event ${s.event_date ?? job.options.event_date} · Sentinel-1 radar and Sentinel-2`

  return (
    <main className="page job-page">
      <div className="crumbs"><a href="#/">Assessments</a> / {job.name}</div>
      <div className="job-head">
        <div>
          <h1>{job.name}</h1>
          <div className="job-meta"><StatusChip status={job.status} /><span className="muted">{subtitle}</span>
            {job.event_counts.warning > 0 && <span className="chip chip-warning">{job.event_counts.warning} warning{job.event_counts.warning > 1 ? 's' : ''}</span>}
          </div>
        </div>
        {done && job.outputs.exports.pdf && (
          <a className="btn btn-primary" href={fileUrl(job.id, job.outputs.exports.pdf.file, true)} download>Download report</a>
        )}
      </div>

      {!done && (
        <div className="run-grid">
          <div className="panel"><div className="panel-head"><h2>Steps</h2></div>
            <Stepper stages={job.stages} selected={stage} onSelect={setStage} />
          </div>
          <div>
            <div className="panel"><div className="panel-body">
              {job.stages.filter((x) => x.summary).map((x) => <p key={x.id}><strong>{x.name}:</strong> {x.summary}</p>)}
              {job.status !== 'failed' && <p className="muted">Working with Earth Engine; a state-wide run takes about two minutes.</p>}
            </div></div>
            <EventLog events={job.events} stages={job.stages} />
          </div>
        </div>
      )}

      {done && (
        <>
          <Kpis job={job} />
          <div className="result-grid">
            {units ? <UnitMap job={job} units={units} selected={selected} onSelect={setSelected} /> : <div className="map-wrap map-loading">Loading map…</div>}
            <aside className="panel detail">
              {result ? (
                job.mode === 'drought' ? <DroughtDetail r={result as DroughtResult} job={job} /> : <DamageDetail r={result as DamageResult} />
              ) : (
                <div className="detail-empty">
                  <h3>{job.mode === 'drought' ? 'Click a taluka or village' : 'Click a village'}</h3>
                  <p className="muted small">
                    {job.mode === 'drought'
                      ? 'Each indicator shows its value, its class under the drought manual, and the satellite it comes from.'
                      : 'Villages outlined in dark red are first in line for panchanama field verification.'}
                  </p>
                </div>
              )}
            </aside>
          </div>
          <div className="tabs">
            {(['table', 'sources', 'downloads', 'processing'] as Tab[]).map((t) => (
              <button key={t} className={tab === t ? 'active' : ''} onClick={() => setTab(t)}>
                {{ table: 'Table', sources: 'Sources and method', downloads: 'Downloads', processing: 'Processing' }[t]}
              </button>
            ))}
          </div>
          {tab === 'table' && <ResultsTable job={job} selected={selected} onSelect={(id) => { setSelected(id); window.scrollTo({ top: 0, behavior: 'smooth' }) }} />}
          {tab === 'sources' && <div className="panel"><SourcesView job={job} /></div>}
          {tab === 'downloads' && <div className="panel"><DownloadsView job={job} /></div>}
          {tab === 'processing' && (
            <div className="run-grid">
              <div className="panel"><div className="panel-head"><h2>Steps</h2></div>
                <Stepper stages={job.stages} selected={stage} onSelect={setStage} /></div>
              <div>
                <div className="panel"><div className="panel-body">
                  {job.stages.map((x) => <p key={x.id}><strong>{x.name}:</strong> {x.summary ?? '–'}</p>)}
                </div></div>
                <EventLog events={job.events} stages={job.stages} />
              </div>
            </div>
          )}
        </>
      )}
    </main>
  )
}
