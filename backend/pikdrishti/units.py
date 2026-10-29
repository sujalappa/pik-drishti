"""Administrative units: talukas of Maharashtra and the villages inside each taluka."""

from __future__ import annotations

import json
import re
from functools import lru_cache

from shapely.geometry import mapping, shape
from shapely.ops import unary_union

from .config import settings

UNIT_ID_RE = re.compile(r"^[a-z0-9-]{3,80}$")
BOUNDARY_SOURCE = {
    "key": "boundaries", "dataset": "Indian Village Boundaries, Maharashtra (Census 2001 villages)",
    "provider": "DataMeet community", "source": "github.com/datameet/indian_village_boundaries",
    "license": "ODbL 1.0",
    "used_for": "Village boundaries; talukas and districts are built by merging villages. Some taluka names and "
                "boundaries have changed since 2001.",
}


@lru_cache(maxsize=1)
def talukas() -> dict:
    return json.loads((settings.boundaries_dir / "talukas.geojson").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def districts() -> dict:
    return json.loads((settings.boundaries_dir / "districts.geojson").read_text(encoding="utf-8"))


def taluka(unit_id: str) -> dict | None:
    return next((f for f in talukas()["features"] if f["properties"]["id"] == unit_id), None)


def villages(taluka_id: str) -> dict:
    if not UNIT_ID_RE.fullmatch(taluka_id):
        raise KeyError(taluka_id)
    path = settings.boundaries_dir / "villages" / f"{taluka_id}.geojson"
    if not path.exists():
        raise KeyError(taluka_id)
    return json.loads(path.read_text(encoding="utf-8"))


def region_of(fc: dict, simplify: float = 0.002) -> dict:
    """One simplified outline around all features (for Earth Engine regions)."""
    geom = unary_union([shape(f["geometry"]) for f in fc["features"]]).simplify(simplify).buffer(simplify)
    return mapping(geom)


def bounds_of(fc: dict) -> tuple[float, float, float, float]:
    return unary_union([shape(f["geometry"]) for f in fc["features"]]).bounds
