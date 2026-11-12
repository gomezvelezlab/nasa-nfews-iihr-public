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
# continue. No GitHub account is needed, because the repository is public.

# %%
# ---- Python tools used by this setup cell (they all come with Python) ----
import os                    # change the working folder
import subprocess            # run command line programs (git, pip)
import sys                   # tell Python where to find code
from pathlib import Path     # work with file and folder paths

# ---- Where the workshop material lives ----
# The repository is public. Anyone can copy it.
# You do NOT need a GitHub account, a password or a token.
REPO_URL = "https://github.com/gomezvelezlab/nasa-nfews-iihr-public.git"
REPO_DIR = "nasa-nfews-iihr-public"     # name of the copy on this machine
WORKSHOP = "workshops/2026-cuahsi-agricultural-remote-sensing"  # our folder
KEEP_RESULTS_IN_DRIVE = True     # Colab only. True saves your results in Drive


def setup_workshop():
    """Find or fetch the workshop code, install requirements, return its path."""
    # Step 1. Is the workshop code already on this machine?
    # Look in the current folder and in the folders above it for "wsrs",
    # the small helper package of this workshop.
    root = next((p for p in [Path.cwd(), *Path.cwd().parents]
                 if (p / "wsrs").is_dir()), None)

    # Step 2. If it is not here (the usual case in Colab), copy it.
    # "git clone" downloads a copy of the public repository.
    # "--depth 1" takes only the latest version, which is faster.
    if root is None:
        if not Path(REPO_DIR).is_dir():      # skip if it was copied before
            subprocess.run(["git", "clone", "--depth", "1", REPO_URL,
                            REPO_DIR], check=True)
        root = (Path(REPO_DIR) / WORKSHOP).resolve()

    # Step 3. Work from the workshop folder.
    os.chdir(root)                     # like "cd" in a terminal
    sys.path.insert(0, str(root))      # lets Python run "import wsrs"

    # Step 4. Install the Python packages that are missing.
    # We try to import four of them. If one is missing, pip installs the
    # list in requirements.txt. Nothing is installed twice.
    try:
        import earthaccess, folium, rasterio, shapefile  # noqa: F401
    except ImportError:
        print("Installing the workshop requirements, about one minute ...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r",
                        "requirements.txt"], check=True)
    return root


# Run the setup. ROOT is the workshop folder on this machine.
ROOT = setup_workshop()

# Load the libraries used in this notebook.
import shutil                       # copy files

import matplotlib.pyplot as plt     # figures
import numpy as np                  # arrays and math
import rasterio                     # reads and writes GeoTIFF files
import wsrs                         # the workshop helper package
from wsrs import basin, hls, viz    # watershed, imagery and map helpers

# Print the Python version and the hardware of this machine.
wsrs.print_environment()

# Connect Google Drive, where notebook 2 saved your crop map.
if KEEP_RESULTS_IN_DRIVE:
    wsrs.connect_drive()
print(f"Results folder: {wsrs.data_dir()}")

# %% [markdown]
# ## Load the crop map
#
# `YEAR` must match the year you used in notebook 2.

# %%
YEAR = 2023               # the year you mapped in notebook 2

# Where to look: the results folder, and the crop map of that year in it.
out_dir = wsrs.data_dir()
pred_path = out_dir / f"crop_map_{YEAR}.tif"

# The list of the crop maps you made so far. The "_cog" copies are left out.
mine = sorted(p for p in out_dir.glob("crop_map_*.tif") if "_cog" not in p.name)

# Three cases are possible:
#   1. the map of YEAR is there, and nothing needs to change
#   2. it is not there, but a map of another year is: use that one
#   3. there is no map at all: use the example of the workshop
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

# The two files that go with the map: the 18 layer image stack of
# notebook 2, and the basin boundary.
stack_path = out_dir / f"stack_{YEAR}.tif"
basin_file = out_dir / "basin.geojson"
HAVE_IMAGERY = stack_path.exists()      # True when the image stack is here

# Read the crop map into memory: one layer, with a class number per pixel.
with rasterio.open(pred_path) as src:
    pred = src.read(1)

# Read the basin polygon (geom) and the gauge information (props).
geom, props = basin.load_geojson(basin_file)

# Print what was loaded.
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
    # Read the 18 layer image stack made in notebook 2.
    with rasterio.open(stack_path) as src:
        stack = src.read()

    # Here we start a figure with three panels side by side.
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.8))

    # Left panel: the July image in true color. The number 1 selects the
    # second date of the stack, which is July (0 is May, 2 is September).
    axes[0].imshow(hls.stretch_rgb(stack, 1))
    axes[0].set_title("July, true color", fontweight="bold")

    # Middle panel: the same July image in false color (near infrared).
    axes[1].imshow(hls.stretch_rgb(stack, 1, idx=hls.FALSE_COLOR_IDX))
    axes[1].set_title("July, false color (NIR)", fontweight="bold")

    # Right panel: the crop map.
    viz.show_classified(pred, ax=axes[2], title="Classification", legend=False)

    # The loop hides the axis ticks of the two image panels.
    for ax in axes[:2]:
        ax.set_axis_off()
else:
    # Without the image stack (the example case): one panel, the crop map.
    fig, ax = plt.subplots(figsize=(10, 7.5))
    viz.show_classified(pred, ax=ax,
                        title=f"{props.get('name', 'basin')}  {YEAR}")

# Tidy the spacing and show the figure.
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
# The size of the map: h rows and w columns.
h, w = pred.shape

# The upper left corner of a square of 220 by 220 pixels (about 6.6 km)
# placed at the center of the map.
r0, c0 = h // 2 - 110, w // 2 - 110

# "sl" is that square, written as (rows, columns). It is used below to cut
# the same area out of the image and out of the crop map.
sl = (slice(max(r0, 0), max(r0, 0) + 220), slice(max(c0, 0), max(c0, 0) + 220))

if HAVE_IMAGERY:
    # Two panels: the July image on the left and the crop map on the right,
    # both cut to the same square.
    fig, axes = plt.subplots(1, 2, figsize=(12, 6))
    axes[0].imshow(hls.stretch_rgb(stack, 1)[sl])
    axes[0].set_title("July imagery, about 6.6 by 6.6 km", fontweight="bold")
    axes[0].set_axis_off()
    viz.show_classified(pred[sl], ax=axes[1], title="Same area, classified",
                        legend_cols=3)
else:
    # Without the image stack: one panel, the crop map of the square.
    fig, ax = plt.subplots(figsize=(7.5, 7.5))
    viz.show_classified(pred[sl], ax=ax,
                        title="Center of the basin, about 6.6 by 6.6 km",
                        legend_cols=3)
plt.tight_layout()
plt.show()

# %% [markdown]
# ## 2. What is in the basin

# %%
# A table with one line per class: number of pixels, area in km2 and
# percent of the classified area. The largest class comes first.
areas = viz.class_area_table(pred)
areas

# %%
# Here we start a figure for a bar chart with horizontal bars.
fig, ax = plt.subplots(figsize=(9, 4.6))

# Take the 8 largest classes. The order is reversed, so that the largest
# class ends up at the top of the chart.
top = areas.head(8).iloc[::-1]

# The color of each class, the same as on the map. Dividing by 255 turns
# color values of 0 to 255 into the 0 to 1 range that the chart expects.
colors = [np.array(viz.CLASS_COLORS[v]) / 255 for v in top.value]

# Draw the bars: one class per bar, and the percent as the bar length.
ax.barh(top["class"], top.percent, color=colors, edgecolor="k", linewidth=0.5)

# The loop writes the percent and the area at the end of each bar.
for y, (pct, km2) in enumerate(zip(top.percent, top.area_km2)):
    ax.text(pct + 0.6, y, f"{pct:.1f}%  ({km2:,.0f} km2)", va="center",
            fontsize=9)

# Axis name, some room on the right for the labels, the title, and no
# frame on the top and right sides.
ax.set_xlabel("percent of classified area")
ax.set_xlim(0, top.percent.max() * 1.28)
ax.set_title(f"Land cover, {props.get('name','basin')}, {YEAR}",
             fontweight="bold")
ax.spines[["top", "right"]].set_visible(False)

# Tidy the spacing and show the figure.
plt.tight_layout()
plt.show()

# Add the shares of corn and soybeans together.
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
# Start an interactive map centered on the basin, with the basin outline.
# The background is a satellite image. A topographic map is the second
# choice in the layer box.
m = viz.basin_map(geom, zoom=11)

# If the image stack is here, lay the July true color image on the map.
if HAVE_IMAGERY:
    viz.add_rgb_overlay(m, stack_path, date_index=1,
                        name="HLS July, true color")

# Lay the crop map on top, slightly transparent (opacity 0.8).
viz.add_class_overlay(m, pred_path, name=f"Crop classification {YEAR}",
                      opacity=0.8)

# Add a legend with the classes that are present in the map.
viz.add_legend(m, present=pred, title=f"Crop classes {YEAR}")

import folium       # the interactive map library

# Add the layer box in the upper right corner, to switch the background
# and to turn each layer on and off.
folium.LayerControl(collapsed=False).add_to(m)

# Show the map.
m

# %% [markdown]
# **Try this:** use the layer box in the corner to switch between the
# satellite background, the topographic map, the July image and the
# classification. Toggling the classification on and off over the imagery is
# the fastest qualitative accuracy check there is.
#
# The backgrounds come from Esri World Imagery and from the USGS National
# Map. OpenStreetMap is not used, because its tile server blocks requests
# that come from a Colab notebook.
#
# The map is a self contained HTML file. Save it and it opens in any browser,
# no Python required.

# %%
# Save the interactive map as one HTML file in the results folder.
html_path = out_dir / f"crop_map_{YEAR}.html"
m.save(str(html_path))

# Confirm where the file went and how big it is.
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
# The name of the new file: the same map, cloud optimized.
cog_path = out_dir / f"crop_map_{YEAR}_cog.tif"

# Write it. The function stores the pixels in small blocks and adds
# reduced copies of the map for zoomed out views.
viz.export_cog(pred_path, cog_path)

# Describe the two files, to compare them.
before = viz.describe_raster(pred_path)
after = viz.describe_raster(cog_path)

# Print the comparison as a small table. The loop writes one line per
# property: file size, blocks, reduced copies, colors, projection.
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
# "try" runs the validator when the rio-cogeo package is installed.
try:
    from rio_cogeo.cogeo import cog_validate

    # Check the file. The answer has three parts: valid or not, a list of
    # errors and a list of warnings.
    valid, errors, warnings = cog_validate(str(cog_path))
    print("valid COG:", valid)

    # The two loops print the errors and the warnings, if there are any.
    for e in errors:
        print("  error:", e)
    for w in warnings:
        print("  warning:", w)
except ImportError:
    # The package is missing: say so and move on.
    print("rio-cogeo not installed. pip install rio-cogeo to run the "
          "official validator.")

# %% [markdown]
# ## 5. The watershed as a shapefile
#
# Google Earth Engine does not take GeoJSON through its upload window, but it
# takes a zipped shapefile. One call writes the basin from notebook 1 in that
# form: the zip holds the `.shp`, `.shx`, `.dbf` and `.prj` parts together.

# %%
# The name of the zip file, in the results folder.
shp_zip = out_dir / "watershed.zip"

# Write the basin polygon as a shapefile and zip its parts together.
basin.save_shapefile_zip(geom, shp_zip, properties=props, layer="watershed")

import zipfile        # reads zip files

# Open the zip. The loop lists what is inside, with the size of each part.
with zipfile.ZipFile(shp_zip) as z:
    for info in z.infolist():
        print(f"{info.filename:>16}  {info.file_size:>8,} bytes")

# %% [markdown]
# ## 6. Take it with you
#
# Cloud machines are temporary. Download the files worth keeping. The first
# two are the ones you will upload to Google Earth Engine.

# %%
# The three files worth keeping: the cloud optimized GeoTIFF, the zipped
# shapefile and the interactive map.
keep = [cog_path, shp_zip, html_path]

# The loop prints their names and sizes.
for p in keep:
    print(f"{p.name:>28}  {p.stat().st_size/1e6:7.2f} MB")

# In Colab, send each file to your computer through the browser.
# Anywhere else, only say where the files are.
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

# The three dots are placeholders. Until you replace both, the cell only
# prints a reminder.
if CLASS_A is ... or CLASS_B is ...:
    print("Replace both ... with class names in quotes, then run this cell again.")
else:
    # Keep the two lines of the area table that match your two classes,
    # print them, then add them together.
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
