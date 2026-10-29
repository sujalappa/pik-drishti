import type { UnitCollection } from '../types'

export default function TalukaSelect({ talukas, value, onChange, id }: {
  talukas: UnitCollection | null
  value: string
  onChange: (id: string) => void
  id: string
}) {
  const byDistrict = new Map<string, { id: string; name: string }[]>()
  for (const f of talukas?.features ?? []) {
    const list = byDistrict.get(f.properties.district) ?? []
    list.push({ id: f.properties.id, name: f.properties.taluka })
    byDistrict.set(f.properties.district, list)
  }
  return (
    <select id={id} value={value} onChange={(e) => onChange(e.target.value)} disabled={!talukas}>
      <option value="">{talukas ? 'Choose a taluka' : 'Loading talukas…'}</option>
      {[...byDistrict.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([d, list]) => (
        <optgroup key={d} label={d}>
          {list.sort((a, b) => a.name.localeCompare(b.name)).map((t) => (
            <option key={t.id} value={t.id}>{t.name}</option>
          ))}
        </optgroup>
      ))}
    </select>
  )
}
