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
# # Notebook 2. From raw imagery to a crop map
#
# **CUAHSI 2026. Agricultural Remote Sensing with Cloud Platforms and
# Geospatial Foundation Models**
#
# This is the core of the workshop.
#
# **By the end of this notebook you will be able to**
#
# 1. search NASA's Harmonized Landsat Sentinel-2 archive over a basin
# 2. judge which scenes are usable, from **cloud cover** and tile coverage
# 3. build the 18 band input that the model expects, and inspect it
# 4. run a geospatial foundation model and save a georeferenced crop map
#
# **Time:** about 45 minutes, most of it downloading and waiting on inference.
#
# **You need:** a free NASA Earthdata Login
# (<https://urs.earthdata.nasa.gov>). Make the account now if you do not have
# one; it takes two minutes.
#
# **Before you run anything, switch this notebook to a GPU.** In the Colab
# menu choose *Runtime*, *Change runtime type*, select **T4 GPU**, and save.
# Changing it later restarts the machine and loses what you have run. The
# notebook also works on a CPU; it is only slower.

# %% [markdown]
# ## Setup
#
# Same first cell as notebook 1: fetch the workshop code, install what is
# missing, connect Google Drive for your results.

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

import numpy as np
import matplotlib.pyplot as plt
import wsrs
from wsrs import basin, hls

env = wsrs.print_environment()
DEVICE = env["device"]
if env["in_colab"] and DEVICE == "cpu":
    print("\nNo GPU on this runtime. For a faster run: Runtime, Change runtime "
          "type, T4 GPU, then run this cell again. On CPU keep QUICK_DEMO = True.")
if KEEP_RESULTS_IN_DRIVE:
    wsrs.connect_drive()
print(f"Results folder: {wsrs.data_dir()}")

# %% [markdown]
# ## Configuration
#
# Two switches control how long this notebook takes.
#
# **`QUICK_DEMO = True`** classifies an 18 km box inside the basin, nine
# model tiles. On a Colab CPU that is roughly two minutes. Start here.
#
# **`QUICK_DEMO = False`** classifies the whole basin: 28 tiles for the
# default basin, five to six minutes on a CPU and much less on a GPU. Switch
# to it once the small version has worked end to end.
#
# **`YEAR`** is the growing season to map. The default, 2023, has a clear
# image in all three seasonal windows over the default basin. Section 4 shows
# how to check that for any other year before committing to it.

# %%
YEAR = 2023
QUICK_DEMO = True
DEMO_WIDTH_KM = 18

# Load the basin from notebook 1. If you skipped it, this fetches it again.
basin_file = wsrs.data_dir() / "basin.geojson"
if basin_file.exists():
    geom, props = basin.load_geojson(basin_file)
    SITE_ID = props.get("site_id", "USGS-05451210")
else:
    SITE_ID = "USGS-05451210"
    geom = basin.basin_polygon(SITE_ID)
    props = basin.site_info(SITE_ID)
    basin.save_geojson(geom, basin_file, properties=props)

full_bbox = basin.geom_bbox(geom)
bbox = (basin.subset_bbox(geom, DEMO_WIDTH_KM) if QUICK_DEMO else full_bbox)

print(f"basin  : {props.get('name', SITE_ID)}")
print(f"area   : {props.get('polygon_km2', basin.area_km2(geom)):,.0f} km2")
print(f"mode   : {'QUICK_DEMO box' if QUICK_DEMO else 'full basin'}")
print(f"bbox   : {', '.join(f'{v:.3f}' for v in bbox)}")
print(f"year   : {YEAR}")

# %% [markdown]
# ## 1. What is HLS, and why these six bands?
#
# NASA's **Harmonized Landsat Sentinel-2** product takes two satellite
# families, applies the same atmospheric correction, and puts both on one
# 30 m grid with matching band definitions. One Landsat satellite revisits
# every 16 days, and the two Sentinel-2 satellites together every 5 days.
# Harmonized, the land is observed every 2 to 3 days, which is what makes
# crop phenology trackable.
#
# We use the Sentinel-2 half, **S30**, version 2.0, because that is what the
# Prithvi crop model was fine-tuned on. Six bands:
#
# | channel | band | name | what it is good for |
# |---|---|---|---|
# | 1 | B02 | Blue | haze, water |
# | 2 | B03 | Green | peak vegetation reflectance |
# | 3 | B04 | Red | chlorophyll absorption |
# | 4 | B8A | Narrow NIR | canopy structure, biomass |
# | 5 | B11 | SWIR 1 | leaf and soil moisture |
# | 6 | B12 | SWIR 2 | residue, bare soil, senescence |
#
# Reflectance is stored as an integer scaled by 10000, with -9999 for no data.

# %% [markdown]
# ### Why three dates and not one
#
# In a single July image, corn and soybeans are both a dense green canopy and
# look nearly identical. What separates them is **timing**: when they emerge,
# how dark the canopy gets, and how they dry down. So we sample three windows
# across the growing season:
#
# | window | dates | what the ground looks like |
# |---|---|---|
# | early | May 1 to May 31 | bare soil, planting, emergence |
# | peak | Jul 1 to Jul 31 | full canopy |
# | late | Aug 25 to Sep 25 | senescence, corn and soybean diverge |
#
# Six bands times three dates is **18 channels**, and that is exactly the
# input the model takes.

# %%
for a, b, label in hls.DEFAULT_WINDOWS:
    print(f"{label:>5}: {YEAR}-{a} to {YEAR}-{b}")

# %% [markdown]
# ## 2. Log in to NASA Earthdata
#
# Running this cell will prompt for your Earthdata username and password.
# `persist=True` keeps them on this machine for the rest of the session, so
# you are asked only once.

# %%
import earthaccess

auth = earthaccess.login(persist=True)
print("authenticated:", auth.authenticated)

# %% [markdown]
# ## 3. Search the archive
#
# One query per seasonal window. We are asking: *what Sentinel-2 passes
# touched this box during these dates?*

# %%
found = hls.search_windows(bbox, YEAR)

for label, recs in found.items():
    tiles = sorted({r["tile"] for r in recs})
    print(f"{label:>5}: {len(recs):>3} granules over tiles {tiles}")

# %% [markdown]
# A **tile** is a fixed 110 km square in the Sentinel-2 grid, named like
# `T15TVG`. A basin that straddles a tile boundary needs granules from both,
# mosaicked together. That is handled for you later.

# %% [markdown]
# ## 4. The cloud problem
#
# This is the part that decides whether the whole exercise works.
#
# Iowa in July is cloudy. A satellite passing every few days still may not see
# the ground for two weeks. Our model needs one clear look in **each** of the
# three windows, so the binding constraint is not the total number of images,
# it is the worst window.
#
# Let us look at every candidate.

# %%
table = hls.scene_table(found)
print(f"{len(table)} granules found, {table.usable.sum()} of them usable\n")
table.sort_values(["window", "cloud_pct"]).head(20)

# %% [markdown]
# ### Two numbers, not one
#
# `cloud_pct` is the cloud cover reported for the **whole tile**.
#
# `coverage_pct` is how much of that tile actually contains data. Sentinel-2
# swaths clip tile corners, so a granule can report **almost no cloud while
# covering only part of the tile**: the cloud statistic is computed over the
# part that exists. Over the default basin, the granule of September 1, 2023
# on tile T15TVG reports 0 percent cloud and covers 56 percent of the tile.
# Pick on cloud alone and you will eventually stack a beautiful, half empty
# image and wonder why part of your basin is missing.
#
# The plot below shows why both matter. Green points are what we want: low
# cloud and full coverage.

# %%
fig, axes = plt.subplots(1, 2, figsize=(13, 4.6))

ax = axes[0]
for label, grp in table.groupby("window"):
    ax.scatter(grp.coverage_pct, grp.cloud_pct, s=42, alpha=0.75, label=label)
ax.axhline(30, color="#c0392b", ls="--", lw=1.2)
ax.axvline(90, color="#c0392b", ls="--", lw=1.2)
ax.add_patch(plt.Rectangle((90, -2), 12, 32, color="#2E7D32", alpha=0.10))
ax.text(91, 2, "usable", color="#2E7D32", fontweight="bold", fontsize=10)
ax.set_xlabel("tile coverage (percent)")
ax.set_ylabel("cloud cover (percent)")
ax.set_title("Every candidate granule", fontweight="bold")
ax.legend(frameon=False)
ax.grid(lw=0.3, alpha=0.4)

ax = axes[1]
order = [w[2] for w in hls.DEFAULT_WINDOWS]
counts = [int(table[(table.window == w) & table.usable].shape[0])
          for w in order]
bars = ax.bar(order, counts, color=["#2E7D32" if c else "#c0392b"
                                    for c in counts], width=0.55)
for b, c in zip(bars, counts):
    ax.text(b.get_x() + b.get_width() / 2, c + 0.06, str(c), ha="center",
            fontweight="bold")
ax.set_ylabel("usable granules")
ax.set_title("Usable scenes per window (we need at least one each)",
             fontweight="bold")
ax.grid(axis="y", lw=0.3, alpha=0.4)
plt.tight_layout()
plt.show()

# %% [markdown]
# **If any bar is zero**, this year cannot be classified properly for this
# basin. Real options, in order of preference: widen that window by a week,
# accept a cloudier scene and inspect the result honestly, or choose a
# different year. Pretending a 70 percent cloudy scene is fine produces a map
# that looks plausible and is wrong, which is the worst outcome in this field.

# %% [markdown]
# ### A quick look at the cloud record across years
#
# Out of curiosity, and because it explains why the HLS archive effectively
# starts in 2016: Sentinel-2A launched mid 2015, Sentinel-2B joined in 2017
# and halved the revisit time. Before that, there is no S30 at all.
#
# 2024 is in the list on purpose: over the default basin it is a cloudy
# year, and the table shows it.
#
# (Skip this cell if you are short on time; it makes a few extra queries.)

# %%
RUN_MULTIYEAR_CHECK = True

if RUN_MULTIYEAR_CHECK:
    rows = []
    for yr in sorted({2016, 2019, 2024, YEAR}):
        f = hls.search_windows(bbox, yr)
        t = hls.scene_table(f)
        rows.append({"year": yr, "granules": len(t),
                     "usable": int(t.usable.sum()),
                     "min_cloud": round(float(t.cloud_pct.min()), 1)
                     if len(t) else None})
    import pandas as pd
    print(pd.DataFrame(rows).to_string(index=False))

# %% [markdown]
# ## 5. Choose the scenes
#
# For each window we first look for **one date** that is clear and complete
# on every tile, so that the whole basin is seen on the same day and the tiles
# join without a seam. If no such date exists, we take the clearest complete
# granule tile by tile. If the best available only partly covers a tile, a
# second date fills the gap.

# %%
picks = hls.pick_scenes(found, cloud_max=30, coverage_min=90)

n_files = sum(len(hls.band_urls(r)) for sel in picks for r in sel)
print(f"\n{sum(len(s) for s in picks)} granules, {n_files} files to download")

# %% [markdown]
# ## 6. Download
#
# Six bands plus the Fmask quality layer per granule, roughly 20 to 30 MB
# each. Files are verified after download: a dropped connection can leave a
# file that is the right size but contains an error page, and that failure
# mode is nasty because it only surfaces much later.

# %%
raw_dir = wsrs.data_dir("raw")
hls.download(picks, raw_dir)

# %% [markdown]
# ## 7. Look at the data
#
# Never trust imagery you have not looked at. We build the stack first, then
# inspect it.

# %%
stack_path = wsrs.data_dir() / f"stack_{YEAR}.tif"
hls.build_stack(picks, raw_dir, bbox, stack_path)

import rasterio

with rasterio.open(stack_path) as src:
    stack = src.read()
    stack_profile = src.profile
print(f"\nstack shape: {stack.shape}  (18 bands, rows, cols)")
print(f"valid pixels in band 1: {100*(stack[0] != hls.NODATA).mean():.1f} percent")

# %% [markdown]
# ### True color, three dates
#
# This is the ground truth of your experiment. Look for: clouds, haze, missing
# wedges, and the obvious seasonal progression from bare soil to green canopy.

# %%
fig, axes = plt.subplots(1, 3, figsize=(15, 5.4))
labels = [w[2] for w in hls.DEFAULT_WINDOWS]
dates = [sel[0]["date"] for sel in picks]
for t, ax in enumerate(axes):
    ax.imshow(hls.stretch_rgb(stack, t))
    ax.set_title(f"{labels[t]}  {dates[t]}", fontweight="bold")
    ax.set_axis_off()
plt.suptitle("True color (red, green, blue)", fontweight="bold", y=1.02)
plt.tight_layout()
plt.show()

# %% [markdown]
# ### False color: near infrared
#
# Swap red for the near infrared band and living vegetation becomes bright
# red. The seasonal story is far easier to read this way: dark in May, blazing
# in July, fading by September.

# %%
fig, axes = plt.subplots(1, 3, figsize=(15, 5.4))
for t, ax in enumerate(axes):
    ax.imshow(hls.stretch_rgb(stack, t, idx=hls.FALSE_COLOR_IDX))
    ax.set_title(f"{labels[t]}  {dates[t]}", fontweight="bold")
    ax.set_axis_off()
plt.suptitle("False color (NIR, red, green). Red is green vegetation.",
             fontweight="bold", y=1.02)
plt.tight_layout()
plt.show()

# %% [markdown]
# ### The actual cloud fraction over your basin
#
# Scene level cloud percentages describe a 110 km tile. What matters is your
# basin. Fmask is HLS's per pixel quality band, and bits 1 to 3 flag cloud
# shadow, cloud adjacency and cloud.

# %%
frac = hls.fmask_fraction(picks, raw_dir, bbox)
for label, date, f in zip(labels, dates, frac):
    bar = "#" * int(f / 2)
    flag = "  <- consider another scene" if f > 10 else ""
    print(f"{label:>5} {date}: {f:5.1f} percent cloud affected {bar}{flag}")

# %% [markdown]
# ### Spectral signatures: what the model actually sees
#
# A pixel is a vector of 18 numbers. Below are the mean reflectance curves for
# a few hand picked locations. Even before any machine learning, you can see
# that a dense July canopy has high NIR and low red, while bare soil is flat
# and bright in the SWIR.

# %%
h, w = stack.shape[1:]
samples = {"center": (h // 2, w // 2),
           "upper left": (h // 4, w // 4),
           "lower right": (3 * h // 4, 3 * w // 4)}

fig, ax = plt.subplots(figsize=(11, 4.4))
x = np.arange(18)
for name, (r, c) in samples.items():
    vals = stack[:, r, c].astype(float)
    vals[vals == hls.NODATA] = np.nan
    ax.plot(x, vals / 10000, marker="o", ms=4, lw=1.6, label=name)
for t in range(3):
    ax.axvspan(t * 6 - 0.5, t * 6 + 5.5, color="k",
               alpha=0.05 if t % 2 == 0 else 0.0)
    ax.text(t * 6 + 2.5, ax.get_ylim()[1] * 0.95, labels[t], ha="center",
            fontsize=10, fontweight="bold")
ax.set_xticks(x, (hls.BAND_LABELS * 3), rotation=45, ha="right", fontsize=8)
ax.set_ylabel("surface reflectance")
ax.set_title("One pixel, 18 numbers: the model's input vector",
             fontweight="bold")
ax.legend(frameon=False)
ax.grid(lw=0.3, alpha=0.4)
plt.tight_layout()
plt.show()

# %% [markdown]
# ## 8. The model
#
# **Prithvi-EO** is a geospatial foundation model from NASA and IBM. It was
# pretrained on a very large amount of HLS imagery over the continental United
# States using masked autoencoding: hide patches of the image, learn to
# reconstruct them. Doing that well requires an internal representation of
# what landscapes look like and how they change through a season.
#
# We use the **crop classification fine-tune**, which was then trained on USDA
# Cropland Data Layer labels to map 13 classes.
#
# | | |
# |---|---|
# | input | 6 bands x 3 dates x 224 x 224 |
# | output | 13 classes per 30 m pixel |
# | encoder | temporal Vision Transformer, 6 blocks, 8 heads, patch 16 |
# | size | about 140 million parameters: 44 million in the encoder, the rest in the layers that turn its output back into a map |
#
# The "100M" in the model name refers to the pretrained foundation model that
# the encoder comes from.
#
# The official release depends on the legacy mmsegmentation stack, which is
# painful to install. `wsrs/model.py` reimplements the architecture in plain
# PyTorch and loads the published weights unchanged, so `pip install torch` is
# the only requirement. Have a look at it if you are curious; it is under 400
# lines.
#
# The next cell downloads the weights, 1.7 GB, from Hugging Face. In Colab a
# warning about a missing `HF_TOKEN` may appear; it is harmless, because the
# model is public.

# %%
from huggingface_hub import hf_hub_download
from wsrs import model as prithvi

REPO = "ibm-nasa-geospatial/Prithvi-EO-1.0-100M-multi-temporal-crop-classification"
ckpt = hf_hub_download(REPO,
                       "multi_temporal_crop_classification_Prithvi_100M.pth")
print(f"checkpoint: {Path(ckpt).stat().st_size/1e9:.2f} GB")

net = prithvi.load_model(ckpt, device=DEVICE)
n_params = sum(p.numel() for p in net.parameters())
n_encoder = sum(p.numel() for p in net.backbone.parameters())
print(f"loaded {n_params/1e6:.0f} million parameters onto {DEVICE} "
      f"({n_encoder/1e6:.0f} million in the encoder)")

# %% [markdown]
# ### The 13 classes

# %%
for i, name in enumerate(prithvi.CLASSES, start=1):
    print(f"{i:>3}  {name}")
print("\n  0  no data (we use it for 'outside the basin' as well)")

# %% [markdown]
# ### Normalization
#
# The model expects each band standardized with the mean and standard
# deviation of the training set, not raw reflectance. These constants ship
# with the published config and must be used exactly.

# %%
print("band means :", prithvi.MEANS)
print("band stds  :", prithvi.STDS)

# %% [markdown]
# ## 9. Run inference
#
# The model sees 224 by 224 tiles, so we slide a window across the basin and
# classify each tile. Tiles that fall entirely outside the basin are skipped,
# which is most of the saving in an irregularly shaped watershed.

# %%
import time

import torch
from rasterio.features import geometry_mask
from rasterio.warp import transform_geom

IMG = 224

with rasterio.open(stack_path) as src:
    transform, W, H = src.transform, src.width, src.height
geom_proj = transform_geom("EPSG:4326", str(stack_profile["crs"]), geom)
inside = geometry_mask([geom_proj], out_shape=(H, W), transform=transform,
                       invert=True)

xs = sorted(set(list(range(0, max(W - IMG, 0) + 1, IMG)) + [max(W - IMG, 0)]))
ys = sorted(set(list(range(0, max(H - IMG, 0) + 1, IMG)) + [max(H - IMG, 0)]))
windows = [(y, x) for y in ys for x in xs
           if inside[y:y + IMG, x:x + IMG].any()]
print(f"{len(windows)} tiles to classify "
      f"({len(xs)*len(ys)} in the box, the rest fall outside the basin)")

pred = np.zeros((H, W), dtype=np.uint8)
t0 = time.time()
for i, (y, x) in enumerate(windows, start=1):
    chip = stack[:, y:y + IMG, x:x + IMG]
    if chip.shape[1] < IMG or chip.shape[2] < IMG:
        pad = np.full((18, IMG, IMG), hls.NODATA, np.int16)
        pad[:, :chip.shape[1], :chip.shape[2]] = chip
        chip = pad
    nodata = np.any(chip == hls.NODATA, axis=0)
    if nodata.all():
        continue
    xt = torch.from_numpy(prithvi.normalize(chip)).reshape(6, 3, IMG, IMG)
    with torch.no_grad():
        logits = net(xt[None].to(DEVICE))[0]
    tile = (logits.argmax(0).cpu().numpy() + 1).astype(np.uint8)
    tile[nodata] = 0
    hh = min(IMG, H - y)
    ww = min(IMG, W - x)
    pred[y:y + hh, x:x + ww] = tile[:hh, :ww]
    if i % 5 == 0 or i == len(windows):
        el = time.time() - t0
        print(f"  {i}/{len(windows)} tiles, {el:5.1f}s elapsed, "
              f"{el/i:4.1f}s per tile", flush=True)

pred[~inside] = 0
print(f"\ndone in {time.time()-t0:.0f} seconds on {DEVICE}")

# %% [markdown]
# ## 10. First look at the result

# %%
from wsrs import viz

fig, ax = plt.subplots(figsize=(10, 8))
viz.show_classified(pred, ax=ax,
                    title=f"{props.get('name','basin')}  {YEAR}")
plt.show()

areas = viz.class_area_table(pred)
areas

# %% [markdown]
# **Sanity checks worth doing every single time**
#
# - Do field boundaries look like fields, with straight edges, or is the map
#   speckled noise?
# - Is corn plus soybeans close to what you expect? For the South Fork basin
#   the USDA Cropland Data Layer of 2023 reports about 83 percent. For a
#   Missouri basin with more pasture and forest, expect less.
# - Do the towns, rivers and woodlots land where the satellite image showed
#   them? Flip back to the true color figure and compare.
# - Are there classes that make no sense here, for example cotton in Iowa?
#   The model was trained nationally and can emit them as noise.

# %%
implausible = {k: v for k, v in viz.IMPLAUSIBLE_MIDWEST.items()
               if (pred == k).any()}
if implausible:
    tot = sum(100 * (pred == k).sum() / max((pred > 0).sum(), 1)
              for k in implausible)
    print(f"classes unlikely in the Midwest are present: "
          f"{list(implausible.values())}, {tot:.2f} percent of the basin")
    print("small amounts are normal label noise inherited from the training "
          "data. A large amount means something is wrong with the input.")
else:
    print("no implausible classes present")

# %% [markdown]
# ## 11. Save the map
#
# Written as a uint8 GeoTIFF with the color table embedded, so it opens
# already styled in QGIS or ArcGIS.

# %%
pred_path = wsrs.data_dir() / f"crop_map_{YEAR}.tif"
viz.save_classified(pred, stack_path, pred_path)
for k, v in viz.describe_raster(pred_path).items():
    print(f"{k:>14}: {v}")

# %% [markdown]
# ## 12. Your turn: is another year usable?
#
# Cloud cover decided which scenes we used. Before mapping a different year,
# check it the same way. **Guided activity:** replace the `...` with a year
# and run the cell. The search needs no download.

# %%
OTHER_YEAR = ...          # for example 2024

if OTHER_YEAR is ...:
    print("Replace ... with a year, then run this cell again.")
else:
    other = hls.scene_table(hls.search_windows(bbox, OTHER_YEAR))
    per_window = (other[other.usable].groupby("window").size()
                  .reindex([w[2] for w in hls.DEFAULT_WINDOWS], fill_value=0))
    print(f"{OTHER_YEAR}: {len(other)} granules, {int(other.usable.sum())} usable")
    print(per_window.to_string())
    # Which window is the weakest link?  Your answer: ...
    # Would you trust a map of this year?  Your answer: ...

# %% [markdown]
# <details>
# <summary><b>Show one solution</b></summary>
#
# `OTHER_YEAR = 2024` over the South Fork Iowa River returns about 67
# granules, of which about 12 are usable, against 24 usable in 2023. May and
# July are the weak windows: the clearest dates that cover the whole basin
# still carry roughly 20 to 30 percent cloud. A map of 2024 can be made, but
# it deserves a careful look at the true color images before anyone uses it.
#
# </details>

# %% [markdown]
# ## What we did
#
# - searched the NASA archive of harmonized imagery with three lines of Python
# - treated cloud cover as a first class problem rather than an afterthought,
#   and used both cloud and coverage to choose scenes
# - looked at the imagery in true color, false color, and as spectral
#   signatures before feeding it to anything
# - built the 18 channel input a geospatial foundation model expects
# - ran a geospatial foundation model and produced a crop map for a real
#   watershed, on ordinary cloud hardware
#
# **Next:** notebook 3 turns this raster into an interactive map, exports a
# cloud optimized GeoTIFF and a watershed shapefile, and gets them ready for
# Google Earth Engine.
