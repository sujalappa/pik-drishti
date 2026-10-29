"""Map overlays rendered by Earth Engine as PNG images with known corners."""

from __future__ import annotations

import urllib.request
from pathlib import Path

from .earthengine import init_ee

DEV_PALETTE = ["8c510a", "d8b365", "f6e8c3", "f5f5f5", "c7eae5", "5ab4ac", "01665e"]   # dry brown -> wet teal


def corners(bounds) -> list[list[float]]:
    w, s, e, n = bounds
    return [[w, n], [e, n], [e, s], [w, s]]


def save_png(image, bounds, path: Path, vis: dict, dimensions: int = 1400) -> list[list[float]]:
    """Render `image` with `vis` over `bounds` (lon/lat) to `path`; returns MapLibre image corners."""
    ee = init_ee()
    w, s, e, n = bounds
    rect = ee.Geometry.Rectangle([w, s, e, n], None, False)
    url = image.visualize(**vis).getThumbURL({"region": rect, "dimensions": dimensions, "format": "png",
                                              "crs": "EPSG:4326"})
    with urllib.request.urlopen(url, timeout=300) as r:
        path.write_bytes(r.read())
    return corners(bounds)
