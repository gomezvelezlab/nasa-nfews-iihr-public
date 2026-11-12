# data/

This folder is filled by the notebooks at run time and is not tracked by git. Nothing here is needed to start.

## Where the files go

| Where the notebooks run | Result files | Downloaded satellite granules |
|---|---|---|
| Google Colab with Google Drive connected (the default) | `MyDrive/cuahsi_crop_map/` in your Google Drive | `data/raw/` on the temporary Colab machine |
| Google Colab without Drive, or your own computer | this folder | `data/raw/` in this folder |

Each Colab notebook runs on its own temporary machine. Saving the results in Google Drive is what lets notebook 3 read what notebook 2 wrote. The downloaded granules are large and are needed only inside notebook 2, so they stay on the temporary machine and do not use your Drive space.

## Files

| File | Written by | Read by |
|---|---|---|
| `basin.geojson` (watershed boundary) | notebook 1 | notebooks 2 and 3 |
| `raw/` (HLS band files, about 1 GB for a full basin) | notebook 2 | notebook 2 |
| `stack_<year>.tif` (18 band model input) | notebook 2 | notebooks 2 and 3 |
| `crop_map_<year>.tif` (classified map, color table embedded) | notebook 2 | notebook 3 |
| `crop_map_<year>.html` (interactive map, opens in any browser) | notebook 3 | |
| `crop_map_<year>_cog.tif` (cloud optimized GeoTIFF) | notebook 3 | uploaded to Google Earth Engine, see `GEE/README.md` |
| `watershed.zip` (watershed boundary as a zipped shapefile) | notebook 3 | uploaded to Google Earth Engine, see `GEE/README.md` |
| `example/` (copy of the example crop map and boundary) | notebook 3, only when it finds no crop map of your own | notebook 3 |

The raster files are derived from NASA Harmonized Landsat Sentinel-2 imagery (open data) and from the Prithvi-EO crop classification model (Apache 2.0). Keep the attributions listed in the workshop README when you share them.
