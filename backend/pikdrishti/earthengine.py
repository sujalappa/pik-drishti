"""Earth Engine login and small helpers shared by the drought and crop-damage analyses."""

from __future__ import annotations

import json
import os
import threading

from .config import settings

_lock = threading.Lock()
_ready = False


class EEError(RuntimeError):
    pass


def init_ee():
    """Log in once per process: a service-account key (hosted) or the machine's own login (local)."""
    global _ready
    import ee

    with _lock:
        if _ready:
            return ee
        if not settings.gee_project:
            raise EEError("GEE_PROJECT is not set. Add it to .env (see .env.example)")
        try:
            key = os.environ.get("GEE_SERVICE_ACCOUNT_KEY", "").strip()
            if key:
                creds = ee.ServiceAccountCredentials(json.loads(key)["client_email"], key_data=key)
                ee.Initialize(creds, project=settings.gee_project)
            else:
                ee.Initialize(project=settings.gee_project)
        except Exception as exc:
            raise EEError(f"Earth Engine login failed ({exc}). Run 'earthengine authenticate' on this machine, "
                          "or set GEE_SERVICE_ACCOUNT_KEY") from exc
        _ready = True
    return ee


def feature_collection(ee, geojson: dict, keep: tuple[str, ...] = ("id",)):
    """GeoJSON FeatureCollection -> ee.FeatureCollection, keeping only the listed properties."""
    feats = [ee.Feature(ee.Geometry(f["geometry"], None, False), {k: f["properties"].get(k) for k in keep})
             for f in geojson["features"]]
    return ee.FeatureCollection(feats)


def latest_date(ee, collection_id: str, region, since: str) -> str | None:
    col = ee.ImageCollection(collection_id).filterBounds(region).filterDate(since, "2100-01-01")
    if col.size().getInfo() == 0:
        return None
    return ee.Date(col.aggregate_max("system:time_start")).format("YYYY-MM-dd").getInfo()


def reduce_table(image, fc, scale: float, reducer=None, tile_scale: int = 4) -> dict[str, dict]:
    """Mean of every band of `image` inside each feature -> {feature id: {band: value}}."""
    import ee

    stats = image.reduceRegions(collection=fc, reducer=reducer or ee.Reducer.mean(), scale=scale,
                                tileScale=tile_scale)
    out = {}
    for f in stats.getInfo()["features"]:
        props = dict(f["properties"])
        out[props.pop("id")] = props
    return out
