import { fileUrl } from '../api'
import type { Job } from '../types'

export function SourcesView({ job }: { job: Job }) {
  const method = job.summary.method ?? {}
  return (
    <div className="panel-body">
      <h3 className="sub">Data sources</h3>
      <table className="data-table">
        <thead><tr><th>Dataset</th><th>Provider</th><th>Used for</th><th>Resolution</th><th>Licence and citation</th></tr></thead>
        <tbody>
          {job.provenance.map((s) => (
            <tr key={s.dataset}>
              <td><strong>{s.dataset}</strong><div className="th-source">{s.source}</div></td>
              <td>{s.provider ?? ''}</td>
              <td>{s.used_for ?? ''}</td>
              <td>{s.resolution_m ? `${s.resolution_m} m` : '–'}</td>
              <td>{s.license}{s.citation ? `. ${s.citation}` : ''}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <h3 className="sub">Method</h3>
      <dl className="method">
        {Object.entries(method).map(([k, v]) => (
          <div key={k}><dt>{k.replace(/_/g, ' ')}</dt><dd>{v}</dd></div>
        ))}
      </dl>
    </div>
  )
}

export function DownloadsView({ job }: { job: Job }) {
  return (
    <div className="panel-body export-grid">
      {Object.entries(job.outputs.exports).map(([k, e]) => (
        <a key={k} className="export-card" href={fileUrl(job.id, e.file, true)} download>
          <strong>{e.label}</strong>
          <span className="muted small">{e.file}</span>
        </a>
      ))}
    </div>
  )
}
