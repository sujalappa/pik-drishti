"""Drought assessment that follows the Government of India Manual for Drought Management (2016).

Step 1, Trigger-1 (mandatory, Table 3.10): seasonal rainfall deviation and dry spells.
Step 2, Trigger-2 (impact, Table 3.11): three of the four impact indicators, compared with the unit's own
recent normal-rainfall years (manual 3.2.2: "averaging ... at least 3 recent normal years"):
  agriculture    -> cropped area (satellite estimate) vs normal years
  remote sensing -> NDVI and NDWI deviation over the latest ~3 weeks, worst of the two
  soil moisture  -> Moisture Adequacy Index (AET / PET), as % of its normal-year value
  hydrology      -> not assessed from satellites here
Severe: all three indicators severe. Moderate: two of three moderate or severe (manual, p. 44).
Step 3 (field verification) stays with the State; the output ranks units for it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from .earthengine import init_ee, latest_date, reduce_table

CHIRPS = "UCSB-CHG/CHIRPS/DAILY"
MOD09 = "MODIS/061/MOD09A1"
MOD16 = "MODIS/061/MOD16A2"          # current season (from 2021)
MOD16_HIST = "MODIS/061/MOD16A2GF"   # gap-filled, for past years
WORLDCOVER = "ESA/WorldCover/v200"

RAIN_NORMAL_YEARS = (1991, 2020)     # manual: at least 30 years
RECENT_YEARS = tuple(range(2017, 2026))  # candidates for the unit's normal-rainfall years
MIN_NORMAL_YEARS = 3
VCI_YEARS = (2001, 2025)             # manual: at least 10 years
RS_WINDOW_DAYS = 24                  # latest three MODIS 8-day composites
MONSOON_ONSET = (6, 15)
DRY_SPELL_WEEKS = 3                  # manual: 3-4 weeks, 3 on light soils
CROPPED_NDVI = 0.6                   # cropland pixel counted as cropped if its season peak NDVI exceeds this

SOURCES = [
    {"key": "rain", "dataset": "CHIRPS v2.0 daily rainfall", "provider": "UC Santa Barbara Climate Hazards Center",
     "source": CHIRPS, "resolution_m": 5566, "license": "Public domain (CC0)",
     "used_for": "Seasonal rainfall deviation and dry spells (normal: 1991-2020)",
     "citation": "Funk et al. (2015), Scientific Data 2:150066"},
    {"key": "veg", "dataset": "MODIS Terra surface reflectance 8-day, MOD09A1 v6.1", "provider": "NASA LP DAAC",
     "source": MOD09, "resolution_m": 500, "license": "NASA, free and open",
     "used_for": "NDVI and NDWI deviation, VCI (2001-2025), cropped area",
     "citation": "Vermote (2021), MOD09A1 v061, doi:10.5067/MODIS/MOD09A1.061"},
    {"key": "et", "dataset": "MODIS Terra evapotranspiration 8-day, MOD16A2 v6.1 (and gap-filled MOD16A2GF)",
     "provider": "NASA LP DAAC", "source": f"{MOD16}; {MOD16_HIST}", "resolution_m": 500,
     "license": "NASA, free and open", "used_for": "Moisture Adequacy Index (AET / PET)",
     "citation": "Running et al. (2021), MOD16A2 v061, doi:10.5067/MODIS/MOD16A2.061"},
    {"key": "crop", "dataset": "ESA WorldCover 2021 v200", "provider": "European Space Agency",
     "source": WORLDCOVER, "resolution_m": 10, "license": "CC BY 4.0", "used_for": "Cropland mask (class 40)",
     "citation": "Zanaga et al. (2022), doi:10.5281/zenodo.7254221"},
    {"key": "manual", "dataset": "Manual for Drought Management (2016)", "provider":
     "Ministry of Agriculture & Farmers Welfare, Government of India", "source": "agricoop.gov.in",
     "license": "Government of India", "used_for": "Indicators, thresholds, Trigger-1 and Trigger-2 rules"},
]


@dataclass(frozen=True)
class Season:
    year: int
    rain_start: date
    rain_end: date        # last day with rainfall data (inclusive)
    veg_end: date         # start date of the latest MODIS 8-day composite
    et_end: date

    @property
    def rs_start(self) -> date:
        return self.veg_end - timedelta(days=RS_WINDOW_DAYS - 8)

    def as_dict(self) -> dict:
        d = {k: str(v) if isinstance(v, date) else v for k, v in self.__dict__.items()}
        d["rs_start"] = str(self.rs_start)
        return d


def _d(ee, year, d: date):
    return ee.Date.fromYMD(year, d.month, d.day)


def _same_window(ee, col, year, start: date, end: date):
    """Filter `col` to [start, end] (inclusive) shifted to `year`."""
    return col.filterDate(_d(ee, year, start), _d(ee, year, end).advance(1, "day"))


def kharif_season(year: int, region_geojson: dict | None = None) -> Season:
    """Kharif season windows ending at the latest data available today."""
    ee = init_ee()
    region = ee.Geometry.Point([76.0, 19.0]) if region_geojson is None else ee.Geometry(region_geojson)

    def latest(cid):
        d = latest_date(ee, cid, region, f"{year}-06-01")
        if d is None:
            raise ValueError(f"No {cid} data yet for the {year} season")
        return date.fromisoformat(d)

    return Season(year, date(year, 6, 1), min(latest(CHIRPS), date(year, 9, 30)),
                  min(latest(MOD09), date(year, 11, 30)), min(latest(MOD16), date(year, 11, 30)))


def _rain_image(ee, s: Season):
    chirps = ee.ImageCollection(CHIRPS)
    years = ee.List.sequence(*RAIN_NORMAL_YEARS)

    def pair(start, end, name):
        cur = _same_window(ee, chirps, s.year, start, end).sum().rename(f"{name}_cur")
        norm = ee.ImageCollection(years.map(
            lambda y: _same_window(ee, chirps, ee.Number(y), start, end).sum())).mean().rename(f"{name}_norm")
        return cur.addBands(norm)

    bands = [pair(s.rain_start, s.rain_end, "rain")]
    bands += [_same_window(ee, chirps, y, s.rain_start, s.rain_end).sum().rename(f"rain_{y}") for y in RECENT_YEARS]
    week, n = date(s.year, *MONSOON_ONSET), 0
    while week + timedelta(days=6) <= s.rain_end:
        n += 1
        bands.append(pair(week, week + timedelta(days=6), f"w{n:02d}"))
        week += timedelta(days=7)
    return ee.Image.cat(bands), n


def _mod09_indices(ee, img):
    qa = img.select("StateQA")
    clear = qa.bitwiseAnd(3).eq(0).And(qa.bitwiseAnd(4).eq(0))
    red, nir, swir = (img.select(b).multiply(1e-4) for b in ("sur_refl_b01", "sur_refl_b02", "sur_refl_b06"))
    ndvi = nir.subtract(red).divide(nir.add(red))
    ndwi = nir.subtract(swir).divide(nir.add(swir))
    return ndvi.addBands(ndwi).rename(["ndvi", "ndwi"]).updateMask(clear)


def cropland(ee):
    return ee.Image(ee.ImageCollection(WORLDCOVER).first()).eq(40)


def _veg_image(ee, s: Season):
    mod09 = ee.ImageCollection(MOD09)

    def rs(year):  # NDVI, NDWI over the latest window
        return _same_window(ee, mod09, year, s.rs_start, s.veg_end).map(lambda i: _mod09_indices(ee, i)).median()

    def cropped(year):
        peak = _same_window(ee, mod09, year, date(s.year, 8, 1), s.veg_end).map(
            lambda i: _mod09_indices(ee, i).select("ndvi")).max()
        return peak.gt(CROPPED_NDVI)

    def et(year):
        col = ee.ImageCollection(MOD16 if year == s.year else MOD16_HIST)
        return _same_window(ee, col, year, s.rain_start, s.et_end).map(
            lambda i: i.select(["ET", "PET"]).updateMask(i.select("ET").lte(32700).And(i.select("PET").lte(32700)))
        ).sum().multiply(0.1)

    bands = []
    for y in (*RECENT_YEARS, s.year):
        tag = "cur" if y == s.year else str(y)
        bands += [rs(y).rename([f"ndvi_{tag}", f"ndwi_{tag}"]), cropped(y).rename(f"crop_{tag}"),
                  et(y).rename([f"aet_{tag}", f"pet_{tag}"])]
    hist = ee.ImageCollection(ee.List.sequence(*VCI_YEARS).map(lambda y: rs(ee.Number(y)).select("ndvi")))
    vmin, vmax = hist.min(), hist.max()
    vci = rs(s.year).select("ndvi").subtract(vmin).divide(vmax.subtract(vmin)).multiply(100).clamp(0, 100)
    bands.append(vci.rename("vci"))
    return ee.Image.cat(bands).updateMask(cropland(ee))


def _dev(cur, norm):
    if cur is None or norm in (None, 0):
        return None
    return (cur - norm) / abs(norm) * 100


def dev_class(dev):
    """Manual 3.2.2: deviation -20 to -30% moderate, below -30% severe."""
    if dev is None:
        return None
    return "severe" if dev < -30 else "moderate" if dev <= -20 else "normal"


def _worst(*classes):
    order = {"severe": 2, "moderate": 1, "normal": 0}
    known = [c for c in classes if c]
    return max(known, key=order.get) if known else None


def rain_category(dev):
    """IMD categories (manual Table 3.1)."""
    if dev is None:
        return None
    if dev <= -99.5:
        return "no rain"
    if dev <= -60:
        return "large deficient"
    if dev <= -20:
        return "deficient"
    return "normal" if dev < 20 else "excess"


def mai_class(mai):
    """Manual Table 3.5."""
    if mai is None:
        return None
    return "severe" if mai <= 25 else "moderate" if mai <= 50 else "mild" if mai <= 75 else "normal"


def longest_dry_spell(ratios: list[float | None]) -> tuple[int, int | None]:
    """Longest run of weeks with rainfall below 50% of normal -> (weeks, index of first week)."""
    run = best = 0
    start = best_start = None
    for i, r in enumerate(ratios):
        if r is not None and r < 0.5:
            if run == 0:
                start = i
            run += 1
            if run > best:
                best, best_start = run, start
        else:
            run = 0
    return best, best_start


def trigger_1(rain_dev, scanty: bool, dry_spell: bool) -> bool:
    """Manual Table 3.10. Deficient = 20% or more below normal; scanty = 60% or more below."""
    deficient = rain_dev is not None and rain_dev <= -20
    if deficient and dry_spell:
        return True
    if deficient:
        return scanty
    return dry_spell


def normal_years(row: dict) -> list[int]:
    """The unit's recent years whose season rainfall was 'normal' (within +-19%, IMD), at least three."""
    norm = row.get("rain_norm")
    devs = {y: _dev(row.get(f"rain_{y}"), norm) for y in RECENT_YEARS}
    good = [y for y, d in devs.items() if d is not None and -19 <= d <= 19]
    if len(good) >= MIN_NORMAL_YEARS:
        return good
    not_dry = [y for y, d in devs.items() if d is not None and d > -19]
    return not_dry if len(not_dry) >= MIN_NORMAL_YEARS else list(RECENT_YEARS)


def _mean(row, key, years):
    vals = [row.get(f"{key}_{y}") for y in years]
    vals = [v for v in vals if v is not None]
    return sum(vals) / len(vals) if vals else None


def classify(row: dict, season: Season, n_weeks: int) -> dict:
    """Turn raw per-unit means into the manual's indicators and drought category."""
    rain_dev = _dev(row.get("rain_cur"), row.get("rain_norm"))
    ratios = []
    for i in range(1, n_weeks + 1):
        c, nrm = row.get(f"w{i:02d}_cur"), row.get(f"w{i:02d}_norm")
        ratios.append(None if c is None or not nrm else c / nrm)
    spell, spell_start = longest_dry_spell(ratios)
    onset = date(season.year, *MONSOON_ONSET)
    spell_from = str(onset + timedelta(days=7 * spell_start)) if spell_start is not None else None
    t1 = trigger_1(rain_dev, rain_dev is not None and rain_dev <= -60, spell >= DRY_SPELL_WEEKS)

    years = normal_years(row)
    ndvi_dev = _dev(row.get("ndvi_cur"), _mean(row, "ndvi", years))
    ndwi_dev = _dev(row.get("ndwi_cur"), _mean(row, "ndwi", years))
    rs = _worst(dev_class(ndvi_dev), dev_class(ndwi_dev))

    def mai(tag_or_years):
        if isinstance(tag_or_years, str):
            a, p = row.get(f"aet_{tag_or_years}"), row.get(f"pet_{tag_or_years}")
            return a / p * 100 if a is not None and p else None
        vals = [mai(str(y)) for y in tag_or_years]
        vals = [v for v in vals if v is not None]
        return sum(vals) / len(vals) if vals else None

    mai_cur, mai_norm = mai("cur"), mai(years)
    mai_rel = mai_cur / mai_norm * 100 if mai_cur is not None and mai_norm else None
    sm = mai_class(mai_rel)
    crop_dev = _dev(row.get("crop_cur"), _mean(row, "crop", years))
    agri = dev_class(crop_dev)

    impacts = [c for c in (agri, rs, "normal" if sm == "mild" else sm) if c]
    if not t1:
        category = "no trigger"
    elif len(impacts) < 3:
        category = "insufficient data"
    elif all(c == "severe" for c in impacts):
        category = "severe"
    elif sum(c in ("moderate", "severe") for c in impacts) >= 2:
        category = "moderate"
    else:
        category = "normal"

    def r(v, n=1):
        return None if v is None else round(v, n)

    return {
        "rain_mm": r(row.get("rain_cur"), 0), "rain_normal_mm": r(row.get("rain_norm"), 0),
        "rain_dev_pct": r(rain_dev), "rain_category": rain_category(rain_dev),
        "dry_spell_weeks": spell, "dry_spell_from": spell_from,
        "weekly_rain_pct": [None if x is None else round(x * 100) for x in ratios],
        "trigger_1": t1, "normal_years": years,
        "ndvi_dev_pct": r(ndvi_dev), "ndwi_dev_pct": r(ndwi_dev), "vci": r(row.get("vci")),
        "remote_sensing_class": rs,
        "mai_pct": r(mai_cur), "mai_normal_pct": r(mai_norm), "mai_of_normal_pct": r(mai_rel),
        "soil_moisture_class": sm,
        "cropped_area_dev_pct": r(crop_dev), "agriculture_class": agri,
        "category": category,
    }


def rain_table(fc, season: Season, scale: float = 5566) -> tuple[dict[str, dict], int]:
    """Trigger-1 inputs per feature: seasonal and weekly rainfall, current and normal."""
    ee = init_ee()
    rain, n_weeks = _rain_image(ee, season)
    return reduce_table(rain, fc, scale), n_weeks


def impact_table(fc, season: Season, scale: float = 500) -> dict[str, dict]:
    """Trigger-2 inputs per feature: NDVI, NDWI, cropped area, AET and PET for every recent year, and VCI."""
    return reduce_table(_veg_image(init_ee(), season), fc, scale)


def assess(fc, season: Season, rain_scale: float = 5566, veg_scale: float = 500) -> dict[str, dict]:
    """Run the assessment for every feature (property `id`) of `fc`."""
    rain_rows, n_weeks = rain_table(fc, season, rain_scale)
    veg_rows = impact_table(fc, season, veg_scale)
    return {uid: classify({**rain_rows.get(uid, {}), **veg_rows.get(uid, {})}, season, n_weeks)
            for uid in rain_rows}


def rain_deviation_image(season: Season):
    """Seasonal rainfall deviation from the 1991-2020 normal, % (for the map)."""
    ee = init_ee()
    chirps = ee.ImageCollection(CHIRPS)
    cur = _same_window(ee, chirps, season.year, season.rain_start, season.rain_end).sum()
    norm = ee.ImageCollection(ee.List.sequence(*RAIN_NORMAL_YEARS).map(
        lambda y: _same_window(ee, chirps, ee.Number(y), season.rain_start, season.rain_end).sum())).mean()
    return cur.subtract(norm).divide(norm.max(1)).multiply(100).resample("bicubic")


def ndvi_deviation_image(season: Season):
    """Latest-window cropland NDVI vs the 2017-2025 median for the same weeks, % (for the map)."""
    ee = init_ee()
    mod09 = ee.ImageCollection(MOD09)

    def rs(year):
        return _same_window(ee, mod09, year, season.rs_start, season.veg_end).map(
            lambda i: _mod09_indices(ee, i).select("ndvi")).median()

    norm = ee.ImageCollection([rs(y) for y in RECENT_YEARS]).median()
    return rs(season.year).subtract(norm).divide(norm.abs().max(0.05)).multiply(100).updateMask(cropland(ee))


METHOD = {
    "trigger_1": "Rainfall 20% or more below the 1991-2020 normal with a dry spell of 3+ weeks (each week under 50% "
                 "of normal), or 60% or more below normal (Manual Table 3.10).",
    "remote_sensing": f"NDVI and NDWI over the latest {RS_WINDOW_DAYS} days vs the unit's normal-rainfall years "
                      "(2017-2025); -20 to -30% moderate, below -30% severe; worst of the two (Manual 3.2.2).",
    "soil_moisture": "Moisture Adequacy Index = AET / PET from MODIS, expressed as % of the unit's normal-year "
                     "value, then Manual Table 3.5 (<=25 severe, 26-50 moderate, 51-75 mild).",
    "agriculture": f"Share of cropland whose August-to-date peak NDVI exceeds {CROPPED_NDVI}, vs normal years; "
                   "same deviation classes as remote sensing.",
    "category": "Severe if all three impact indicators are severe; moderate if two of three are moderate or "
                "severe; otherwise normal (Manual, Trigger-2). Field verification (Step 3) decides the final "
                "category.",
    "adaptations": "MODIS PET is a land-surface potential, not the crop water need used in the manual's weekly "
                   "water balance, so MAI is compared with the unit's own normal years. Cropped area is a "
                   "satellite estimate, not Agriculture Department sowing returns.",
}
