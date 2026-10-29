import type { DamageResult, DroughtResult, Job } from '../types'
import { CATEGORY, CLASS_COLOR } from './colors'

const pct = (v: number | null | undefined, signed = true) =>
  v == null ? '–' : `${signed && v > 0 ? '+' : ''}${v.toFixed(0)}%`

function Row({ label, value, cls, source }: { label: string; value: string; cls?: string | null; source: string }) {
  return (
    <div className="ind-row">
      <div>
        <div className="ind-label">{label}</div>
        <div className="ind-source">{source}</div>
      </div>
      <div className="ind-value">
        {value}
        {cls && <span className="cls" style={{ background: CLASS_COLOR[cls] ?? '#999' }}>{cls}</span>}
      </div>
    </div>
  )
}

function WeeklyRain({ weeks, from }: { weeks: (number | null)[]; from: string }) {
  const start = new Date(from)
  return (
    <div className="weekly">
      <div className="weekly-bars">
        {weeks.map((w, i) => {
          const d = new Date(start.getTime() + i * 7 * 864e5)
          const v = Math.min(w ?? 0, 200)
          return (
            <div key={i} className="wbar" title={`Week of ${d.toLocaleDateString([], { day: 'numeric', month: 'short' })}: ${w ?? '–'}% of normal`}>
              <div className={`wfill ${w != null && w < 50 ? 'dry' : ''}`} style={{ height: `${v / 2}%` }} />
            </div>
          )
        })}
        <div className="wline" style={{ bottom: '25%' }} title="50% of normal" />
        <div className="wline normal" style={{ bottom: '50%' }} title="Normal" />
      </div>
      <div className="weekly-axis"><span>{start.toLocaleDateString([], { day: 'numeric', month: 'short' })}</span><span>weekly rain, % of normal (dark: below 50%)</span><span>Sep</span></div>
    </div>
  )
}

export function DroughtDetail({ r, job }: { r: DroughtResult; job: Job }) {
  const cat = CATEGORY[r.category]
  return (
    <>
      <div className="detail-head">
        <h3>{r.name}</h3>
        <div className="muted small">{r.taluka && r.taluka !== r.name ? `${r.taluka}, ` : ''}{r.district}</div>
        <div className="cat-badge" style={{ background: cat.color }}>{cat.label}</div>
      </div>
      <h4>Step 1 · Trigger-1 (rainfall) <span className={`t1 ${r.trigger_1 ? 'on' : ''}`}>{r.trigger_1 ? 'met' : 'not met'}</span></h4>
      <Row label="Season rainfall" value={`${r.rain_mm ?? '–'} mm vs ${r.rain_normal_mm ?? '–'} mm normal`} source="CHIRPS daily · normal 1991-2020" />
      <Row label="Deviation" value={pct(r.rain_dev_pct)} source={`IMD category: ${r.rain_category ?? '–'}`} />
      <Row label="Longest dry spell" value={`${r.dry_spell_weeks} weeks`} source={r.dry_spell_from ? `from ${r.dry_spell_from} · weeks under 50% of normal` : 'weeks under 50% of normal'} />
      {job.season && <WeeklyRain weeks={r.weekly_rain_pct} from={`${job.season.year}-06-15`} />}
      <h4>Step 2 · Trigger-2 (impact on crops)</h4>
      <Row label="Crop greenness (NDVI)" value={pct(r.ndvi_dev_pct)} cls={r.remote_sensing_class} source={`MODIS MOD09A1 · latest 3 weeks vs normal-rain years ${r.normal_years.join(', ')}`} />
      <Row label="Crop wetness (NDWI)" value={pct(r.ndwi_dev_pct)} source={`VCI ${r.vci ?? '–'} (2001-2025 range)`} />
      <Row label="Moisture adequacy" value={r.mai_of_normal_pct == null ? '–' : `${r.mai_of_normal_pct.toFixed(0)}% of normal`} cls={r.soil_moisture_class} source={`MODIS MOD16A2 · AET/PET ${r.mai_pct ?? '–'}% vs ${r.mai_normal_pct ?? '–'}% normal`} />
      <Row label="Cropped area" value={pct(r.cropped_area_dev_pct)} cls={r.agriculture_class} source="MODIS peak NDVI on ESA WorldCover cropland" />
      <p className="muted small detail-note">Step 3: field verification by the State decides the final category.</p>
    </>
  )
}

export function DamageDetail({ r }: { r: DamageResult }) {
  return (
    <>
      <div className="detail-head">
        <h3>{r.name}</h3>
        <div className="muted small">{r.taluka}, {r.district}</div>
        {r.verify_first && <div className="cat-badge" style={{ background: '#a8341f' }}>Verify first</div>}
      </div>
      <Row label="Cropland" value={`${r.crop_ha.toLocaleString()} ha`} source="ESA WorldCover 2021, minus permanent water (JRC)" />
      <Row label="Flooded after the event" value={pct(r.flooded_pct, false)} source="Sentinel-1 radar vs same weeks 2019-2024" />
      <Row label="Damaged cropland" value={`${pct(r.damaged_pct, false)} · ${r.damaged_ha.toLocaleString()} ha`} source="Flooded, or unusual NDVI loss of 25%+" />
      <Row label="Severe" value={pct(r.severe_pct, false)} source="Flooded, or NDVI loss of 50%+" />
      <Row label="Crop greenness after" value={`${r.ndvi_after ?? '–'} vs ${r.ndvi_normal ?? '–'} normal`} source={`Sentinel-2 · mean loss ${pct(r.ndvi_loss_pct, false)}`} />
      <p className="muted small detail-note">A screening for the panchanama team, not a loss certificate.</p>
    </>
  )
}
