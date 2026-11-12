"""
Making the crop map look like something: colors, legends, interactive maps,
and a cloud optimized GeoTIFF to hand to Earth Engine.

The palette matches the USDA Cropland Data Layer conventions, so a hydrologist
who has seen a CDL map before will read ours without a second thought:
corn is yellow, soybeans dark green, water blue, developed gray.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from .classes import CLASS_COLORS, CLASSES

# Classes that do not occur in the Midwest. The model can still emit them,
# usually as salt and pepper noise, because its training labels covered the
# whole country.
IMPLAUSIBLE_MIDWEST = {11: "Cotton", 12: "Sorghum"}


# --------------------------------------------------------------- coloring --
def colorize(pred: np.ndarray, alpha: bool = False) -> np.ndarray:
    """Class integers to an RGB (or RGBA) image. Class 0 is transparent."""
    h, w = pred.shape
    out = np.zeros((h, w, 4 if alpha else 3), dtype=np.uint8)
    for cid, rgb in CLASS_COLORS.items():
        m = pred == cid
        if not m.any():
            continue
        out[m, :3] = rgb
        if alpha:
            out[m, 3] = 0 if cid == 0 else 255
    return out


def legend_handles(present: np.ndarray | None = None):
    """matplotlib patches for a legend, optionally only for classes present."""
    from matplotlib.patches import Patch
    ids = (sorted(int(c) for c in np.unique(present) if c > 0)
           if present is not None else list(range(1, 14)))
    return [Patch(facecolor=np.array(CLASS_COLORS[c]) / 255, edgecolor="k",
                  linewidth=0.3, label=CLASSES[c - 1]) for c in ids]


def show_classified(pred: np.ndarray, ax=None, title: str = "",
                    legend: bool = True, legend_cols: int = 4):
    """Quick look at a classified array with a legend underneath."""
    import matplotlib.pyplot as plt
    if ax is None:
        _, ax = plt.subplots(figsize=(9, 7))
    rgba = colorize(pred, alpha=True)
    ax.imshow(rgba, interpolation="nearest")
    ax.set_axis_off()
    if title:
        ax.set_title(title, fontweight="bold")
    if legend:
        ax.legend(handles=legend_handles(pred), loc="upper center",
                  bbox_to_anchor=(0.5, -0.02), ncol=legend_cols,
                  frameon=False, fontsize=9)
    return ax


def class_area_table(pred: np.ndarray, pixel_m: float = 30.0):
    """Per class pixel count, area and share of the classified area."""
    import pandas as pd
    valid = int((pred > 0).sum())
    rows = []
    for cid in range(1, 14):
        n = int((pred == cid).sum())
        if n == 0:
            continue
        rows.append({"value": cid, "class": CLASSES[cid - 1], "pixels": n,
                     "area_km2": round(n * pixel_m ** 2 / 1e6, 2),
                     "percent": round(100 * n / max(valid, 1), 2)})
    df = pd.DataFrame(rows).sort_values("percent", ascending=False)
    return df.reset_index(drop=True)


# ------------------------------------------------------------ georeferenced --
def save_classified(pred: np.ndarray, like_path, out_path,
                    colormap: bool = True) -> Path:
    """Write a class array as a uint8 GeoTIFF borrowing a grid from like_path.

    The color table is embedded, so the file opens already styled in QGIS
    or ArcGIS without anyone touching a symbology dialog.
    """
    import rasterio
    with rasterio.open(like_path) as src:
        profile = src.profile
    profile.update(count=1, dtype="uint8", nodata=0, compress="lzw",
                   driver="GTiff")
    profile.pop("BIGTIFF", None)
    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(pred.astype(np.uint8), 1)
        if colormap:
            dst.write_colormap(1, {k: tuple(v) for k, v in
                                   CLASS_COLORS.items()})
    return Path(out_path)


def export_cog(src_path, dst_path, overview_resampling: str = "nearest"
               ) -> Path:
    """Convert a GeoTIFF to a Cloud Optimized GeoTIFF.

    A COG is an ordinary GeoTIFF with its data tiled and its overviews
    arranged so that a client can read one corner over HTTP without pulling
    the whole file. Earth Engine, QGIS and web clients all like them.
    """
    import rasterio
    import rasterio.shutil
    rasterio.shutil.copy(str(src_path), str(dst_path), driver="COG",
                         compress="DEFLATE", blocksize=512,
                         overview_resampling=overview_resampling)
    return Path(dst_path)


def describe_raster(path) -> dict:
    """Facts worth printing after writing a file: size, CRS, overviews."""
    import rasterio
    with rasterio.open(path) as src:
        return {"path": str(path),
                "size_mb": round(Path(path).stat().st_size / 1e6, 2),
                "width": src.width, "height": src.height,
                "bands": src.count, "dtype": src.dtypes[0],
                "crs": str(src.crs), "pixel_m": round(abs(src.transform.a), 1),
                "nodata": src.nodata, "tiled": src.profile.get("tiled", False),
                "overviews": src.overviews(1),
                "has_colormap": bool(src.colormap(1)) if src.count else False}


# --------------------------------------------------------------- warping ----
def _warp_to_wgs84(path, bands=(1,), resampling="nearest",
                   max_pixels: int = 2_000_000):
    """Reproject selected bands to EPSG:4326 for web mapping.

    Folium overlays want lon/lat. We also cap the size, because a 4000 by
    4000 overlay turns a notebook into a slideshow.
    """
    import rasterio
    from rasterio.enums import Resampling
    from rasterio.warp import calculate_default_transform, reproject
    rs = getattr(Resampling, resampling)
    with rasterio.open(path) as src:
        transform, width, height = calculate_default_transform(
            src.crs, "EPSG:4326", src.width, src.height, *src.bounds)
        scale = max(1.0, np.sqrt(width * height / max_pixels))
        if scale > 1:
            width, height = int(width / scale), int(height / scale)
            transform, width, height = calculate_default_transform(
                src.crs, "EPSG:4326", src.width, src.height, *src.bounds,
                dst_width=width, dst_height=height)
        stack = []
        for b in bands:
            arr = np.zeros((height, width), dtype=src.dtypes[b - 1])
            reproject(source=rasterio.band(src, b), destination=arr,
                      dst_transform=transform, dst_crs="EPSG:4326",
                      dst_nodata=src.nodata if src.nodata is not None else 0,
                      resampling=rs)
            stack.append(arr)
    west, north = transform * (0, 0)
    east, south = transform * (width, height)
    return np.stack(stack), [[south, west], [north, east]]


# --------------------------------------------------------------- folium -----
def basin_map(geom: dict, center=None, zoom: int = 10, site=None,
              tiles: str = "satellite"):
    """A folium map centered on a basin, with the outline drawn on top."""
    import folium
    from shapely.geometry import shape
    if center is None:
        c = shape(geom).centroid
        center = [c.y, c.x]
    if tiles == "satellite":
        m = folium.Map(location=center, zoom_start=zoom, tiles=None)
        folium.TileLayer(
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/"
                  "World_Imagery/MapServer/tile/{z}/{y}/{x}",
            attr="Esri World Imagery", name="Satellite").add_to(m)
        folium.TileLayer("OpenStreetMap", name="Street map").add_to(m)
    else:
        m = folium.Map(location=center, zoom_start=zoom, tiles=tiles)
    folium.GeoJson(geom, name="Basin",
                   style_function=lambda _: {"color": "#e31a1c", "weight": 2.5,
                                             "fillOpacity": 0.05}).add_to(m)
    if site:
        folium.Marker([site["lat"], site["lon"]],
                      tooltip=f"{site.get('site_id','')} {site.get('name','')}",
                      icon=folium.Icon(color="blue", icon="tint",
                                       prefix="fa")).add_to(m)
    return m


def add_class_overlay(m, pred_path, name: str = "Crop classification",
                      opacity: float = 0.75):
    """Drape a classified GeoTIFF over a folium map."""
    import folium
    arr, bounds = _warp_to_wgs84(pred_path, bands=(1,), resampling="nearest")
    rgba = colorize(arr[0], alpha=True)
    folium.raster_layers.ImageOverlay(
        image=rgba, bounds=bounds, opacity=opacity, name=name,
        mercator_project=True).add_to(m)
    return m


def add_rgb_overlay(m, stack_path, date_index: int = 0,
                    name: str = "True color", opacity: float = 1.0,
                    false_color: bool = False):
    """Drape one date of the HLS stack over a folium map."""
    import folium
    from .hls import FALSE_COLOR_IDX, NODATA, RGB_IDX
    idx = FALSE_COLOR_IDX if false_color else RGB_IDX
    bands = tuple(date_index * 6 + i + 1 for i in idx)
    arr, bounds = _warp_to_wgs84(stack_path, bands=bands,
                                 resampling="bilinear")
    rgba = np.zeros((*arr.shape[1:], 4), dtype=np.uint8)
    for k in range(3):
        b = arr[k].astype(np.float32)
        valid = b != NODATA
        if valid.any():
            lo, hi = np.percentile(b[valid], (2, 98))
            s = np.clip((b - lo) / max(hi - lo, 1e-6), 0, 1)
            rgba[..., k] = (s * 255).astype(np.uint8)
    rgba[..., 3] = np.where(arr[0] != NODATA, 255, 0)
    folium.raster_layers.ImageOverlay(
        image=rgba, bounds=bounds, opacity=opacity, name=name,
        mercator_project=True).add_to(m)
    return m


def add_legend(m, present: np.ndarray | None = None, title: str = "Land cover"):
    """A fixed HTML legend box in the corner of a folium map."""
    import folium
    ids = (sorted(int(c) for c in np.unique(present) if c > 0)
           if present is not None else list(range(1, 14)))
    rows = "".join(
        f'<div style="line-height:1.45"><span style="display:inline-block;'
        f'width:13px;height:13px;background:rgb{CLASS_COLORS[c]};'
        f'border:1px solid #444;margin-right:7px;vertical-align:-2px">'
        f'</span>{c} {CLASSES[c - 1]}</div>' for c in ids)
    html = (f'<div style="position:fixed;bottom:28px;left:14px;z-index:9999;'
            f'background:white;padding:10px 12px;border:1px solid #999;'
            f'border-radius:4px;font-size:12px;font-family:sans-serif;'
            f'box-shadow:0 1px 4px rgba(0,0,0,.3)">'
            f'<b>{title}</b><br>{rows}</div>')
    m.get_root().html.add_child(folium.Element(html))
    return m
