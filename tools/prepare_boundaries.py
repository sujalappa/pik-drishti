"""Build taluka, district and per-taluka village boundaries for Maharashtra.

Source: DataMeet Indian Village Boundaries (Census 2001 villages, ODbL)
https://github.com/datameet/indian_village_boundaries  (files mh1.geojson, mh2.geojson)

Run:  python tools/prepare_boundaries.py
Writes data/boundaries/{talukas,districts}.geojson and data/boundaries/villages/<taluka_id>.geojson.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

from shapely.geometry import mapping, shape
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "boundaries" / "raw"
OUT = ROOT / "data" / "boundaries"

# Census-2001 district names in the source -> names in use today.
DISTRICT_NAMES = {
    "Ahmadnagar": "Ahilyanagar",
    "Aurangabad": "Chhatrapati Sambhajinagar",
    "Osmanabad": "Dharashiv",
    "Nasik": "Nashik",
    "Mumbai (Suburban)": "Mumbai Suburban",
}
TALUKA_TOLERANCE = 0.0015  # degrees, ~150 m
VILLAGE_TOLERANCE = 0.0002  # ~20 m


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def rounded(geom, ndigits=5):
    """GeoJSON mapping with coordinates rounded to ~1 m to keep files small."""
    def rnd(c):
        if isinstance(c[0], (int, float)):
            return [round(c[0], ndigits), round(c[1], ndigits)]
        return [rnd(x) for x in c]
    m = mapping(geom)
    return {"type": m["type"], "coordinates": rnd(m["coordinates"])}


def main() -> None:
    villages = defaultdict(list)
    for name in ("mh1.geojson", "mh2.geojson"):
        for ft in json.load(open(RAW / name, encoding="utf-8"))["features"]:
            p = ft["properties"]
            district = DISTRICT_NAMES.get(p["DISTRICT"], p["DISTRICT"])
            geom = shape(ft["geometry"])
            if not geom.is_valid:
                geom = geom.buffer(0)
            if geom.is_empty:
                continue
            villages[(district, p["SUB_DIST"])].append((p["NAME"], p["CEN_2001"], geom))

    (OUT / "villages").mkdir(parents=True, exist_ok=True)
    talukas, district_geoms = [], defaultdict(list)
    for (district, taluka), items in sorted(villages.items()):
        tid = f"{slug(district)}--{slug(taluka)}"
        union = unary_union([g for _, _, g in items])
        district_geoms[district].append(union)
        talukas.append({"type": "Feature", "properties": {
            "id": tid, "taluka": taluka, "district": district, "villages": len(items),
            "area_km2": round(union.area * 111.32 ** 2 * 0.95, 1)},  # rough, for display only
            "geometry": rounded(union.simplify(TALUKA_TOLERANCE, preserve_topology=True), 4)})
        vfeats = [{"type": "Feature", "properties": {
            "id": code, "village": vname, "taluka": taluka, "district": district},
            "geometry": rounded(g.simplify(VILLAGE_TOLERANCE, preserve_topology=True))}
            for vname, code, g in sorted(items, key=lambda t: t[0])]
        (OUT / "villages" / f"{tid}.geojson").write_text(
            json.dumps({"type": "FeatureCollection", "features": vfeats}), encoding="utf-8")

    districts = [{"type": "Feature", "properties": {"id": slug(d), "district": d},
                  "geometry": rounded(unary_union(gs).simplify(TALUKA_TOLERANCE * 2, preserve_topology=True), 4)}
                 for d, gs in sorted(district_geoms.items())]
    for name, feats in (("talukas", talukas), ("districts", districts)):
        (OUT / f"{name}.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": feats}),
                                            encoding="utf-8")
    print(f"{sum(len(v) for v in villages.values())} villages, {len(talukas)} talukas, {len(districts)} districts")


if __name__ == "__main__":
    main()
