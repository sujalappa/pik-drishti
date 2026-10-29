import { useMemo, useState } from 'react'
import type { Job } from '../types'
import { CATEGORY, CLASS_COLOR } from './colors'

type Col = { key: string; label: string; source?: string; num?: boolean }

const DROUGHT_COLS: Col[] = [
  { key: 'name', label: 'Unit' }, { key: 'district', label: 'District' },
  { key: 'category', label: 'Category', source: 'Manual for Drought Management 2016' },
  { key: 'rain_dev_pct', label: 'Rain dev. %', source: 'CHIRPS', num: true },
  { key: 'dry_spell_weeks', label: 'Dry spell (wk)', source: 'CHIRPS', num: true },
  { key: 'ndvi_dev_pct', label: 'NDVI dev. %', source: 'MODIS MOD09A1', num: true },
  { key: 'ndwi_dev_pct', label: 'NDWI dev. %', source: 'MODIS MOD09A1', num: true },
  { key: 'mai_of_normal_pct', label: 'MAI % normal', source: 'MODIS MOD16A2', num: true },
  { key: 'cropped_area_dev_pct', label: 'Cropped area %', source: 'MODIS + ESA WorldCover', num: true },
]
const DAMAGE_COLS: Col[] = [
  { key: 'name', label: 'Village' }, { key: 'verify_first', label: 'Verify first' },
  { key: 'crop_ha', label: 'Cropland ha', source: 'ESA WorldCover', num: true },
  { key: 'flooded_pct', label: 'Flooded %', source: 'Sentinel-1', num: true },
  { key: 'damaged_pct', label: 'Damaged %', source: 'Sentinel-1, Sentinel-2', num: true },
  { key: 'damaged_ha', label: 'Damaged ha', source: 'Sentinel-1, Sentinel-2', num: true },
  { key: 'ndvi_loss_pct', label: 'NDVI loss %', source: 'Sentinel-2', num: true },
]
const ORDER = ['severe', 'moderate', 'normal', 'no trigger', 'insufficient data']

export default function ResultsTable({ job, selected, onSelect }: {
  job: Job
  selected: string | null
  onSelect: (id: string) => void
}) {
  const cols = job.mode === 'drought' ? DROUGHT_COLS : DAMAGE_COLS
  const [sort, setSort] = useState<{ key: string; asc: boolean }>(
    job.mode === 'drought' ? { key: 'category', asc: true } : { key: 'damaged_ha', asc: false })
  const [q, setQ] = useState('')
  const rows = useMemo(() => {
    const all: Record<string, unknown>[] = Object.entries(job.results ?? {}).map(([id, r]) => ({ ...(r as unknown as Record<string, unknown>), id }))
    const filtered = q ? all.filter((r) => `${r.name} ${r.district}`.toLowerCase().includes(q.toLowerCase())) : all
    const val = (r: Record<string, unknown>) => sort.key === 'category' ? ORDER.indexOf(String(r.category)) : r[sort.key]
    return filtered.sort((a, b) => {
      const x = val(a), y = val(b)
      if (x == null) return 1
      if (y == null) return -1
      const c = typeof x === 'number' && typeof y === 'number' ? x - y : String(x).localeCompare(String(y))
      return sort.asc ? c : -c
    })
  }, [job.results, sort, q])

  const cell = (c: Col, r: Record<string, unknown>) => {
    const v = r[c.key]
    if (c.key === 'category') {
      const cat = CATEGORY[v as keyof typeof CATEGORY]
      return <span className="cls" style={{ background: cat?.color, color: v === 'severe' || v === 'moderate' ? '#fff' : '#3b3a33' }}>{String(v)}</span>
    }
    if (c.key === 'verify_first') return v ? <span className="cls" style={{ background: CLASS_COLOR.severe }}>yes</span> : ''
    if (typeof v === 'number') return v.toLocaleString(undefined, { maximumFractionDigits: 1 })
    return v == null ? '–' : String(v)
  }

  return (
    <div className="panel">
      <div className="panel-head">
        <h2>{rows.length} {job.summary.unit === 'taluka' ? 'talukas' : 'villages'}</h2>
        <input className="search-input" type="search" placeholder="Search" value={q} onChange={(e) => setQ(e.target.value)} />
      </div>
      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              {cols.map((c) => (
                <th key={c.key} title={c.source ? `Source: ${c.source}` : undefined} className={c.num ? 'num' : ''}
                  onClick={() => setSort({ key: c.key, asc: sort.key === c.key ? !sort.asc : !c.num })}>
                  {c.label}{sort.key === c.key ? (sort.asc ? ' ↑' : ' ↓') : ''}
                  {c.source && <div className="th-source">{c.source}</div>}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={String(r.id)} className={`clickable ${selected === r.id ? 'sel' : ''}`} onClick={() => onSelect(String(r.id))}>
                {cols.map((c) => <td key={c.key} className={c.num ? 'num' : ''}>{cell(c, r)}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
