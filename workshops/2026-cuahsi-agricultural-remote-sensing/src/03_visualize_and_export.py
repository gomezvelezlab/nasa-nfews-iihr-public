# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Notebook 3. Visualize and export
#
# **CUAHSI 2026. Agricultural Remote Sensing with Cloud Platforms and
# Geospatial Foundation Models**
#
# You have a crop map. Now make it useful to somebody else.
#
# **By the end of this notebook you will be able to**
#
# 1. read a classified map critically, next to the imagery it came from
# 2. build an interactive web map in Python
# 3. export a **cloud optimized GeoTIFF** and a **watershed shapefile**, the
#    two files Google Earth Engine needs
# 4. move results from the cloud machine to your own computer
#
# **Time:** about 20 minutes.
#
# The last step of the workshop, in the `GEE` folder of the repository, takes
# these two files into Google Earth Engine and publishes them as a public web
# app.

# %% [markdown]
# ## Setup
#
# Same first cell as before. With Google Drive connected, this notebook finds
# the crop map you made in notebook 2. If it does not find one, it uses the
# example shipped with the workshop (South Fork Iowa River), so you can always
# continue.

# %%
import os
import subprocess
import sys
from pathlib import Path

REPO_URL = "https://github.com/gomezvelezlab/nasa-nfews-iihr-public.git"
REPO_DIR = "nasa-nfews-iihr-public"
WORKSHOP = "workshops/2026-cuahsi-agricultural-remote-sensing"
KEEP_RESULTS_IN_DRIVE = True     # Colab only


def setup_workshop():
    """Find or fetch the workshop code, install requirements, return its path."""
    root = next((p for p in [Path.cwd(), *Path.cwd().parents]
                 if (p / "wsrs").is_dir()), None)
    if root is None:
        if not Path(REPO_DIR).is_dir():
            subprocess.run(["git", "clone", "--depth", "1", REPO_URL,
                            REPO_DIR], check=True)
        root = (Path(REPO_DIR) / WORKSHOP).resolve()
    os.chdir(root)
    sys.path.insert(0, str(root))
    try:
        import earthaccess, folium, rasterio, shapefile  # noqa: F401
    except ImportError:
        print("Installing the workshop requirements, about one minute ...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r",
                        "requirements.txt"], check=True)
    return root


ROOT = setup_workshop()

import shutil

import matplotlib.pyplot as plt
import numpy as np
import rasterio
import wsrs
from wsrs import basin, hls, viz

wsrs.print_environment()
if KEEP_RESULTS_IN_DRIVE:
    wsrs.connect_drive()
print(f"Results folder: {wsrs.data_dir()}")

# %% [markdown]
# ## Load the crop map
#
# `YEAR` must match the year you used in notebook 2.

# %%
YEAR = 2023               # the year you mapped in notebook 2

out_dir = wsrs.data_dir()
pred_path = out_dir / f"crop_map_{YEAR}.tif"
mine = sorted(p for p in out_dir.glob("crop_map_*.tif") if "_cog" not in p.name)

if not pred_path.exists() and mine:
    # You mapped a different year: use the most recent map you made.
    pred_path = mine[-1]
    YEAR = int(pred_path.stem.split("_")[-1])
    print(f"Using your {pred_path.name}.\n")
elif not pred_path.exists():
    # No map from notebook 2 here: continue with the ready made example,
    # kept in its own folder so that nothing of yours is overwritten.
    example = wsrs.example_files()
    YEAR = example["year"]
    out_dir = wsrs.data_dir("example")
    pred_path = out_dir / f"crop_map_{YEAR}.tif"
    shutil.copy(example["crop_map"], pred_path)
    shutil.copy(example["basin"], out_dir / "basin.geojson")
    print("No crop map from notebook 2 was found, so this notebook uses the "
          f"example:\nSouth Fork Iowa River, {YEAR}, classified by the "
          "instructors with the same workflow.\n")

stack_path = out_dir / f"stack_{YEAR}.tif"
basin_file = out_dir / "basin.geojson"
HAVE_IMAGERY = stack_path.exists()

with rasterio.open(pred_path) as src:
    pred = src.read(1)
geom, props = basin.load_geojson(basin_file)

print(f"crop map : {pred.shape[1]} by {pred.shape[0]} pixels, year {YEAR}")
print(f"basin    : {props.get('name', '')}")
print(f"imagery  : {'available' if HAVE_IMAGERY else 'not on this machine, the imagery panels are skipped'}")

# %% [markdown]
# ## 1. Read the map against the imagery
#
# The single most useful habit in remote sensing: never look at a
# classification on its own. Put it beside the reflectance it came from.

# %%
if HAVE_IMAGERY:
    with rasterio.open(stack_path) as src:
        stack = src.read()

    fig, axes = plt.subplots(1, 3, figsize=(16, 5.8))
    axes[0].imshow(hls.stretch_rgb(stack, 1))
    axes[0].set_title("July, true color", fontweight="bold")
    axes[1].imshow(hls.stretch_rgb(stack, 1, idx=hls.FALSE_COLOR_IDX))
    axes[1].set_title("July, false color (NIR)", fontweight="bold")
    viz.show_classified(pred, ax=axes[2], title="Classification", legend=False)
    for ax in axes[:2]:
        ax.set_axis_off()
else:
    fig, ax = plt.subplots(figsize=(10, 7.5))
    viz.show_classified(pred, ax=ax,
                        title=f"{props.get('name', 'basin')}  {YEAR}")
plt.tight_layout()
plt.show()

# %% [markdown]
# ### Zoom in
#
# Field edges are the test. A good classification has straight boundaries that
# line up with what you can see in the imagery. Speckle inside a single field
# means the model is unsure, which usually traces back to clouds or a missing
# date rather than to the model itself.

# %%
h, w = pred.shape
r0, c0 = h // 2 - 110, w // 2 - 110
sl = (slice(max(r0, 0), max(r0, 0) + 220), slice(max(c0, 0), max(c0, 0) + 220))

if HAVE_IMAGERY:
    fig, axes = plt.subplots(1, 2, figsize=(12, 6))
    axes[0].imshow(hls.stretch_rgb(stack, 1)[sl])
    axes[0].set_title("July imagery, about 6.6 by 6.6 km", fontweight="bold")
    axes[0].set_axis_off()
    viz.show_classified(pred[sl], ax=axes[1], title="Same area, classified",
                        legend_cols=3)
else:
    fig, ax = plt.subplots(figsize=(7.5, 7.5))
    viz.show_classified(pred[sl], ax=ax,
                        title="Center of the basin, about 6.6 by 6.6 km",
                        legend_cols=3)
plt.tight_layout()
plt.show()

# %% [markdown]
# ## 2. What is in the basin

# %%
areas = viz.class_area_table(pred)
areas

# %%
fig, ax = plt.subplots(figsize=(9, 4.6))
top = areas.head(8).iloc[::-1]
colors = [np.array(viz.CLASS_COLORS[v]) / 255 for v in top.value]
ax.barh(top["class"], top.percent, color=colors, edgecolor="k", linewidth=0.5)
for y, (pct, km2) in enumerate(zip(top.percent, top.area_km2)):
    ax.text(pct + 0.6, y, f"{pct:.1f}%  ({km2:,.0f} km2)", va="center",
            fontsize=9)
ax.set_xlabel("percent of classified area")
ax.set_xlim(0, top.percent.max() * 1.28)
ax.set_title(f"Land cover, {props.get('name','basin')}, {YEAR}",
             fontweight="bold")
ax.spines[["top", "right"]].set_visible(False)
plt.tight_layout()
plt.show()

row_crop = areas[areas["class"].isin(["Corn", "Soybeans"])].percent.sum()
print(f"corn plus soybeans: {row_crop:.1f} percent of the classified area")

# %% [markdown]
# ## 3. An interactive map, in Python
#
# `folium` wraps Leaflet, the same library behind most web maps. The classified
# raster is reprojected to lon/lat, turned into a transparent PNG, and draped
# over a basemap. Everything below runs locally in this notebook, with no
# account and no server.

# %%
m = viz.basin_map(geom, zoom=11)
if HAVE_IMAGERY:
    viz.add_rgb_overlay(m, stack_path, date_index=1,
                        name="HLS July, true color")
viz.add_class_overlay(m, pred_path, name=f"Crop classification {YEAR}",
                      opacity=0.8)
viz.add_legend(m, present=pred, title=f"Crop classes {YEAR}")

import folium

folium.LayerControl(collapsed=False).add_to(m)
m

# %% [markdown]
# **Try this:** use the layer control in the corner to switch between the
# satellite basemap, the July image and the classification. Toggling the
# classification on and off over the imagery is the fastest qualitative
# accuracy check there is.
#
# The map is a self contained HTML file. Save it and it opens in any browser,
# no Python required.

# %%
html_path = out_dir / f"crop_map_{YEAR}.html"
m.save(str(html_path))
print(f"saved {html_path}  ({html_path.stat().st_size/1e6:.1f} MB)")

# %% [markdown]
# > This HTML embeds the image as base64, so it is self contained but chunky,
# > and it is a picture rather than a queryable layer. Google Earth Engine
# > solves both problems: the raster is tiled on demand and can be inspected
# > pixel by pixel. That is the last step of the workshop.

# %% [markdown]
# ## 4. Export a cloud optimized GeoTIFF
#
# A **COG** is an ordinary GeoTIFF with two disciplines applied: the pixels are
# stored in tiles rather than strips, and reduced resolution overviews are
# embedded. A client can then fetch the few kilobytes covering one corner, or
# a zoomed out preview, with an HTTP range request instead of downloading the
# whole file.
#
# This is what makes a raster usable on the web, and it is what Earth Engine,
# QGIS and STAC catalogues expect.

# %%
cog_path = out_dir / f"crop_map_{YEAR}_cog.tif"
viz.export_cog(pred_path, cog_path)

before = viz.describe_raster(pred_path)
after = viz.describe_raster(cog_path)

print(f"{'':>14}  {'plain GeoTIFF':>16}  {'COG':>16}")
for k in ["size_mb", "tiled", "overviews", "has_colormap", "crs"]:
    print(f"{k:>14}  {str(before[k])[:16]:>16}  {str(after[k])[:16]:>16}")

# %% [markdown]
# The `overviews` entry is the part that matters. `[2, 4, 8, 16]` means the
# file carries copies at half, quarter, eighth and sixteenth resolution, so a
# viewer zoomed out reads a small pyramid level instead of decoding every
# pixel.

# %% [markdown]
# ### Verify it properly
#
# `rio-cogeo` is the reference validator. If it is not installed the cell
# falls back to the structural check above.

# %%
try:
    from rio_cogeo.cogeo import cog_validate
    valid, errors, warnings = cog_validate(str(cog_path))
    print("valid COG:", valid)
    for e in errors:
        print("  error:", e)
    for w in warnings:
        print("  warning:", w)
except ImportError:
    print("rio-cogeo not installed. pip install rio-cogeo to run the "
          "official validator.")

# %% [markdown]
# ## 5. The watershed as a shapefile
#
# Google Earth Engine does not take GeoJSON through its upload window, but it
# takes a zipped shapefile. One call writes the basin from notebook 1 in that
# form: the zip holds the `.shp`, `.shx`, `.dbf` and `.prj` parts together.

# %%
shp_zip = out_dir / "watershed.zip"
basin.save_shapefile_zip(geom, shp_zip, properties=props, layer="watershed")

import zipfile

with zipfile.ZipFile(shp_zip) as z:
    for info in z.infolist():
        print(f"{info.filename:>16}  {info.file_size:>8,} bytes")

# %% [markdown]
# ## 6. Take it with you
#
# Cloud machines are temporary. Download the files worth keeping. The first
# two are the ones you will upload to Google Earth Engine.

# %%
keep = [cog_path, shp_zip, html_path]
for p in keep:
    print(f"{p.name:>28}  {p.stat().st_size/1e6:7.2f} MB")

if "google.colab" in sys.modules:
    from google.colab import files
    print("\nStarting downloads. Your browser may ask permission to download "
          "several files: allow it.")
    for p in keep:
        files.download(str(p))
else:
    print(f"\nNot in Colab. The files are in {out_dir}")

# %% [markdown]
# ## 7. Your turn: how much of the basin is row crop?
#
# **Guided activity.** Replace each `...` with a class name from the table in
# section 2, in quotes, and run the cell.

# %%
CLASS_A = ...             # for example "Corn"
CLASS_B = ...

if CLASS_A is ... or CLASS_B is ...:
    print("Replace both ... with class names in quotes, then run this cell again.")
else:
    chosen = areas[areas["class"].isin([CLASS_A, CLASS_B])]
    print(chosen[["class", "area_km2", "percent"]].to_string(index=False))
    print(f"\ntogether: {chosen.area_km2.sum():,.0f} km2, "
          f"{chosen.percent.sum():.1f} percent of the classified area")
    # Is that share plausible for this landscape?  Your answer: ...

# %% [markdown]
# <details>
# <summary><b>Show one solution</b></summary>
#
# `CLASS_A = "Corn"` and `CLASS_B = "Soybeans"`. For the South Fork Iowa
# River in 2023 the two classes together cover about 86 percent of the basin
# (corn about 55 percent, soybeans about 30 percent). That is plausible: the
# USDA Cropland Data Layer of the same year gives about 83 percent for this
# basin. A Missouri basin with more pasture and forest should give a much
# lower share.
#
# </details>

# %% [markdown]
# ## What comes next
#
# You now hold a georeferenced, styled, web ready crop map and the boundary
# of its watershed.
#
# **Share it (the `GEE` folder).** Upload the cloud optimized GeoTIFF and the
# zipped shapefile to Google Earth Engine, paste one short script, and publish
# an app. The result is a link that opens in any browser for someone with no
# Earth Engine account, no GIS software, and no idea what a GeoTIFF is. The
# steps are in `GEE/README.md` in the workshop repository.
#
# **Check it (notebook 4, optional).** The honest question about any
# classification is how often it is right. Notebook 4 compares your map with
# the USDA Cropland Data Layer class by class, and reminds you that the
# reference is itself a model product, not ground truth.
#
# **Use it.** Corn and soybean fractions per sub-basin feed nutrient export
# estimates; repeating the workflow across years turns one map into a
# rotation history. Notebook 1 gives you any gauged basin in the country.

# %% [markdown]
# ## What we did
#
# - compared the classification against its own input imagery, at basin scale
#   and at field scale, because that is how you catch a bad map
# - summarized land cover as numbers a hydrologist can use
# - built an interactive, shareable map in pure Python
# - exported a cloud optimized GeoTIFF and a zipped watershed shapefile
# - moved the results off the cloud machine
#
# **Next:** open `GEE/README.md` and publish your map as an online app.
