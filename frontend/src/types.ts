import type { Geometry } from 'geojson'

export type StageStatus = 'pending' | 'running' | 'done' | 'skipped' | 'failed'
export type JobStatus = 'queued' | 'running' | 'completed' | 'failed'
export type EventLevel = 'info' | 'warning' | 'error'
export type Mode = 'drought' | 'damage'

export interface Stage {
  id: string
  name: string
  description: string
  status: StageStatus
  started_at: string | null
  finished_at: string | null
  summary: string | null
  metrics: Record<string, unknown>
  preview: string | null
}

export interface JobEvent {
  time: string
  level: EventLevel
  code: string
  stage: string | null
  message: string
  action: string | null
}

export interface Legend {
  type: 'continuous' | 'categorical'
  min?: number
  max?: number
  unit?: string
  palette?: string[]
  items?: { label: string; color: string }[]
}

export interface RasterOutput {
  file: string
  corners: [number, number][]
  label: string
  legend: Legend | null
}

export interface FileOutput {
  file: string
  label: string
}

export interface Source {
  key?: string
  dataset: string
  provider?: string
  source: string
  resolution_m?: number
  license: string
  used_for?: string
  citation?: string
}

export type DroughtCategory = 'severe' | 'moderate' | 'normal' | 'no trigger' | 'insufficient data'
export type ImpactClass = 'severe' | 'moderate' | 'normal' | null

export interface DroughtResult {
  name: string
  district: string
  taluka?: string | null
  rain_mm: number | null
  rain_normal_mm: number | null
  rain_dev_pct: number | null
  rain_category: string | null
  dry_spell_weeks: number
  dry_spell_from: string | null
  weekly_rain_pct: (number | null)[]
  trigger_1: boolean
  normal_years: number[]
  ndvi_dev_pct: number | null
  ndwi_dev_pct: number | null
  vci: number | null
  remote_sensing_class: ImpactClass
  mai_pct: number | null
  mai_normal_pct: number | null
  mai_of_normal_pct: number | null
  soil_moisture_class: string | null
  cropped_area_dev_pct: number | null
  agriculture_class: ImpactClass
  category: DroughtCategory
}

export interface DamageResult {
  name: string
  taluka: string
  district: string
  crop_ha: number
  flooded_pct: number | null
  damaged_pct: number | null
  severe_pct: number | null
  damaged_ha: number
  ndvi_loss_pct: number | null
  ndvi_after: number | null
  ndvi_normal: number | null
  verify_first: boolean
}

export type UnitResult = DroughtResult | DamageResult

export interface Season {
  year: number
  rain_start: string
  rain_end: string
  veg_end: string
  et_end: string
  rs_start: string
}

export interface Summary {
  kind?: Mode
  unit?: 'taluka' | 'village'
  units?: number
  trigger_1?: number
  counts?: Record<DroughtCategory, number>
  mean_rain_dev_pct?: number | null
  season?: Season
  method?: Record<string, string>
  crop_ha?: number
  damaged_ha?: number
  damaged_pct?: number | null
  verify_first?: number
  event_date?: string
  taluka?: string
  district?: string
}

export interface Job {
  id: string
  name: string
  mode: Mode
  status: JobStatus
  created_at: string
  finished_at: string | null
  options: Record<string, string | number>
  stages: Stage[]
  outputs: {
    layers: Record<string, FileOutput>
    rasters: Record<string, RasterOutput>
    exports: Record<string, FileOutput>
  }
  summary: Summary
  provenance: Source[]
  event_counts: Record<EventLevel, number>
  events: JobEvent[]
  results: Record<string, UnitResult> | null
  season?: Season
  acquisitions?: { radar_after: string[]; radar_before: string[]; optical_after: string[]; orbits: string[] }
}

export interface JobListItem {
  id: string
  name: string
  mode: Mode
  status: JobStatus
  created_at: string
  finished_at: string | null
  summary: Summary
}

export interface UnitFeature {
  type: 'Feature'
  properties: { id: string; taluka: string; district: string; village?: string; villages?: number }
  geometry: Geometry
}

export interface UnitCollection {
  type: 'FeatureCollection'
  features: UnitFeature[]
}
