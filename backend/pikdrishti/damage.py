"""Crop damage after a flood or heavy-rain event, per village or farm.

Flooding: Sentinel-1 VV radar backscatter after the event compared with the same weeks in earlier years at the
same pixel (Z-score change detection, after DeVries et al. 2020 and the UN-SPIDER recommended practice). Radar
sees through monsoon cloud; normally wet paddy is not flagged because the baseline is the pixel's own history.
Crop loss: Sentinel-2 NDVI 1-5 weeks after the event compared with the same weeks in normal years.
Only cropland (ESA WorldCover class 40) is counted; permanent water (JRC) is excluded.

The result is a screening for field verification, not a loss certificate: officials still sign the panchanama.
"""

from __future__ import annotations

from datetime import date, timedelta

from .earthengine import init_ee, reduce_table

S1 = "COPERNICUS/S1_GRD"
S2 = "COPERNICUS/S2_SR_HARMONIZED"
CLOUD_SCORE = "GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED"
WORLDCOVER = "ESA/WorldCover/v200"
JRC = "JRC/GSW1_4/GlobalSurfaceWater"

BASELINE_YEARS = range(2019, 2025)
Z_FLOOD = -2.0          # standard deviations below the pixel's normal backscatter
VV_WATER_DB = -15.0     # and dark enough to be water
SEVERE_LOSS, MODERATE_LOSS = 0.5, 0.25
Z_LOSS = -1.5           # NDVI drop must also be unusual for that pixel (vs its spread across baseline years)
LIKELY_RELIEF_SHARE = 33.0  # % of crop area damaged: SDRF input-subsidy threshold is 33% crop loss
FLOODED_SHARE = 10.0        # % of crop area under water after the event

SOURCES = [
    {"key": "s1", "dataset": "Sentinel-1 SAR GRD (C-band, VV)", "provider": "European Space Agency / Copernicus",
     "source": S1, "resolution_m": 10, "license": "Copernicus open licence",
     "used_for": "Flooded and waterlogged cropland after the event (Z-score against 2019-2024)",
     "citation": "DeVries et al. (2020), Remote Sensing of Environment 240:111664; UN-SPIDER recommended practice"},
    {"key": "s2", "dataset": "Sentinel-2 L2A surface reflectance (harmonized) with Cloud Score+",
     "provider": "European Space Agency / Copernicus; Google", "source": f"{S2}; {CLOUD_SCORE}", "resolution_m": 10,
     "license": "Copernicus open licence", "used_for": "NDVI after the event vs normal years (crop loss)",
     "citation": "Pasquarella et al. (2023), Cloud Score+, CVPR Workshops"},
    {"key": "crop", "dataset": "ESA WorldCover 2021 v200", "provider": "European Space Agency", "source": WORLDCOVER,
     "resolution_m": 10, "license": "CC BY 4.0", "used_for": "Cropland mask (class 40)"},
    {"key": "water", "dataset": "JRC Global Surface Water v1.4", "provider": "European Commission JRC", "source": JRC,
     "resolution_m": 30, "license": "CC BY 4.0", "used_for": "Excludes rivers, lakes and reservoirs",
     "citation": "Pekel et al. (2016), Nature 540:418-422"},
]

METHOD = {
    "flood": f"Sentinel-1 VV after the event vs the same weeks in {BASELINE_YEARS.start}-{BASELINE_YEARS.stop - 1} "
             f"at each pixel; flooded if {Z_FLOOD} standard deviations below normal and darker than {VV_WATER_DB} dB.",
    "loss": "Sentinel-2 NDVI 7-35 days after the event vs the same weeks in 2019-2024; "
            f"loss >= {int(SEVERE_LOSS * 100)}% severe, {int(MODERATE_LOSS * 100)}-{int(SEVERE_LOSS * 100)}% moderate, "
            f"counted only where the drop is also unusual for that pixel ({Z_LOSS} standard deviations).",
    "damaged": "Damaged crop area = flooded, or moderate/severe NDVI loss.",
    "flag": f"Villages with {LIKELY_RELIEF_SHARE:.0f}% or more of their crop area damaged, or {FLOODED_SHARE:.0f}% or "
            "more flooded, are listed first for field verification (SDRF input subsidy needs 33% crop loss).",
    "limits": "Radar misses water under tall, dense crops; NDVI loss can also come from early harvest. "
              "A screening for field verification, not a loss certificate.",
}


def _s1_vv(ee, region, start, end, orbit=None):
    col = (ee.ImageCollection(S1).filterBounds(region).filterDate(start, end)
           .filter(ee.Filter.eq("instrumentMode", "IW"))
           .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV")))
    if orbit:
        col = col.filter(ee.Filter.eq("orbitProperties_pass", orbit))
    return col.select("VV")


def _s2_ndvi(ee, region, start, end):
    s2 = ee.ImageCollection(S2).filterBounds(region).filterDate(start, end)
    cs = ee.ImageCollection(CLOUD_SCORE).filterBounds(region).filterDate(start, end)
    linked = s2.linkCollection(cs, ["cs"])
    return linked.map(lambda i: i.normalizedDifference(["B8", "B4"]).rename("ndvi")
                      .updateMask(i.select("cs").gte(0.6)).copyProperties(i, ["system:time_start"]))


def event_info(region_geojson: dict, event_day: date) -> dict:
    """Radar and optical acquisitions available around the event (for the user and the report)."""
    ee = init_ee()
    region = ee.Geometry(region_geojson)
    post = _s1_vv(ee, region, str(event_day), str(event_day + timedelta(days=12)))
    pre = _s1_vv(ee, region, str(event_day - timedelta(days=14)), str(event_day))
    opt = _s2_ndvi(ee, region, str(event_day + timedelta(days=7)), str(event_day + timedelta(days=35)))
    fmt = lambda c: ee.List(c.aggregate_array("system:time_start")).map(
        lambda t: ee.Date(t).format("YYYY-MM-dd")).distinct().getInfo()
    orbits = post.aggregate_array("orbitProperties_pass").distinct().getInfo()
    return {"radar_after": fmt(post), "radar_before": fmt(pre), "optical_after": fmt(opt), "orbits": orbits}


def damage_image(region_geojson: dict, event_day: date):
    """Per-pixel layers: crop (1), flooded (0/1), loss (0-1), damaged (0/1), all masked to cropland."""
    ee = init_ee()
    region = ee.Geometry(region_geojson)
    crop = ee.Image(ee.ImageCollection(WORLDCOVER).first()).eq(40)
    permanent = ee.Image(JRC).select("occurrence").unmask(0).gt(50)
    cropland = crop.And(permanent.Not())

    post_vv_col = _s1_vv(ee, region, str(event_day), str(event_day + timedelta(days=12)))
    orbit = ee.String(ee.Algorithms.If(post_vv_col.size().gt(0),
                                       post_vv_col.first().get("orbitProperties_pass"), "DESCENDING"))
    post_vv = _s1_vv(ee, region, str(event_day), str(event_day + timedelta(days=12)), orbit).min()
    base = ee.ImageCollection(ee.List([
        _s1_vv(ee, region, str(date(y, event_day.month, event_day.day) - timedelta(days=15)),
               str(date(y, event_day.month, event_day.day) + timedelta(days=15)), orbit)
        for y in BASELINE_YEARS]).iterate(lambda c, acc: ee.ImageCollection(acc).merge(c), ee.ImageCollection([])))
    mean, std = base.mean(), base.reduce(ee.Reducer.stdDev()).rename("VV").max(0.5)
    z = post_vv.subtract(mean).divide(std)
    flooded = z.lt(Z_FLOOD).And(post_vv.lt(VV_WATER_DB)).unmask(0)

    def ndvi_window(y):
        d = date(y, event_day.month, event_day.day)
        return _s2_ndvi(ee, region, str(d + timedelta(days=7)), str(d + timedelta(days=35))).median()

    post_ndvi = ndvi_window(event_day.year)
    hist = ee.ImageCollection([ndvi_window(y) for y in BASELINE_YEARS])
    norm_ndvi, spread = hist.median(), hist.reduce(ee.Reducer.stdDev()).max(0.03)
    loss = norm_ndvi.subtract(post_ndvi).divide(norm_ndvi.max(0.2)).clamp(0, 1)
    unusual = post_ndvi.subtract(hist.mean()).divide(spread).lt(Z_LOSS)
    damaged = flooded.Or(loss.gte(MODERATE_LOSS).And(unusual).unmask(0))
    severe = flooded.Or(loss.gte(SEVERE_LOSS).And(unusual).unmask(0))
    img = ee.Image.cat([ee.Image(1).rename("crop"), flooded.rename("flooded"), loss.rename("loss"),
                        damaged.rename("damaged"), severe.rename("severe"), post_ndvi.rename("ndvi_post"),
                        norm_ndvi.rename("ndvi_normal")])
    return img.updateMask(cropland).clip(region), cropland


def assess(fc, region_geojson: dict, event_day: date, scale: float = 20) -> dict[str, dict]:
    """Per-feature crop area, flooded share, NDVI loss and damaged share."""
    ee = init_ee()
    img, cropland = damage_image(region_geojson, event_day)
    px_ha = ee.Image.pixelArea().divide(1e4)
    area = ee.Image.cat([img.select(b).unmask(0).multiply(px_ha).updateMask(cropland).rename(f"{b}_ha")
                         for b in ("crop", "flooded", "damaged", "severe")])
    sums = reduce_table(area, fc, scale, ee.Reducer.sum())
    means = reduce_table(img.select(["loss", "ndvi_post", "ndvi_normal"]), fc, scale, ee.Reducer.mean())
    out = {}
    for uid, s in sums.items():
        m = means.get(uid, {})
        crop_ha = s.get("crop_ha") or 0
        share = lambda k: round(s.get(k, 0) / crop_ha * 100, 1) if crop_ha > 0.5 else None
        damaged = share("damaged_ha")
        out[uid] = {
            "crop_ha": round(crop_ha, 1),
            "flooded_pct": share("flooded_ha"),
            "damaged_pct": damaged,
            "severe_pct": share("severe_ha"),
            "damaged_ha": round(s.get("damaged_ha", 0), 1),
            "ndvi_loss_pct": None if m.get("loss") is None else round(m["loss"] * 100, 1),
            "ndvi_after": None if m.get("ndvi_post") is None else round(m["ndvi_post"], 3),
            "ndvi_normal": None if m.get("ndvi_normal") is None else round(m["ndvi_normal"], 3),
            "verify_first": (damaged is not None and damaged >= LIKELY_RELIEF_SHARE)
                            or (share("flooded_ha") or 0) >= FLOODED_SHARE,
        }
    return out
