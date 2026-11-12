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
# # Notebook 1. Pick a basin
#
# **CUAHSI 2026. Agricultural Remote Sensing with Cloud Platforms and
# Geospatial Foundation Models**
#
# Everything in this workshop happens inside a watershed. Before we touch
# satellite imagery we need a boundary: a polygon that says "this is the land
# that drains to the place I care about".
#
# You could download a shapefile and hope it is current. Instead we will ask
# the USGS for it directly, which takes about three seconds and gives us the
# exact polygon that appears on a USGS monitoring location page.
#
# **By the end of this notebook you will be able to**
#
# 1. get the watershed boundary of any USGS stream gauge from a web service
# 2. check that boundary against the published drainage area
# 3. estimate how basin size translates into computing time
#
# The boundary is saved as GeoJSON, ready for notebook 2.
#
# **Time:** about 15 minutes.

# %% [markdown]
# ## Setup
#
# Run this cell first. In Google Colab it copies the workshop code to your
# cloud machine, installs what is missing (about one minute the first time),
# and connects your Google Drive so that your results are still there when you
# open the next notebook.
#
# Colab will ask permission to access Drive: choose your account, tick
# **Select all**, and continue. If you prefer not to, set
# `KEEP_RESULTS_IN_DRIVE = False`; the later notebooks then fall back to the
# example data shipped with the workshop.

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

import wsrs
from wsrs import basin

wsrs.print_environment()
if KEEP_RESULTS_IN_DRIVE:
    wsrs.connect_drive()
print(f"\nWorkshop code : {ROOT}")
print(f"Results folder: {wsrs.data_dir()}")

# %% [markdown]
# ## 1. Two USGS services, no account needed
#
# **NWIS**, the National Water Information System site file, answers *what is
# this gauge*: name, coordinates, drainage area, hydrologic unit code.
#
# **NLDI**, the Network Linked Data Index, answers *what is connected to it*.
# NLDI knows the NHDPlus river network, so it can walk upstream from a gauge
# and return the contributing basin as a polygon, the river reaches above it,
# and any other monitoring sites on those reaches.
#
# Both are plain HTTP. The basin request is literally:
#
# ```
# https://api.water.usgs.gov/nldi/linked-data/nwissite/USGS-05451210/basin
# ```
#
# That is the whole trick. `wsrs/basin.py` wraps these calls, and it is short
# enough to read if you are curious.

# %% [markdown]
# ## 2. Choose your gauge
#
# The default is the South Fork Iowa River, an intensively tiled corn and
# soybean basin in central Iowa. It is a good teaching case: nearly 80 percent
# of it is row crop, and it is small enough to classify quickly.
#
# **Change `SITE_ID` to any USGS stream gauge** and the rest of the workshop
# follows along. Section 6 shows how to find one near you.

# %%
SITE_ID = "05451210"   # South Fork Iowa River NE of New Providence, IA

site = basin.site_info(SITE_ID)
for k, v in site.items():
    print(f"{k:>18}: {v}")

# %% [markdown]
# `drain_area_km2` is the official published drainage area. Keep it in mind:
# in a moment we will compare it against the polygon we download, which is a
# free and surprisingly effective sanity check.

# %% [markdown]
# ## 3. Ask NLDI for the basin

# %%
geom = basin.basin_polygon(SITE_ID)
poly_km2 = basin.area_km2(geom)
bbox = basin.geom_bbox(geom)

print(f"geometry type     : {geom['type']}")
print(f"polygon area      : {poly_km2:,.1f} km2")
print(f"NWIS drainage area: {site['drain_area_km2']:,.1f} km2")

if site["drain_area_km2"]:
    diff = 100 * abs(poly_km2 - site["drain_area_km2"]) / site["drain_area_km2"]
    verdict = "good agreement" if diff < 10 else "CHECK THIS"
    print(f"difference        : {diff:.1f} percent  ({verdict})")

print(f"\nbounding box (lon/lat): "
      f"{bbox[0]:.3f}, {bbox[1]:.3f}, {bbox[2]:.3f}, {bbox[3]:.3f}")

# %% [markdown]
# **Why compare the two numbers?** They come from different places. The
# drainage area is a surveyed, published value. The polygon is traced by an
# automated routine over a digital elevation model. When they agree within
# roughly 10 percent you have the right basin. When they do not, you may have
# a gauge NLDI cannot resolve, a braided or diverted channel, or a
# transboundary basin. Catching that now costs a second. Catching it after you
# have classified the wrong area costs an afternoon.

# %% [markdown]
# ## 4. Look at it
#
# A polygon in a variable is easy to be wrong about. Put it on a map.

# %%
from wsrs import viz

m = viz.basin_map(geom, site=site, zoom=10)
m

# %% [markdown]
# Pan around. You should see field boundaries, a dendritic stream network, and
# the gauge marker sitting on the main stem at the basin outlet. If the marker
# is in the middle of the polygon rather than at its edge, something is wrong.

# %% [markdown]
# ## 5. The river network above the gauge
#
# NLDI can also return every flowline upstream. This is not strictly needed
# for the crop map, but it makes the idea of "upstream contributing area"
# concrete, and it is one more HTTP call.

# %%
flowlines = basin.upstream_flowlines(SITE_ID, distance_km=200)
n_reaches = len(flowlines.get("features", []))
print(f"{n_reaches} river reaches upstream of {SITE_ID}")

import folium  # noqa: E402

folium.GeoJson(flowlines, name="Upstream rivers",
               style_function=lambda _: {"color": "#1f78b4",
                                         "weight": 1.6}).add_to(m)
folium.LayerControl(collapsed=False).add_to(m)
m

# %% [markdown]
# ## 6. How big is this, in compute terms?
#
# The Prithvi model reads the landscape in 224 by 224 pixel tiles at 30 m
# resolution, so one tile covers 6.7 by 6.7 km. The number of tiles is what
# determines how long notebook 2 takes.
#
# A rough rule of thumb. The CPU row was measured on a 2 core cloud machine;
# the GPU row is the order of magnitude to expect.
#
# | hardware | per tile | 30 tiles |
# |---|---|---|
# | Colab CPU | 10 to 12 s | 5 to 6 min |
# | Colab T4 GPU | under 1 s | under 1 min |

# %%
import math

west, south, east, north = bbox
km_x = (east - west) * 111.0 * math.cos(math.radians((south + north) / 2))
km_y = (north - south) * 111.0
tiles = math.ceil(km_x / 6.72) * math.ceil(km_y / 6.72)

print(f"bounding box : {km_x:.0f} by {km_y:.0f} km")
print(f"at 30 m      : {km_x*1000/30:.0f} by {km_y*1000/30:.0f} pixels")
print(f"model tiles  : about {tiles} (not all of them fall inside the basin)")
print(f"\nCPU estimate : {tiles*10/60:.0f} to {tiles*12/60:.0f} minutes for "
      "the full basin")

# %% [markdown]
# If that number is uncomfortable, notebook 2 has a `QUICK_DEMO` switch that
# classifies an 18 km box inside the basin instead of the whole thing. The
# science is identical; there is just less of it. Run the small version first,
# then start the full one and let it work while you follow along.

# %% [markdown]
# ## 7. Save the basin for notebook 2

# %%
out = wsrs.data_dir() / "basin.geojson"
basin.save_geojson(geom, out, properties={**site, "polygon_km2": poly_km2})
print(f"saved {out}")
print(f"{out.stat().st_size/1024:.0f} KB")

# %% [markdown]
# > **Where did it go?** With Google Drive connected, the file is in
# > `MyDrive/cuahsi_crop_map/`, and notebook 2 will find it there. Without
# > Drive it lives on this temporary machine only, and notebook 2 simply asks
# > the USGS for the basin again.

# %% [markdown]
# ## 8. Your turn: a basin near the conference
#
# The table below lists USGS stream gauges with a published drainage area in a
# box around Columbia, Missouri. Pick one between roughly 150 and 1500 km2.

# %%
import pandas as pd

near_columbia = basin.sites_in_bbox(-93.2, 38.5, -91.8, 39.5)
df = pd.DataFrame(near_columbia).dropna(subset=["drain_area_km2"])
df = df[(df.drain_area_km2 > 150) & (df.drain_area_km2 < 2000)]
print(f"{len(df)} candidate gauges")
df.sort_values("drain_area_km2").head(15)

# %% [markdown]
# **Guided activity.** Replace the `...` with the gauge number you picked, in
# quotes, and run the cell. Then answer the question in the last comment.

# %%
MY_SITE_ID = ...          # for example "06910230"

if MY_SITE_ID is ...:
    print("Replace ... with a gauge number in quotes, then run this cell again.")
else:
    my_site = basin.site_info(MY_SITE_ID)
    my_geom = basin.basin_polygon(MY_SITE_ID)
    my_km2 = basin.area_km2(my_geom)
    print(my_site["name"])
    print(f"polygon area       : {my_km2:,.0f} km2")
    print(f"published drainage : {my_site['drain_area_km2']:,.0f} km2")
    # Do the two areas agree within 10 percent?  Your answer: ...

# %% [markdown]
# <details>
# <summary><b>Show one solution</b></summary>
#
# `MY_SITE_ID = "06910230"` is Hinkson Creek at Columbia, Missouri. The
# polygon is about 184 km2 and the published drainage area is 181 km2, a
# difference under 2 percent, so the basin can be trusted.
# To run the whole workshop on your own basin, put the same number in
# `SITE_ID` in section 2 and run the notebook again from there.
#
# </details>
#
# **If you finish early**
#
# - `basin.upstream_sites(SITE_ID)` returns every USGS site on the river
#   network above your gauge. In a nested study you would classify the full
#   basin once and summarize crops for each sub-basin.
# - Try a site that is not a stream gauge, for example a groundwater well,
#   and read the error. Knowing how a service fails is part of knowing it.

# %% [markdown]
# ## What we did
#
# - pulled a watershed boundary from a public USGS API, with no account, no
#   download page, and no shapefile wrangling
# - checked it against an independent published number before trusting it
# - looked at it on a map, because polygons lie when you do not
# - sized the job in model tiles, so the next notebook holds no surprises
#
# **Next:** notebook 2 fetches Harmonized Landsat Sentinel-2 imagery for this
# basin, works out which scenes are clear enough to use, and runs the Prithvi
# foundation model to turn them into a crop map.
