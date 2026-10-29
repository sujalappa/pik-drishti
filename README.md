# Pik-drishti AI

Crop drought and crop damage for Maharashtra, measured from free satellite data, per taluka and per village.

- **Drought watch**: follows the Government of India *Manual for Drought Management (2016)*.
  - Trigger-1 comes from rainfall deficit and dry spells.
  - Trigger-2 comes from three impact indicators: crop condition (NDVI/NDWI), moisture adequacy (MAI) and cropped area.
  - Every taluka, or every village of one taluka, gets a category and the evidence behind it.
- **Crop damage after an event**: finds flooded cropland with Sentinel-1 radar, which sees through monsoon cloud, and crop loss with Sentinel-2 greenness.
  - Results are per village, and villages are ranked so panchanama teams know where to verify first.

Every number in the app, the PDF report and the exports names its data source.

## Data sources

| Dataset | Provider | Used for | Licence |
|---|---|---|---|
| CHIRPS v2.0 daily rainfall | UCSB Climate Hazards Center | Seasonal deviation, dry spells (normal 1991-2020) | CC0 |
| MODIS MOD09A1 v6.1 | NASA LP DAAC | NDVI, NDWI, VCI, cropped area | NASA open data |
| MODIS MOD16A2 v6.1 / MOD16A2GF | NASA LP DAAC | Moisture Adequacy Index (AET / PET) | NASA open data |
| Sentinel-1 SAR GRD | ESA / Copernicus | Flooded cropland | Copernicus open licence |
| Sentinel-2 L2A + Cloud Score+ | ESA / Copernicus; Google | Crop loss after an event | Copernicus open licence |
| ESA WorldCover 2021 | ESA | Cropland mask | CC BY 4.0 |
| JRC Global Surface Water | European Commission JRC | Excludes rivers and reservoirs | CC BY 4.0 |
| Indian Village Boundaries (Maharashtra) | DataMeet | Village, taluka and district units | ODbL |
| Manual for Drought Management (2016) | MoA&FW, Government of India | Indicators and thresholds | Government of India |

All imagery is processed in Google Earth Engine.

## Run locally

```bash
# once
python tools/prepare_boundaries.py         # needs data/boundaries/raw/mh1.geojson, mh2.geojson from DataMeet
cd frontend && npm install && npm run build && cd ..
cp .env.example .env                        # set GEE_PROJECT; run `earthengine authenticate` once

# every time
cd backend && uvicorn pikdrishti.api:app --port 8100
```

Open http://localhost:8100. Tests: `cd backend && python -m pytest tests -q`.

## Layout

- `backend/pikdrishti/drought.py`: manual-based drought assessment (Trigger-1, Trigger-2)
- `backend/pikdrishti/damage.py`: flood and crop-loss assessment after an event
- `backend/pikdrishti/pipelines.py`: jobs with visible steps, map layers, PDF, CSV, GeoJSON and KML exports
- `frontend/`: React + MapLibre web app
- `research/NOTES.md`: problem evidence, validation and sources
- `presentation/`: Seva Innovation Challenge 2026 deck
