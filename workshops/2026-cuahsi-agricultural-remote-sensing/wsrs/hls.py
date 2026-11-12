"""
Harmonized Landsat Sentinel-2 (HLS): search, cloud screening, download, stack.

HLS in one paragraph
--------------------
NASA takes Landsat 8/9 (L30) and Sentinel-2 (S30), corrects both to surface
reflectance, and resamples them onto one common 30 m grid with matching band
definitions. The result is a single analysis-ready archive with a 2 to 3 day
revisit. We use the S30 half, version 2.0, because the Prithvi crop model was
fine-tuned on it.

What the model wants
--------------------
Six bands, in this order, at three dates across one growing season:

    channel  band  name          wavelength
    1        B02   Blue          0.49 um
    2        B03   Green         0.56 um
    3        B04   Red           0.66 um
    4        B8A   Narrow NIR    0.865 um
    5        B11   SWIR 1        1.61 um
    6        B12   SWIR 2        2.19 um

Stacked in time order that is 18 bands. Reflectance is stored as integers
scaled by 10000, with -9999 for no data.

Two traps this module handles for you
-------------------------------------
1. CloudCover in the metadata describes the whole tile, and it ignores empty
   area. A granule can report 0 percent cloud while covering only part of the
   tile, because the Sentinel-2 swath clipped the corner. Always read
   SPATIAL_COVERAGE too.
2. Interrupted downloads leave files that are the right size but contain an
   HTML or JSON error page. Check the first two bytes for a TIFF signature.
"""
from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

S30_BANDS = ["B02", "B03", "B04", "B8A", "B11", "B12"]
L30_BANDS = ["B02", "B03", "B04", "B05", "B06", "B07"]
BAND_LABELS = ["Blue", "Green", "Red", "Narrow NIR", "SWIR 1", "SWIR 2"]
NODATA = -9999
RGB_IDX = (2, 1, 0)          # red, green, blue within one date
FALSE_COLOR_IDX = (3, 2, 1)  # NIR, red, green: vegetation glows

# Three windows spanning the US Midwest growing season. Early season is mostly
# bare soil, mid season is peak canopy, late season separates corn from
# soybean by how they senesce.
DEFAULT_WINDOWS = [("05-01", "05-31", "May"),
                   ("07-01", "07-31", "Jul"),
                   ("08-25", "09-25", "Sep")]


# --------------------------------------------------------------- searching --
def _attrs(granule) -> tuple[float, float]:
    """(cloud percent, spatial coverage percent) from granule metadata."""
    cloud, cov = 101.0, 100.0
    umm = granule["umm"]
    if "CloudCover" in umm:
        cloud = float(umm["CloudCover"])
    for a in umm.get("AdditionalAttributes", []):
        if a.get("Name") == "CLOUD_COVERAGE":
            cloud = float(a["Values"][0])
        elif a.get("Name") == "SPATIAL_COVERAGE":
            cov = float(a["Values"][0])
    return cloud, cov


def parse_name(name: str) -> tuple[str | None, str | None]:
    """'HLS.S30.T15TVG.2025130T165849.v2.0' -> ('T15TVG', '2025130')."""
    m = re.search(r"HLS\.[SL]30\.(T\w{5})\.(\d{7})T", name)
    return (m.group(1), m.group(2)) if m else (None, None)


def doy_to_date(doy: str) -> str:
    """'2025130' -> '2025-05-10'."""
    import datetime as dt
    return dt.datetime.strptime(doy, "%Y%j").strftime("%Y-%m-%d")


def search(bbox, start: str, end: str, product: str = "HLSS30",
           count: int = 500) -> list[dict[str, Any]]:
    """Every HLS granule touching bbox between two dates.

    Returns plain dicts so they are easy to put in a DataFrame and look at.
    Requires earthaccess.login() to have been called.
    """
    import earthaccess
    results = earthaccess.search_data(short_name=product, version="2.0",
                                      bounding_box=tuple(bbox),
                                      temporal=(start, end), count=count)
    out = []
    for g in results:
        name = g["umm"].get("GranuleUR", "")
        tile, doy = parse_name(name)
        if not tile:
            continue
        cloud, cov = _attrs(g)
        out.append({"name": name, "tile": tile, "doy": doy,
                    "date": doy_to_date(doy), "cloud_pct": cloud,
                    "coverage_pct": cov, "granule": g})
    return sorted(out, key=lambda r: (r["date"], r["tile"]))


def search_windows(bbox, year: int, windows=None, product="HLSS30"
                   ) -> dict[str, list[dict[str, Any]]]:
    """Run search() once per seasonal window. Keyed by window label."""
    windows = windows or DEFAULT_WINDOWS
    return {label: search(bbox, f"{year}-{a}", f"{year}-{b}", product)
            for a, b, label in windows}


def scene_table(found: dict[str, list[dict]]):
    """Searched granules as a tidy DataFrame, minus the heavy granule object."""
    import pandas as pd
    rows = []
    for label, recs in found.items():
        for r in recs:
            rows.append({"window": label, "date": r["date"], "tile": r["tile"],
                         "cloud_pct": r["cloud_pct"],
                         "coverage_pct": r["coverage_pct"],
                         "usable": r["cloud_pct"] <= 30 and
                         r["coverage_pct"] >= 90,
                         "name": r["name"]})
    return pd.DataFrame(rows)


def pick_scenes(found: dict[str, list[dict]], cloud_max: float = 30.0,
                coverage_min: float = 90.0, verbose: bool = True
                ) -> list[list[dict]]:
    """Choose what to download: per window, the best scene for each tile.

    Rules, in order:
      1. if one date is clear and complete on every tile, use that date for
         the whole area: one atmosphere and one day of the season, so the
         tiles join without a visible seam
      2. otherwise choose tile by tile: prefer granules that fill the tile
         (coverage >= coverage_min) and are below cloud_max, taking the
         clearest
      3. if none qualify, take the best available and warn
      4. if the chosen granule only partly covers the tile, add a second
         granule from a different date to fill the hole
    """
    all_tiles = sorted({r["tile"] for recs in found.values() for r in recs})
    picks = []
    for label, recs in found.items():
        by_tile = defaultdict(list)
        for r in recs:
            by_tile[r["tile"]].append(r)

        # Rule 1: one date for every tile.
        good = defaultdict(dict)
        for r in recs:
            if (r["coverage_pct"] >= coverage_min
                    and r["cloud_pct"] <= cloud_max):
                kept = good[r["date"]].get(r["tile"])
                if kept is None or r["cloud_pct"] < kept["cloud_pct"]:
                    good[r["date"]][r["tile"]] = r
        shared = {d: g for d, g in good.items() if len(g) == len(by_tile)}
        if len(by_tile) > 1 and shared:
            day = min(shared, key=lambda d: (
                max(g["cloud_pct"] for g in shared[d].values()), d))
            chosen = [shared[day][t] for t in sorted(by_tile)]
            if verbose:
                for r in chosen:
                    print(f"  [{label}] {r['tile']}: {r['date']} "
                          f"cloud {r['cloud_pct']:.0f}% "
                          f"cover {r['coverage_pct']:.0f}%")
                print(f"  [{label}] same date on all {len(chosen)} tiles")
            picks.append(chosen)
            continue

        # Rules 2 to 4: tile by tile.
        chosen = []
        for tile in all_tiles:
            cands = by_tile.get(tile)
            if not cands:
                if verbose:
                    print(f"  [{label}] {tile}: no granule at all")
                continue
            full = [c for c in cands if c["coverage_pct"] >= coverage_min]
            pool = [c for c in full if c["cloud_pct"] <= cloud_max] or full
            best = (min(pool, key=lambda c: c["cloud_pct"]) if pool else
                    max(cands, key=lambda c: (c["coverage_pct"],
                                              -c["cloud_pct"])))
            if verbose:
                flag = "" if best["cloud_pct"] <= cloud_max else "  <- cloudy"
                print(f"  [{label}] {tile}: {best['date']} "
                      f"cloud {best['cloud_pct']:.0f}% "
                      f"cover {best['coverage_pct']:.0f}%{flag}")
            chosen.append(best)
            if best["coverage_pct"] < coverage_min:
                rest = [c for c in cands if c["date"] != best["date"]
                        and c["coverage_pct"] >= 30]
                if rest:
                    fill = min(rest, key=lambda c: c["cloud_pct"])
                    chosen.append(fill)
                    if verbose:
                        print(f"            + fill from {fill['date']}")
        if verbose and len({c["date"] for c in chosen}) > 1:
            print(f"  [{label}] tiles come from different dates, "
                  "look for a seam in the image")
        picks.append(chosen)
    return picks


# -------------------------------------------------------------- downloading --
def band_urls(rec: dict, bands=None, with_fmask: bool = True) -> list[str]:
    """Direct download links for the bands we need from one granule."""
    bands = bands or S30_BANDS
    wanted = list(bands) + (["Fmask"] if with_fmask else [])
    return [u for u in rec["granule"].data_links()
            if any(u.endswith(f".{b}.tif") for b in wanted)]


def _is_tiff(path: Path) -> bool:
    try:
        with open(path, "rb") as f:
            return f.read(2) in (b"II", b"MM")
    except OSError:
        return False


def download(picks, outdir, bands=None, with_fmask=True, verbose=True) -> Path:
    """Download every band of every picked granule, then verify each file.

    Verification matters: a dropped connection can leave a file that looks
    complete but holds an error page. We check size against the server and
    the TIFF magic bytes, and re-fetch anything that fails.
    """
    import earthaccess
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    urls = [u for sel in picks for rec in sel
            for u in band_urls(rec, bands, with_fmask)]
    urls = sorted(set(urls))
    if verbose:
        print(f"{len(urls)} files to fetch into {outdir}")
    earthaccess.download(urls, str(outdir))

    session = earthaccess.get_requests_https_session()
    for attempt in range(3):
        bad = []
        for u in urls:
            f = outdir / u.split("/")[-1]
            try:
                remote = int(session.head(u, allow_redirects=True)
                             .headers.get("Content-Length", -1))
            except Exception:
                continue
            if remote > 0 and (not f.exists() or f.stat().st_size != remote
                               or not _is_tiff(f)):
                bad.append((u, f))
        if not bad:
            if verbose:
                print(f"all {len(urls)} files verified")
            return outdir
        if verbose:
            print(f"repairing {len(bad)} incomplete file(s)")
        for u, f in bad:
            r = session.get(u, stream=True, timeout=300)
            with open(f, "wb") as fh:
                for chunk in r.iter_content(1 << 22):
                    fh.write(chunk)
    raise RuntimeError("Some downloads could not be verified. Re-run the cell.")


# ---------------------------------------------------------------- stacking --
def target_grid(bbox, crs: str = "EPSG:5070", res: float = 30.0):
    """A clean 30 m grid covering bbox, snapped to round coordinates.

    EPSG:5070 (CONUS Albers) is the grid the USDA Cropland Data Layer uses,
    which makes later comparison against CDL a straight array operation.
    """
    import rasterio
    from rasterio.warp import transform_bounds
    left, bottom, right, top = transform_bounds("EPSG:4326", crs, *bbox)
    left, bottom = np.floor(left / res) * res, np.floor(bottom / res) * res
    right, top = np.ceil(right / res) * res, np.ceil(top / res) * res
    width, height = int((right - left) / res), int((top - bottom) / res)
    return rasterio.transform.from_origin(left, top, res, res), width, height


def build_stack(picks, raw_dir, bbox, out_tif, bands=None, crs="EPSG:5070",
                res=30.0, verbose=True):
    """Mosaic the chosen granules into one 18-band GeoTIFF.

    Band order is date-major: date 1 bands 1-6, date 2 bands 7-12, date 3
    bands 13-18. That is exactly what the Prithvi model expects.
    """
    import rasterio
    from rasterio.warp import Resampling, reproject
    bands = bands or S30_BANDS
    raw_dir = Path(raw_dir)
    transform, width, height = target_grid(bbox, crs, res)
    if verbose:
        print(f"output grid: {width} x {height} pixels at {res:.0f} m, {crs}")

    profile = dict(driver="GTiff", height=height, width=width, count=18,
                   dtype="int16", crs=crs, transform=transform,
                   nodata=NODATA, compress="lzw", tiled=True,
                   blockxsize=256, blockysize=256, BIGTIFF="IF_SAFER")
    with rasterio.open(out_tif, "w", **profile) as dst:
        for t, sel in enumerate(picks):
            for b_i, band in enumerate(bands):
                arr = np.full((height, width), NODATA, dtype=np.int16)
                first = True
                for rec in sel:
                    f = raw_dir / f"{rec['name']}.{band}.tif"
                    if not f.exists():
                        continue
                    with rasterio.open(f) as src:
                        reproject(rasterio.band(src, 1), arr,
                                  dst_transform=transform, dst_crs=crs,
                                  dst_nodata=NODATA,
                                  resampling=Resampling.bilinear,
                                  init_dest_nodata=first)
                    first = False
                dst.write(arr, t * 6 + b_i + 1)
            if verbose:
                print(f"  date {t + 1}: bands {t*6+1} to {t*6+6} written")
    return Path(out_tif)


# ------------------------------------------------------------ cloud masking --
def fmask_fraction(picks, raw_dir, bbox, crs="EPSG:5070", res=30.0):
    """Percent of the area flagged cloud, cloud shadow or cloud adjacent.

    Fmask is HLS's own per-pixel quality band. Bits 1, 2 and 3 are cloud
    shadow, adjacent to cloud, and cloud. Scene level cloud percentages
    describe a whole tile, so this is the number that matters for your area.
    """
    import rasterio
    from rasterio.warp import Resampling, reproject
    raw_dir = Path(raw_dir)
    transform, width, height = target_grid(bbox, crs, res)
    out = []
    for sel in picks:
        mask = np.full((height, width), 255, dtype=np.uint8)
        first = True
        for rec in sel:
            f = raw_dir / f"{rec['name']}.Fmask.tif"
            if not f.exists():
                continue
            with rasterio.open(f) as src:
                reproject(rasterio.band(src, 1), mask,
                          dst_transform=transform, dst_crs=crs,
                          dst_nodata=255, resampling=Resampling.nearest,
                          init_dest_nodata=first)
            first = False
        bad = (mask != 255) & ((mask & 0b00001110) > 0)
        out.append(round(float(100 * bad.sum() / bad.size), 1))
    return out


# ------------------------------------------------------------- display help --
def stretch_rgb(stack: np.ndarray, date_index: int = 0,
                idx: tuple[int, int, int] = RGB_IDX,
                pct: tuple[float, float] = (2, 98)) -> np.ndarray:
    """Pull one date out of an 18-band stack and stretch it for display.

    date_index is 0, 1 or 2. idx picks which three of the six bands to map to
    red, green and blue: RGB_IDX for true color, FALSE_COLOR_IDX for the
    near infrared composite where healthy vegetation is bright red.
    """
    chans = [date_index * 6 + i for i in idx]
    out = np.zeros((*stack.shape[1:], 3), dtype=np.uint8)
    for k, c in enumerate(chans):
        b = stack[c].astype(np.float32)
        valid = b != NODATA
        if not valid.any():
            continue
        lo, hi = np.percentile(b[valid], pct)
        s = np.clip((b - lo) / max(hi - lo, 1e-6), 0, 1)
        s[~valid] = 0
        out[..., k] = (s * 255).astype(np.uint8)
    return out


def ndvi(stack: np.ndarray, date_index: int = 0) -> np.ndarray:
    """NDVI for one date. Useful for seeing the season progress."""
    nir = stack[date_index * 6 + 3].astype(np.float32)
    red = stack[date_index * 6 + 2].astype(np.float32)
    valid = (nir != NODATA) & (red != NODATA)
    out = np.full(nir.shape, np.nan, dtype=np.float32)
    denom = nir + red
    ok = valid & (denom != 0)
    out[ok] = (nir[ok] - red[ok]) / denom[ok]
    return out
