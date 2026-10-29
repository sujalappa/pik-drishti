// MapLibre 6 loads its web worker as a separate ES module that imports a shared
// chunk; bundlers don't emit these, so copy them to public/ for setWorkerUrl().
import { copyFileSync, mkdirSync } from 'node:fs'

const src = 'node_modules/maplibre-gl/dist'
const dst = 'public/maplibre'
mkdirSync(dst, { recursive: true })
for (const f of ['maplibre-gl-worker.mjs', 'maplibre-gl-shared.mjs']) copyFileSync(`${src}/${f}`, `${dst}/${f}`)
