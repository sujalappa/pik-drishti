"""Drought and crop-damage assessments as jobs with visible stages, events, maps and exports."""

from __future__ import annotations

import json
import traceback
from datetime import date

from . import damage, drought, report, units
from .earthengine import EEError, feature_collection, init_ee
from .exports import write_csv, write_geojson, write_kml
from .jobs import Job
from .layers import DEV_PALETTE, save_png

DROUGHT_STAGES = [
    {"id": "data", "name": "Latest satellite data", "description": "Newest rainfall, vegetation and evapotranspiration dates"},
    {"id": "trigger1", "name": "Trigger-1: rainfall", "description": "Seasonal deficit and dry spells (CHIRPS)"},
    {"id": "trigger2", "name": "Trigger-2: crop impact", "description": "Crop condition, moisture and cropped area (MODIS)"},
    {"id": "maps", "name": "Maps", "description": "Rainfall and crop-condition layers"},
    {"id": "outputs", "name": "Report and exports", "description": "PDF, CSV, GeoJSON and KML"},
]
DAMAGE_STAGES = [
    {"id": "data", "name": "Satellite passes", "description": "Radar and optical images around the event"},
    {"id": "damage", "name": "Flooding and crop loss", "description": "Sentinel-1 radar and Sentinel-2 crop condition"},
    {"id": "maps", "name": "Maps", "description": "Flooded and damaged cropland"},
    {"id": "outputs", "name": "Report and exports", "description": "Verification list, PDF, CSV and KML"},
]

DROUGHT_COLUMNS = [
    ("name", "Unit"), ("district", "District"), ("category", "Drought category"), ("trigger_1", "Trigger-1"),
    ("rain_mm", "Rain (mm)"), ("rain_normal_mm", "Normal (mm)"), ("rain_dev_pct", "Rain deviation %"),
    ("dry_spell_weeks", "Longest dry spell (weeks)"), ("dry_spell_from", "Dry spell from"),
    ("ndvi_dev_pct", "NDVI deviation %"), ("ndwi_dev_pct", "NDWI deviation %"), ("vci", "VCI"),
    ("remote_sensing_class", "Remote sensing"), ("mai_of_normal_pct", "MAI % of normal"),
    ("soil_moisture_class", "Soil moisture"), ("cropped_area_dev_pct", "Cropped area deviation %"),
    ("agriculture_class", "Agriculture"),
]
DAMAGE_COLUMNS = [
    ("name", "Village"), ("crop_ha", "Crop area (ha)"), ("flooded_pct", "Flooded %"), ("damaged_pct", "Damaged %"),
    ("damaged_ha", "Damaged (ha)"), ("severe_pct", "Severe %"), ("ndvi_loss_pct", "NDVI loss %"),
    ("verify_first", "Verify first"),
]
CATEGORY_KML = {"severe": "c80000c0", "moderate": "c80080ff", "normal": "9600b4ff", "no trigger": "5050a050",
                "insufficient data": "50999999"}


def _fail(job: Job, exc: Exception) -> None:
    stage = job.state.get("current_stage")
    msg = str(exc) if isinstance(exc, (EEError, ValueError, KeyError)) else f"{type(exc).__name__}: {exc}"
    job.event("error", "JOB_FAILED", msg, action="Try again; if it repeats, check the Earth Engine login",
              data={"trace": traceback.format_exc()[-2000:]})
    if stage:
        job.fail_stage(stage, msg)
    job.set_status("failed")


def _names(fc: dict, name_key: str) -> dict:
    return {f["properties"]["id"]: f["properties"] for f in fc["features"]}


# ---------------------------------------------------------------- drought
def run_drought_job(job: Job) -> None:
    try:
        opts = job.state["options"]
        scope = opts["scope"]
        if scope == "state":
            fc, unit_kind, name_key = units.talukas(), "taluka", "taluka"
            rain_scale, veg_scale = 5566, 500
        else:
            fc, unit_kind, name_key = units.villages(scope), "village", "village"
            rain_scale, veg_scale = 1000, 250
        bounds = units.bounds_of(fc)
        props = _names(fc, name_key)

        job.start_stage("data")
        ee = init_ee()
        season = drought.kharif_season(int(opts["year"]))
        job.update("season", season.as_dict())
        for s in (*drought.SOURCES, units.BOUNDARY_SOURCE):
            job.add_provenance(s)
        job.finish_stage("data", f"Rainfall to {season.rain_end}, vegetation to {season.veg_end}, "
                                 f"evapotranspiration to {season.et_end}", season.as_dict())

        job.start_stage("trigger1")
        efc = feature_collection(ee, fc)
        rain_rows, n_weeks = drought.rain_table(efc, season, rain_scale)
        partial = {u: drought.classify(r, season, n_weeks) for u, r in rain_rows.items()}
        t1 = sum(r["trigger_1"] for r in partial.values())
        job.finish_stage("trigger1", f"Trigger-1 met in {t1} of {len(partial)} {unit_kind}s",
                         {"trigger_1": t1, "units": len(partial)})

        job.start_stage("trigger2")
        veg_rows = drought.impact_table(efc, season, veg_scale)
        results = {u: drought.classify({**rain_rows[u], **veg_rows.get(u, {})}, season, n_weeks) for u in rain_rows}
        for u, r in results.items():
            p = props[u]
            r.update(name=p[name_key], district=p["district"], taluka=p.get("taluka"))
        counts = {c: sum(r["category"] == c for r in results.values())
                  for c in ("severe", "moderate", "normal", "no trigger", "insufficient data")}
        job.finish_stage("trigger2", f"{counts['severe']} severe, {counts['moderate']} moderate, "
                                     f"{counts['normal']} normal among Trigger-1 {unit_kind}s", counts)
        (job.path("results.json")).write_text(json.dumps(results), encoding="utf-8")
        (job.path("units.geojson")).write_text(json.dumps(fc), encoding="utf-8")
        job.set_layer("units", "units.geojson", f"{unit_kind.capitalize()} boundaries")
        devs = [r["rain_dev_pct"] for r in results.values() if r["rain_dev_pct"] is not None]
        job.update("summary", {
            "kind": "drought", "unit": unit_kind, "units": len(results), "trigger_1": t1, "counts": counts,
            "mean_rain_dev_pct": round(sum(devs) / len(devs), 1) if devs else None, "season": season.as_dict(),
            "method": drought.METHOD,
        })

        job.start_stage("maps")
        try:
            c = save_png(drought.rain_deviation_image(season), bounds, job.path("rain_dev.png"),
                         {"min": -60, "max": 60, "palette": DEV_PALETTE})
            job.set_raster("rain_dev", "rain_dev.png", c, "Rainfall deviation from normal (CHIRPS)",
                           {"type": "continuous", "min": -60, "max": 60, "unit": "%", "palette": DEV_PALETTE})
            c = save_png(drought.ndvi_deviation_image(season), bounds, job.path("ndvi_dev.png"),
                         {"min": -40, "max": 40, "palette": DEV_PALETTE})
            job.set_raster("ndvi_dev", "ndvi_dev.png", c, "Crop NDVI deviation, latest 3 weeks (MODIS)",
                           {"type": "continuous", "min": -40, "max": 40, "unit": "%", "palette": DEV_PALETTE})
            job.finish_stage("maps", "Rainfall and crop-condition layers")
        except Exception as exc:  # maps are optional; the table is the result
            job.event("warning", "MAPS_FAILED", f"Map layers could not be rendered: {exc}",
                      action="Results and exports are unaffected")
            job.skip_stage("maps", "Map layers unavailable")

        job.start_stage("outputs")
        rows = sorted(results.values(), key=lambda r: (["severe", "moderate", "normal", "no trigger",
                                                         "insufficient data"].index(r["category"]),
                                                        r["rain_dev_pct"] if r["rain_dev_pct"] is not None else 0))
        write_csv(job.path("drought.csv"), rows, DROUGHT_COLUMNS)
        write_geojson(job.path("drought.geojson"), fc, results)
        write_kml(job.path("drought.kml"), fc, results, name_key, DROUGHT_COLUMNS,
                  lambda r: CATEGORY_KML.get(r["category"], "50999999"))
        where = "Maharashtra" if scope == "state" else f"{fc['features'][0]['properties']['taluka']} taluka"
        report.build(
            job.path("drought_report.pdf"), f"Kharif {season.year} drought assessment: {where}",
            f"Pik-drishti AI · data to {season.veg_end} · following the Manual for Drought Management (2016)",
            [("Units assessed", f"{len(results)} {unit_kind}s"), ("Trigger-1 met", t1),
             ("Severe / moderate (Trigger-2)", f"{counts['severe']} / {counts['moderate']}"),
             ("Rainfall window", f"{season.rain_start} to {season.rain_end}"),
             ("Crop-condition window", f"{season.rs_start} to {season.veg_end}")],
            drought.METHOD, job.state["provenance"], DROUGHT_COLUMNS[:12], rows[:60],
            "A satellite screening to support Steps 1-2 of the manual. The final category is decided after field "
            "verification (Step 3) by the State.")
        for fmt, f, label in (("pdf", "drought_report.pdf", "PDF report"), ("csv", "drought.csv", "Table (CSV)"),
                              ("geojson", "drought.geojson", "Map data (GeoJSON)"),
                              ("kml", "drought.kml", "Google Earth (KML)")):
            job.set_export(fmt, f, label)
        job.finish_stage("outputs", "PDF, CSV, GeoJSON and KML ready")
        job.set_status("completed")
    except Exception as exc:
        _fail(job, exc)


# ---------------------------------------------------------------- crop damage
def run_damage_job(job: Job) -> None:
    try:
        opts = job.state["options"]
        fc = units.villages(opts["taluka"])
        event_day = date.fromisoformat(opts["event_date"])
        region = units.region_of(fc)
        bounds = units.bounds_of(fc)
        props = _names(fc, "village")

        job.start_stage("data")
        ee = init_ee()
        for s in (*damage.SOURCES, units.BOUNDARY_SOURCE):
            job.add_provenance(s)
        info = damage.event_info(region, event_day)
        job.update("acquisitions", info)
        if not info["radar_after"]:
            job.event("warning", "NO_RADAR", "No Sentinel-1 pass within 12 days after the event",
                      action="Flooding is not mapped; crop loss uses Sentinel-2 only")
        if not info["optical_after"]:
            job.event("warning", "NO_OPTICAL", "No cloud-free Sentinel-2 image 1-5 weeks after the event",
                      action="Crop loss is not measured; flooding uses radar only")
        job.finish_stage("data", f"Radar after: {', '.join(info['radar_after']) or 'none'}; optical after: "
                                 f"{len(info['optical_after'])} dates", info)

        job.start_stage("damage")
        results = damage.assess(feature_collection(ee, fc), region, event_day)
        for u, r in results.items():
            p = props[u]
            r.update(name=p["village"], taluka=p["taluka"], district=p["district"])
        crop = sum(r["crop_ha"] for r in results.values())
        dmg = sum(r["damaged_ha"] for r in results.values())
        flagged = sum(r["verify_first"] for r in results.values())
        job.finish_stage("damage", f"{dmg:,.0f} ha of {crop:,.0f} ha cropland damaged; {flagged} villages to verify "
                                   "first", {"crop_ha": round(crop), "damaged_ha": round(dmg), "verify_first": flagged})
        job.path("results.json").write_text(json.dumps(results), encoding="utf-8")
        job.path("units.geojson").write_text(json.dumps(fc), encoding="utf-8")
        job.set_layer("units", "units.geojson", "Village boundaries")
        job.update("summary", {
            "kind": "damage", "unit": "village", "units": len(results), "crop_ha": round(crop),
            "damaged_ha": round(dmg), "damaged_pct": round(dmg / crop * 100, 1) if crop else None,
            "verify_first": flagged, "event_date": str(event_day), "method": damage.METHOD,
            "taluka": fc["features"][0]["properties"]["taluka"], "district": fc["features"][0]["properties"]["district"],
        })

        job.start_stage("maps")
        try:
            img, _ = damage.damage_image(region, event_day)
            layer = (img.select("flooded").multiply(3).max(img.select("severe").multiply(2))
                     .max(img.select("damaged")).selfMask())
            c = save_png(layer, bounds, job.path("damage.png"),
                         {"min": 1, "max": 3, "palette": ["f2b134", "c0392b", "1f6fd1"]}, 1600)
            job.set_raster("damage", "damage.png", c, "Damaged and flooded cropland (Sentinel-1, Sentinel-2)",
                           {"type": "categorical", "items": [{"label": "Moderate crop loss", "color": "#f2b134"},
                                                             {"label": "Severe crop loss", "color": "#c0392b"},
                                                             {"label": "Flooded", "color": "#1f6fd1"}]})
            job.finish_stage("maps", "Damage layer ready")
        except Exception as exc:
            job.event("warning", "MAPS_FAILED", f"Map layer could not be rendered: {exc}",
                      action="Results and exports are unaffected")
            job.skip_stage("maps", "Map layer unavailable")

        job.start_stage("outputs")
        rows = sorted(results.values(), key=lambda r: (not r["verify_first"], -(r["damaged_ha"] or 0)))
        write_csv(job.path("verification_list.csv"), rows, DAMAGE_COLUMNS)
        write_geojson(job.path("damage.geojson"), fc, results)
        write_kml(job.path("damage.kml"), fc, results, "village", DAMAGE_COLUMNS,
                  lambda r: "c80000c0" if r["verify_first"] else "9600b4ff" if (r["damaged_pct"] or 0) >= 15
                  else "5050a050")
        s = job.state["summary"]
        report.build(
            job.path("damage_report.pdf"), f"Crop damage after {event_day:%d %b %Y}: {s['taluka']} taluka, "
                                           f"{s['district']}",
            "Pik-drishti AI · satellite screening for panchanama field verification",
            [("Villages", len(results)), ("Cropland", f"{crop:,.0f} ha"),
             ("Damaged cropland", f"{dmg:,.0f} ha ({s['damaged_pct']}%)"), ("Villages to verify first", flagged),
             ("Radar passes after the event", ", ".join(info["radar_after"]) or "none"),
             ("Optical images after the event", ", ".join(info["optical_after"][:8]) or "none")],
            damage.METHOD, job.state["provenance"], DAMAGE_COLUMNS, rows[:80],
            "Officials still verify and sign the panchanama; this list tells them where to go first.")
        for fmt, f, label in (("pdf", "damage_report.pdf", "PDF report"),
                              ("csv", "verification_list.csv", "Verification list (CSV)"),
                              ("geojson", "damage.geojson", "Map data (GeoJSON)"), ("kml", "damage.kml", "Google Earth (KML)")):
            job.set_export(fmt, f, label)
        job.finish_stage("outputs", "Verification list, PDF, CSV, GeoJSON and KML ready")
        job.set_status("completed")
    except Exception as exc:
        _fail(job, exc)
