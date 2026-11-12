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
# # Notebook 4 (optional). Check the map against the Cropland Data Layer
#
# **CUAHSI 2026. Agricultural Remote Sensing with Cloud Platforms and
# Geospatial Foundation Models**
#
# The honest question about any classification: how often does it agree with
# an independent reference? The USDA publishes the Cropland Data Layer (CDL)
# every year on the same 30 m grid as our map, and Google Earth Engine hosts
# all of it. This notebook compares the two.
#
# **By the end of this notebook you will be able to**
#
# 1. read an Earth Engine asset from Python
# 2. regroup a reference map into the classes of your own map
# 3. report agreement per class, and say what the numbers do not mean
#
# **Time:** about 15 minutes.
#
# **You need:** your crop map uploaded as an Earth Engine image asset. The
# steps are in `GEE/README.md`; do those first.

# %% [markdown]
# ## Setup
#
# Same first cell as the other notebooks: it copies the workshop code and
# installs what is missing. No GitHub account is needed, because the
# repository is public. The comments inside the cell say what each line does.

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
    # We try to import two of them. If one is missing, pip installs the
    # list in requirements.txt. Nothing is installed twice.
    try:
        import ee, pandas  # noqa: F401
    except ImportError:
        print("Installing the workshop requirements, about one minute ...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r",
                        "requirements.txt"], check=True)
    return root


# Run the setup. ROOT is the workshop folder on this machine.
ROOT = setup_workshop()

# Load the libraries used in this notebook.
import numpy as np        # arrays and math
import pandas as pd       # tables
import wsrs               # the workshop helper package

# The 13 class names of our map, and the list that links each class of the
# Cropland Data Layer to one of them.
from wsrs.classes import CDL_DEFAULT_CLASS, CLASSES, cdl_remap_lists

# Print the Python version and the hardware of this machine.
wsrs.print_environment()

# %% [markdown]
# ## Configuration
#
# `PROJECT` is your Earth Engine Cloud project id. It is shown in the top
# right corner of the Code Editor at <https://code.earthengine.google.com>.
#
# `ASSET_NAME` is the name you gave the image when you uploaded it, and `YEAR`
# is the growing season it shows. The defaults match the example in the `GEE`
# folder.

# %%
PROJECT = "your-cloud-project-id"         # your Earth Engine Cloud project
ASSET_NAME = "south_fork_crop_map_2023"   # the name of your uploaded image
YEAR = 2023                               # the growing season it shows

# The full address of the image in Earth Engine, built from the two names.
ASSET = f"projects/{PROJECT}/assets/{ASSET_NAME}"
print("asset:", ASSET)

# %% [markdown]
# ## 1. Connect to Earth Engine
#
# The first run opens a Google sign in and asks permission. `ee.Initialize`
# then ties the session to your Cloud project.

# %%
import ee          # the Earth Engine library for Python

# Try to start the session. If Earth Engine does not know you yet on this
# machine, sign in first (a Google window opens), then start the session.
try:
    ee.Initialize(project=PROJECT)
except Exception:
    ee.Authenticate()
    ee.Initialize(project=PROJECT)

# Ask Earth Engine to describe your image. This is also a test of the
# connection and of the asset name.
info = ee.data.getAsset(ASSET)       # fails here if the asset id is wrong
print("connected")
print("asset type:", info["type"])
print("bands     :", [b["id"] for b in info.get("bands", [])])

# %% [markdown]
# If the cell above fails with *not found*, open the Assets tab of the Code
# Editor, click your image, and compare its id with the one printed in the
# configuration cell.

# %% [markdown]
# ## 2. Your map and the reference, on the same legend
#
# The CDL has more than a hundred classes. The crosswalk in
# `wsrs/classes.py` groups them into the 13 classes our model predicts: named
# crops go to their own class, land cover codes to the matching land cover
# class, everything else to Other.

# %%
# ---- Our map ----
# Load the uploaded image, keep its first band and name that band "pred"
# (for prediction).
crop_map = ee.Image(ASSET).select(0).rename("pred").toInt()

# Hide the pixels with the value 0.
crop_map = crop_map.updateMask(crop_map.gt(0))        # 0 is outside the basin

# ---- The reference ----
# The Cropland Data Layer collection holds one image per year.
# Keep the image of our year.
cdl_year = (ee.ImageCollection("USDA/NASS/CDL")
            .filter(ee.Filter.calendarRange(YEAR, YEAR, "year")))

# Stop here with a clear message if that year is not available.
assert cdl_year.size().getInfo() > 0, (
    f"The Cropland Data Layer for {YEAR} is not in Earth Engine yet. It is "
    "published early in the following year. Compare a map of an earlier year.")

# Two lists of the same length: the CDL class numbers, and for each of
# them the class number of our own legend.
cdl_from, cdl_to = cdl_remap_lists()

# Replace every CDL number by our class number. A CDL class that is not in
# the list becomes class 13 (Other). Name the band "ref" (for reference).
cdl13 = (cdl_year.first().select("cropland")
         .remap(cdl_from, cdl_to, CDL_DEFAULT_CLASS).rename("ref").toInt())
cdl13 = cdl13.updateMask(cdl13.gt(0))

# ---- The two together ----
# One image with two bands: "pred" (our map) and "ref" (the CDL).
pair = crop_map.addBands(cdl13)

# Keep only pixels where both maps have a value.
pair = pair.updateMask(pair.select("pred").mask().And(pair.select("ref").mask()))

# The area to compare: the footprint of our map.
region = crop_map.geometry()
print(f"reference: USDA Cropland Data Layer {YEAR}, regrouped to 13 classes")

# %% [markdown]
# ## 3. How much of the basin agrees
#
# The share of pixels where the two maps carry the same class. Row crops
# dominate the Midwest, so this number is mostly about corn and soybeans.

# %%
# The pixel grid of our map. The comparison is made on this grid.
proj = ee.Image(ASSET).projection()      # compare on the grid of our map

# A new image: 1 where the two maps carry the same class, 0 where they differ.
agree = pair.select("pred").eq(pair.select("ref")).rename("agree")

# The mean of that image over the basin is the share of pixels that agree.
# Earth Engine computes it on its own servers. getInfo() brings the answer
# back to this notebook.
overall = agree.reduceRegion(reducer=ee.Reducer.mean(), geometry=region,
                             crs=proj, scale=30, maxPixels=1e9,
                             tileScale=4).getInfo()
print(f"pixel agreement with the CDL: {100 * overall['agree']:.1f} percent")

# %% [markdown]
# ## 4. Agreement per class
#
# One number hides the classes that cover little area. A cross tabulation
# counts, for every pair (CDL class, map class), the pixels that fall in it.
# We pack the two class numbers into one code, `100 x CDL + map`, and ask
# Earth Engine for the histogram of that code over every pixel of the basin.

# %%
# One number per pixel that holds both classes: 100 x CDL class + map class.
# For example 304 means that the CDL says corn (3) and our map says
# soybeans (4).
code = (pair.select("ref").multiply(100).add(pair.select("pred"))
        .rename("code").toInt())

# Count how many pixels carry each code, over the whole basin.
# The answer is a dictionary: code, then number of pixels.
hist = code.reduceRegion(reducer=ee.Reducer.frequencyHistogram(),
                         geometry=region, crs=proj, scale=30, maxPixels=1e9,
                         tileScale=4).get("code").getInfo()

# An empty table of counts, 14 by 14, for the class numbers 0 to 13.
M = np.zeros((14, 14))                   # rows: CDL, columns: our map

# The loop splits each code back into its two classes and stores the count
# in the table. value // 100 is the CDL class, value % 100 is the map class.
for key, count in hist.items():
    value = int(float(key))
    M[value // 100, value % 100] += count

total = M.sum()          # all the pixels that were compared

# The loop builds one line of results per class.
rows = []
for i in range(1, 14):
    # The pixels of class i in the CDL (row i) and in our map (column i).
    cdl_total, map_total = M[i].sum(), M[:, i].sum()

    # Skip a class that appears in neither map.
    if cdl_total == 0 and map_total == 0:
        continue

    # M[i, i] counts the pixels where both maps say class i.
    rows.append({
        "class": CLASSES[i - 1],
        "CDL %": round(100 * cdl_total / total, 1),
        "our map %": round(100 * map_total / total, 1),
        "producer's agreement %": round(100 * M[i, i] / cdl_total, 1)
        if cdl_total else np.nan,
        "user's agreement %": round(100 * M[i, i] / map_total, 1)
        if map_total else np.nan})

# Turn the lines into a table, and print the overall agreement again as a
# check: it is the share of pixels on the diagonal of the count table.
per_class = pd.DataFrame(rows)
print(f"{int(total):,} pixels compared, "
      f"{100 * np.trace(M) / total:.1f} percent of them on the diagonal")
per_class

# %% [markdown]
# **How to read it**
#
# - *Producer's agreement*: of the pixels the CDL calls corn, how many did
#   our map call corn? A low value means the map misses that class.
# - *User's agreement*: of the pixels our map calls corn, how many does the
#   CDL also call corn? A low value means the map uses that class too freely.
#
# Corn and soybeans should score much higher than the small classes. Part of
# every gap is the model, part is the crosswalk, and part is the CDL, which
# is itself a model product with its own errors. This is an agreement
# assessment, not an accuracy against ground truth.

# %% [markdown]
# ## 5. Your turn: read one class
#
# **Guided activity.** Replace the `...` with a class name from the table, in
# quotes, and run the cell.

# %%
MY_CLASS = ...            # for example "Soybeans"

# The three dots are a placeholder. Until you replace them, the cell only
# prints a reminder.
if MY_CLASS is ...:
    print("Replace ... with a class name in quotes, then run this cell again.")
else:
    # Keep the line of the table that matches your class, and print it.
    row = per_class[per_class["class"] == MY_CLASS]
    print(row.to_string(index=False))
    # Which is lower for this class, producer's or user's agreement?  ...
    # What does that say about how the map errs?                       ...

# %% [markdown]
# <details>
# <summary><b>Show one solution</b></summary>
#
# With `MY_CLASS = "Soybeans"` and the example map of 2023, the instructors
# obtained a producer's agreement of about 94 percent and a user's agreement
# of about 89 percent. The map rarely misses a soybean field that the CDL has
# (few omissions). It calls soybeans somewhat too freely: about one in ten of
# its soybean pixels is corn, developed land or grassland in the CDL
# (commission). The overall agreement for that map is about 86 percent, with
# corn at 95 percent (producer's) and 93 percent (user's). Grassland and
# pasture are the weak class: the map finds only about a third of what the
# CDL labels as natural vegetation.
#
# </details>

# %% [markdown]
# ## What we did
#
# - read our own map as an Earth Engine asset from Python
# - regrouped the Cropland Data Layer into the model's 13 classes
# - measured agreement two ways: over the whole basin, and class by class
#   from a cross tabulation of every pixel
#
# The same three steps work for any year the CDL covers and any basin you
# map with notebooks 1 to 3.
