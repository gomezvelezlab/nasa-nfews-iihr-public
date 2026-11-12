"""
Watershed boundaries from USGS web services.

Two public APIs, no key and no account:

  NLDI  https://api.water.usgs.gov/nldi/linked-data/...
        The Network Linked Data Index. Give it a monitoring site and it walks
        the NHDPlus river network for you: upstream basin polygon, upstream
        and downstream flowlines, other sites on the same network.

  NWIS  https://waterservices.usgs.gov/nwis/site/
        The site file: name, coordinates, drainage area, HUC code.

The basin polygon returned by NLDI is the same one drawn on a USGS monitoring
location page, so what participants get here is what they would see online.
"""
from __future__ import annotations

import json
from typing import Any

import requests

NLDI = "https://api.water.usgs.gov/nldi/linked-data"
NWIS = "https://waterservices.usgs.gov/nwis"
TIMEOUT = 60


def _site(site_id: str) -> str:
    """Accept '05451210' or 'USGS-05451210' and return the NLDI form."""
    site_id = str(site_id).strip()
    return site_id if site_id.startswith("USGS-") else f"USGS-{site_id}"


def site_info(site_id: str) -> dict[str, Any]:
    """Name, coordinates, drainage area and HUC for a USGS monitoring site."""
    bare = _site(site_id).replace("USGS-", "")
    r = requests.get(f"{NWIS}/site/", timeout=TIMEOUT,
                     params={"format": "rdb", "sites": bare,
                             "siteOutput": "expanded"})
    r.raise_for_status()
    lines = [ln for ln in r.text.splitlines() if ln and not ln.startswith("#")]
    if len(lines) < 3:
        raise ValueError(f"No NWIS site record for {site_id}")
    row = dict(zip(lines[0].split("\t"), lines[2].split("\t")))
    drain_sqmi = row.get("drain_area_va", "").strip()
    return {
        "site_id": _site(site_id),
        "name": row.get("station_nm", "").strip(),
        "lon": float(row["dec_long_va"]),
        "lat": float(row["dec_lat_va"]),
        "huc": row.get("huc_cd", "").strip(),
        "state": row.get("state_cd", "").strip(),
        "drain_area_sqmi": float(drain_sqmi) if drain_sqmi else None,
        "drain_area_km2": round(float(drain_sqmi) * 2.58999, 1)
        if drain_sqmi else None,
    }


def basin_polygon(site_id: str, simplified: bool = False) -> dict[str, Any]:
    """Upstream basin for a site, as a GeoJSON geometry in EPSG:4326."""
    r = requests.get(f"{NLDI}/nwissite/{_site(site_id)}/basin", timeout=TIMEOUT,
                     params={"simplified": str(simplified).lower()})
    r.raise_for_status()
    feats = r.json().get("features", [])
    if not feats:
        raise ValueError(f"NLDI returned no basin for {site_id}. Not every "
                         "site is indexed on the river network.")
    return feats[0]["geometry"]


def upstream_flowlines(site_id: str, distance_km: float = 200) -> dict[str, Any]:
    """River network upstream of the site (GeoJSON FeatureCollection)."""
    r = requests.get(
        f"{NLDI}/nwissite/{_site(site_id)}/navigation/UT/flowlines",
        params={"distance": distance_km}, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def upstream_sites(site_id: str, distance_km: float = 200) -> dict[str, Any]:
    """Other USGS monitoring sites upstream of this one."""
    r = requests.get(
        f"{NLDI}/nwissite/{_site(site_id)}/navigation/UT/nwissite",
        params={"distance": distance_km}, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def sites_in_bbox(west: float, south: float, east: float, north: float,
                  has_discharge: bool = True) -> list[dict[str, Any]]:
    """Stream gauges inside a lon/lat box. Handy for picking your own basin."""
    params = {"format": "rdb", "bBox": f"{west},{south},{east},{north}",
              "siteType": "ST", "siteStatus": "active",
              "siteOutput": "expanded"}
    if has_discharge:
        params["parameterCd"] = "00060"
        params["hasDataTypeCd"] = "dv"
    r = requests.get(f"{NWIS}/site/", params=params, timeout=TIMEOUT)
    r.raise_for_status()
    lines = [ln for ln in r.text.splitlines() if ln and not ln.startswith("#")]
    if len(lines) < 3:
        return []
    hdr = lines[0].split("\t")
    out = []
    for ln in lines[2:]:
        row = dict(zip(hdr, ln.split("\t")))
        da = row.get("drain_area_va", "").strip()
        out.append({"site_id": f"USGS-{row['site_no']}",
                    "name": row.get("station_nm", "").strip(),
                    "lon": float(row["dec_long_va"]),
                    "lat": float(row["dec_lat_va"]),
                    "drain_area_km2": round(float(da) * 2.58999, 1)
                    if da else None})
    return out


# ----------------------------------------------------------------- geometry --
def geom_bbox(geom: dict[str, Any]) -> tuple[float, float, float, float]:
    """(west, south, east, north) of a GeoJSON Polygon or MultiPolygon."""
    rings = (geom["coordinates"] if geom["type"] == "Polygon"
             else [r for poly in geom["coordinates"] for r in poly])
    pts = [p for ring in rings for p in ring]
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def area_km2(geom: dict[str, Any], crs: str = "EPSG:5070") -> float:
    """Area of a lon/lat geometry, measured in an equal-area projection."""
    from rasterio.warp import transform_geom
    from shapely.geometry import shape
    return round(shape(transform_geom("EPSG:4326", crs, geom)).area / 1e6, 1)


def subset_bbox(geom: dict[str, Any], width_km: float,
                center: tuple[float, float] | None = None
                ) -> tuple[float, float, float, float]:
    """A square lon/lat box of a given width, for keeping demo runs small.

    Centered on the basin centroid unless a (lon, lat) center is given.
    """
    import math
    from shapely.geometry import shape
    if center is None:
        c = shape(geom).centroid
        clon, clat = c.x, c.y
    else:
        clon, clat = center
    dlat = width_km / 111.0 / 2
    dlon = width_km / (111.0 * math.cos(math.radians(clat))) / 2
    return clon - dlon, clat - dlat, clon + dlon, clat + dlat


def save_geojson(geom: dict[str, Any], path, properties: dict | None = None):
    """Write a geometry as a one-feature GeoJSON file."""
    fc = {"type": "FeatureCollection",
          "features": [{"type": "Feature",
                        "properties": properties or {},
                        "geometry": geom}]}
    with open(path, "w") as f:
        json.dump(fc, f)
    return path


def load_geojson(path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Read back a file written by save_geojson. Returns (geometry, props)."""
    with open(path) as f:
        fc = json.load(f)
    feat = fc["features"][0] if fc.get("type") == "FeatureCollection" else fc
    return feat["geometry"], feat.get("properties", {})


_WGS84_PRJ = ('GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",'
              '6378137.0,298.257223563]],PRIMEM["Greenwich",0.0],'
              'UNIT["Degree",0.0174532925199433]]')


def save_shapefile_zip(geom: dict[str, Any], out_zip, properties: dict | None = None,
                       layer: str = "watershed"):
    """Write a basin polygon as a zipped shapefile (WGS84 lon/lat).

    Google Earth Engine, QGIS and ArcGIS all accept a zipped shapefile, and
    Earth Engine in particular cannot ingest GeoJSON through the Code Editor.
    The zip holds the four parts every shapefile needs: .shp (geometry),
    .shx (index), .dbf (attributes) and .prj (coordinate system).
    """
    import io
    import zipfile
    from pathlib import Path

    import shapefile                       # the pyshp package
    from shapely.geometry import shape
    from shapely.geometry.polygon import orient

    g = shape(geom)
    polys = [g] if g.geom_type == "Polygon" else list(g.geoms)
    parts = []
    for poly in polys:
        poly = orient(poly, sign=-1.0)     # shapefile outer rings run clockwise
        parts.append([list(map(float, xy[:2])) for xy in poly.exterior.coords])
        for ring in poly.interiors:
            parts.append([list(map(float, xy[:2])) for xy in ring.coords])

    props = properties or {}
    shp, shx, dbf = io.BytesIO(), io.BytesIO(), io.BytesIO()
    w = shapefile.Writer(shp=shp, shx=shx, dbf=dbf, shapeType=shapefile.POLYGON)
    w.field("name", "C", size=80)
    w.field("site_id", "C", size=20)
    w.field("area_km2", "N", size=12, decimal=1)
    w.field("drain_km2", "N", size=12, decimal=1)
    w.field("source", "C", size=60)
    w.poly(parts)
    w.record(str(props.get("name", ""))[:80],
             str(props.get("site_id", ""))[:20],
             round(float(props.get("polygon_km2") or area_km2(geom)), 1),
             round(float(props.get("drain_area_km2") or 0.0), 1),
             "USGS NLDI basin, WGS84")
    w.close()

    out_zip = Path(out_zip)
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"{layer}.shp", shp.getvalue())
        z.writestr(f"{layer}.shx", shx.getvalue())
        z.writestr(f"{layer}.dbf", dbf.getvalue())
        z.writestr(f"{layer}.prj", _WGS84_PRJ)
        z.writestr(f"{layer}.cpg", "UTF-8")
    return out_zip
