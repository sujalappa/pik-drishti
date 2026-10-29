"""CSV, GeoJSON and KML exports of per-unit results."""

from __future__ import annotations

import csv
import io
import json
from xml.sax.saxutils import escape

from shapely.geometry import shape


def _flat(value):
    if isinstance(value, list):
        return " ".join("" if v is None else str(v) for v in value)
    return "" if value is None else value


def write_csv(path, rows: list[dict], columns: list[tuple[str, str]]) -> None:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow([label for _, label in columns])
    for r in rows:
        w.writerow([_flat(r.get(k)) for k, _ in columns])
    path.write_text(buf.getvalue(), encoding="utf-8-sig")


def write_geojson(path, units: dict, results: dict) -> None:
    feats = [{**f, "properties": {**f["properties"], **results.get(f["properties"]["id"], {})}}
             for f in units["features"] if f["properties"]["id"] in results]
    path.write_text(json.dumps({"type": "FeatureCollection", "features": feats}), encoding="utf-8")


def write_kml(path, units: dict, results: dict, name_key: str, columns: list[tuple[str, str]],
              color_of) -> None:
    """KML for Google Earth and field teams; one placemark per unit, coloured by `color_of(result)` (aabbggrr)."""
    parts = ['<?xml version="1.0" encoding="UTF-8"?>', '<kml xmlns="http://www.opengis.net/kml/2.2"><Document>']
    for f in units["features"]:
        uid = f["properties"]["id"]
        if uid not in results:
            continue
        r = results[uid]
        rows = "".join(f"<tr><td>{escape(label)}</td><td>{escape(str(_flat(r.get(k))))}</td></tr>"
                       for k, label in columns)
        parts.append(f"<Placemark><name>{escape(str(f['properties'][name_key]))}</name>"
                     f"<description><![CDATA[<table>{rows}</table>]]></description>"
                     f"<Style><LineStyle><color>ff333333</color><width>1</width></LineStyle>"
                     f"<PolyStyle><color>{color_of(r)}</color></PolyStyle></Style>")
        geom = shape(f["geometry"])
        polys = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
        parts.append("<MultiGeometry>")
        for p in polys:
            coords = " ".join(f"{x:.5f},{y:.5f}" for x, y in p.exterior.coords)
            parts.append(f"<Polygon><outerBoundaryIs><LinearRing><coordinates>{coords}</coordinates>"
                         f"</LinearRing></outerBoundaryIs></Polygon>")
        parts.append("</MultiGeometry></Placemark>")
    parts.append("</Document></kml>")
    path.write_text("".join(parts), encoding="utf-8")
