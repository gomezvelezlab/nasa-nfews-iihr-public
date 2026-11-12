"""
wsrs: helpers for the CUAHSI 2026 workshop
"Agricultural Remote Sensing with Cloud Platforms and Geospatial Foundation Models"

Modules
    basin  watershed boundaries from the USGS NLDI and NWIS web services
    hls    Harmonized Landsat Sentinel-2 search, cloud screening, stacking
    model  standalone PyTorch Prithvi-EO-1.0-100M crop classifier
    viz    colors, legends, folium maps, cloud optimized GeoTIFF export

The heavy import (torch, inside model) is lazy, so notebook 1 stays light.
"""
from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

__version__ = "1.0.0"
_LAZY = {"basin", "hls", "model", "viz"}


def __getattr__(name):
    if name in _LAZY:
        return importlib.import_module(f".{name}", __name__)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(list(globals()) + list(_LAZY))


def environment() -> dict:
    """Where are we running, and what hardware is there?

    Printed at the top of each notebook so that when something behaves oddly
    during the workshop the answer is already on screen.
    """
    info = {"python": sys.version.split()[0],
            "in_colab": "google.colab" in sys.modules,
            "cwd": str(Path.cwd()),
            "cpu_count": os.cpu_count()}
    try:
        import torch
        info["torch"] = torch.__version__
        info["gpu"] = (torch.cuda.get_device_name(0)
                       if torch.cuda.is_available() else None)
        info["device"] = "cuda" if torch.cuda.is_available() else "cpu"
    except ImportError:
        info["torch"] = None
        info["device"] = "cpu"
    try:
        with open("/proc/meminfo") as f:
            kb = int(f.readline().split()[1])
        info["ram_gb"] = round(kb / 1e6, 1)
    except OSError:
        pass
    return info


def print_environment() -> dict:
    info = environment()
    print(f"Python {info['python']}   torch {info.get('torch')}")
    print(f"Running in Colab: {info['in_colab']}")
    print(f"Device: {info.get('device')}"
          + (f"  ({info['gpu']})" if info.get("gpu") else "  (no GPU found,"
             " which is fine, the notebook is sized for CPU)"))
    print(f"CPU cores: {info['cpu_count']}   RAM: {info.get('ram_gb', '?')} GB")
    return info


WORKSPACE_ENV = "WSRS_WORKSPACE"
EXAMPLE_YEAR = 2023


def repo_root() -> Path:
    """The workshop folder that holds wsrs/, notebooks/, GEE/ and data/."""
    return Path(__file__).resolve().parent.parent


def in_colab() -> bool:
    return "google.colab" in sys.modules


def connect_drive(folder: str = "cuahsi_crop_map") -> Path | None:
    """Keep results in Google Drive so that the next notebook finds them.

    Every Colab notebook runs on its own temporary machine, so a file written
    by notebook 2 is invisible to notebook 3 unless it lives somewhere shared.
    This mounts Google Drive (Colab asks permission once per notebook) and
    points data_dir() at MyDrive/<folder>. Outside Colab, or if the mount is
    refused, nothing changes and results stay next to the notebooks.
    """
    if not in_colab():
        return None
    try:
        from google.colab import drive
        drive.mount("/content/drive")
        target = Path("/content/drive/MyDrive") / folder
        target.mkdir(parents=True, exist_ok=True)
        os.environ[WORKSPACE_ENV] = str(target)
        print("Google Drive connected.")
        return target
    except Exception as exc:                      # mount refused or unavailable
        os.environ.pop(WORKSPACE_ENV, None)
        print(f"Google Drive not connected ({exc}).")
        print("Results stay on this temporary machine. The next notebook will "
              "fall back to the example data shipped with the workshop.")
        return None


def data_dir(sub: str = "") -> Path:
    """Folder for results, created on first use.

    Results go to the workspace chosen by connect_drive() when there is one,
    otherwise to data/ in the workshop folder. Bulky downloads (sub="raw")
    always stay on the local disk: they are quick to fetch again and would
    only fill up a Drive quota.
    """
    local = repo_root() / "data"
    workspace = os.environ.get(WORKSPACE_ENV)
    base = Path(workspace) if (workspace and sub != "raw") else local
    p = base / sub if sub else base
    p.mkdir(parents=True, exist_ok=True)
    return p


def example_files() -> dict:
    """The ready made example in GEE/data: one basin, one classified year.

    Used as a fallback by notebooks 3 and 4, and as the upload material for
    the Earth Engine exercise in GEE/README.md.
    """
    d = repo_root() / "GEE" / "data"
    return {"year": EXAMPLE_YEAR,
            "crop_map": d / f"south_fork_crop_map_{EXAMPLE_YEAR}.tif",
            "basin": d / "south_fork_watershed.geojson",
            "shapefile_zip": d / "south_fork_watershed.zip"}
