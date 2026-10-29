import type { ExpressionSpecification } from 'maplibre-gl'
import type { DroughtCategory } from '../types'

export const CATEGORY: Record<DroughtCategory, { label: string; color: string }> = {
  severe: { label: 'Severe drought', color: '#a8341f' },
  moderate: { label: 'Moderate drought', color: '#e07b1a' },
  normal: { label: 'Trigger-1 only (crops normal so far)', color: '#f3d27a' },
  'no trigger': { label: 'No Trigger-1', color: '#cfe3d4' },
  'insufficient data': { label: 'Insufficient data', color: '#c9c6bd' },
}

export const CLASS_COLOR: Record<string, string> = {
  severe: '#a8341f', moderate: '#e07b1a', mild: '#e9b949', normal: '#5b8f6a',
}

export interface Metric {
  key: string
  label: string
  unit: string
  stops: [number, string][]
  source: string
}

const DRY_WET = ['#8c510a', '#d8b365', '#f6e8c3', '#f5f5f5', '#c7eae5', '#5ab4ac', '#01665e']

export const DROUGHT_METRICS: Metric[] = [
  { key: 'rain_dev_pct', label: 'Rainfall deviation', unit: '%', source: 'CHIRPS',
    stops: [[-60, DRY_WET[0]], [-40, DRY_WET[1]], [-20, DRY_WET[2]], [0, DRY_WET[3]], [20, DRY_WET[4]], [40, DRY_WET[5]], [60, DRY_WET[6]]] },
  { key: 'dry_spell_weeks', label: 'Longest dry spell', unit: 'weeks', source: 'CHIRPS',
    stops: [[0, '#f5f5f5'], [2, '#f6e8c3'], [3, '#d8b365'], [5, '#a6611a'], [8, '#5c3006']] },
  { key: 'ndvi_dev_pct', label: 'Crop NDVI deviation', unit: '%', source: 'MODIS MOD09A1',
    stops: [[-40, DRY_WET[0]], [-30, DRY_WET[1]], [-20, DRY_WET[2]], [0, DRY_WET[3]], [20, DRY_WET[5]], [40, DRY_WET[6]]] },
  { key: 'mai_of_normal_pct', label: 'Moisture adequacy (% of normal)', unit: '%', source: 'MODIS MOD16A2',
    stops: [[25, DRY_WET[0]], [50, DRY_WET[1]], [75, DRY_WET[2]], [100, DRY_WET[3]], [125, DRY_WET[5]]] },
]

export const DAMAGE_METRICS: Metric[] = [
  { key: 'damaged_pct', label: 'Damaged cropland', unit: '%', source: 'Sentinel-1, Sentinel-2',
    stops: [[0, '#f7f4ea'], [10, '#f6dd9c'], [20, '#f2b134'], [33, '#c0392b'], [50, '#7a1f12']] },
  { key: 'flooded_pct', label: 'Flooded cropland', unit: '%', source: 'Sentinel-1',
    stops: [[0, '#f5f7fa'], [2, '#cfe0f7'], [5, '#8db8ee'], [10, '#3b82d6'], [25, '#123f80']] },
  { key: 'ndvi_loss_pct', label: 'Mean NDVI loss', unit: '%', source: 'Sentinel-2',
    stops: [[0, '#f7f4ea'], [10, '#f6dd9c'], [20, '#f2b134'], [35, '#c0392b']] },
]

export function categoryExpr(): ExpressionSpecification {
  const pairs = Object.entries(CATEGORY).flatMap(([k, v]) => [k, v.color])
  return ['match', ['coalesce', ['get', 'category'], 'insufficient data'], ...pairs, '#c9c6bd'] as unknown as ExpressionSpecification
}

export function metricExpr(m: Metric): ExpressionSpecification {
  return ['case', ['==', ['get', m.key], null], '#d9d6cc',
    ['interpolate', ['linear'], ['get', m.key], ...m.stops.flat()]] as ExpressionSpecification
}

export function gradient(stops: [number, string][]): string {
  return `linear-gradient(90deg,${stops.map(([, c]) => c).join(',')})`
}
