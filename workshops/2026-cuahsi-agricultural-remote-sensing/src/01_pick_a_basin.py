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
# **You do not need a GitHub account.** The workshop repository is public, so
# the cell copies it without a login, a password or a token. The comments
# inside the cell say what each line does.
#
# Colab will ask permission to access Drive: choose your account, tick
# **Select all**, and continue. If you prefer not to, set
# `KEEP_RESULTS_IN_DRIVE = False`; the later notebooks then fall back to the
# example data shipped with the workshop.

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

# Load the workshop helper package. This works only after the setup above.
import wsrs
from wsrs import basin       # the watershed functions used in this notebook

# Print the Python version and the hardware of this machine.
wsrs.print_environment()

# Connect Google Drive, so that the results outlive this temporary machine.
if KEEP_RESULTS_IN_DRIVE:
    wsrs.connect_drive()

# Show where the code is and where the results will be saved.
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
# The default is the South Fork Iowa River, a corn and soybean basin in
# central Iowa. It is a good teaching case: corn and soybeans cover about 83
# percent of it in the USDA Cropland Data Layer of 2023, and it is small
# enough to classify quickly.
#
# **Change `SITE_ID` to any USGS stream gauge** and the rest of the workshop
# follows along. Section 6 shows how to find one near you.

# %%
# The USGS number of the stream gauge. Change it to work on another basin.
SITE_ID = "05451210"   # South Fork Iowa River NE of New Providence, IA

# Ask the USGS site file (NWIS) what this gauge is. The answer is a small
# dictionary: name, coordinates, drainage area and a few more items.
site = basin.site_info(SITE_ID)

# The loop prints the dictionary, one line per item.
# k is the label of the item and v is its value.
for k, v in site.items():
    print(f"{k:>18}: {v}")

# %% [markdown]
# `drain_area_km2` is the official published drainage area. Keep it in mind:
# in a moment we will compare it against the polygon we download, which is a
# free and surprisingly effective sanity check.

# %% [markdown]
# ## 3. Ask NLDI for the basin

# %%
# Ask NLDI for the land that drains to the gauge. The answer is a polygon.
geom = basin.basin_polygon(SITE_ID)

# Measure the polygon: its area in km2, and the box that contains it
# (west, south, east, north, in degrees).
poly_km2 = basin.area_km2(geom)
bbox = basin.geom_bbox(geom)

# Print the area of our polygon next to the official drainage area.
print(f"geometry type     : {geom['type']}")
print(f"polygon area      : {poly_km2:,.1f} km2")
print(f"NWIS drainage area: {site['drain_area_km2']:,.1f} km2")

# Compare the two areas as a percent difference.
# Under 10 percent we call it good agreement.
if site["drain_area_km2"]:
    diff = 100 * abs(poly_km2 - site["drain_area_km2"]) / site["drain_area_km2"]
    verdict = "good agreement" if diff < 10 else "CHECK THIS"
    print(f"difference        : {diff:.1f} percent  ({verdict})")

# Print the box. Notebook 2 uses it to search for satellite images.
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
from wsrs import viz      # the map and figure helpers of this workshop

# Build an interactive map centered on the basin (it uses the folium library).
# The basin outline is drawn in red, with a blue marker on the gauge.
# zoom=10 shows the whole basin. A larger number zooms in.
# The background is a satellite image.
m = viz.basin_map(geom, site=site, zoom=10)

# A map written alone on the last line of a cell is displayed below the cell.
m

# %% [markdown]
# Pan around and zoom in. You should see the field boundaries, and the gauge
# marker sitting at the basin outlet. If the marker is in the middle of the
# polygon rather than at its edge, something is wrong.
#
# The background comes from Esri World Imagery. The next cell adds a box in
# the corner of the map to switch to the USGS topographic map, which shows
# the names of towns, rivers and counties.

# %% [markdown]
# ## 5. The river network above the gauge
#
# NLDI can also return every flowline upstream. This is not strictly needed
# for the crop map, but it makes the idea of "upstream contributing area"
# concrete, and it is one more HTTP call.

# %%
# Ask NLDI for every river reach upstream of the gauge, up to 200 km away.
flowlines = basin.upstream_flowlines(SITE_ID, distance_km=200)

# Count the reaches that came back.
n_reaches = len(flowlines.get("features", []))
print(f"{n_reaches} river reaches upstream of {SITE_ID}")

import folium  # noqa: E402     (the interactive map library)

# Add the rivers to the map made in section 4, as thin blue lines.
folium.GeoJson(flowlines, name="Upstream rivers",
               style_function=lambda _: {"color": "#1f78b4",
                                         "weight": 1.6}).add_to(m)

# Add the layer box in the upper right corner of the map. It switches the
# background (satellite or topographic map) and turns the basin and the
# rivers on and off.
folium.LayerControl(collapsed=False).add_to(m)

# Show the map again, now with the rivers.
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

# The four sides of the box around the basin, in degrees.
west, south, east, north = bbox

# Turn degrees into kilometers. One degree of latitude is about 111 km.
# One degree of longitude gets shorter away from the equator, which is
# what the cosine accounts for.
km_x = (east - west) * 111.0 * math.cos(math.radians((south + north) / 2))
km_y = (north - south) * 111.0

# One model tile is 224 pixels of 30 m, that is 6.72 km on a side.
# Count the tiles that fit across and down, rounded up.
tiles = math.ceil(km_x / 6.72) * math.ceil(km_y / 6.72)

# Print the size of the job, and a time estimate at 10 to 12 s per tile.
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
# The file name. wsrs.data_dir() is the results folder: your Google Drive
# when it is connected, otherwise the data folder of the workshop.
out = wsrs.data_dir() / "basin.geojson"

# Write the polygon to the file, with the gauge information attached.
basin.save_geojson(geom, out, properties={**site, "polygon_km2": poly_km2})

# Confirm where the file went and how big it is.
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
import pandas as pd      # the table library

# Ask the USGS for the stream gauges inside a box around Columbia, Missouri.
# The four numbers are west, south, east and north, in degrees.
near_columbia = basin.sites_in_bbox(-93.2, 38.5, -91.8, 39.5)

# Put the gauges in a table. Drop those without a published drainage area.
df = pd.DataFrame(near_columbia).dropna(subset=["drain_area_km2"])

# Keep the basins of a workable size, between 150 and 2000 km2.
df = df[(df.drain_area_km2 > 150) & (df.drain_area_km2 < 2000)]
print(f"{len(df)} candidate gauges")

# Show the 15 smallest basins, smallest first.
df.sort_values("drain_area_km2").head(15)

# %% [markdown]
# **Guided activity.** Replace the `...` with the gauge number you picked, in
# quotes, and run the cell. Then answer the question in the last comment.

# %%
MY_SITE_ID = ...          # for example "06910230"

# The three dots are a placeholder. Until you replace them, the cell only
# prints a reminder.
if MY_SITE_ID is ...:
    print("Replace ... with a gauge number in quotes, then run this cell again.")
else:
    # The same three steps as above: gauge information, polygon, area.
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
