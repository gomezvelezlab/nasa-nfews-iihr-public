# Example data for the Earth Engine app

These are the data displayed by the app of the [`GEE`](../README.md) exercise. Download the first two files, then upload them to Google Earth Engine by following [`GEE/README.md`](../README.md).

## Download

| Click to download | Upload to Earth Engine as | Size |
|---|---|---|
| [**south_fork_crop_map_2023.tif**](https://github.com/gomezvelezlab/nasa-nfews-iihr-public/raw/main/workshops/2026-cuahsi-agricultural-remote-sensing/GEE/data/south_fork_crop_map_2023.tif) | Image asset (Assets, NEW, Image Upload, GeoTIFF) | 94 KB |
| [**south_fork_watershed.zip**](https://github.com/gomezvelezlab/nasa-nfews-iihr-public/raw/main/workshops/2026-cuahsi-agricultural-remote-sensing/GEE/data/south_fork_watershed.zip) | Table asset (Assets, NEW, Table Upload, Shape files). Keep it zipped. | 15 KB |

No GitHub account is needed. If a link opens a GitHub page instead of saving the file, click the download button on that page (the arrow pointing down, labeled *Download raw file*).

## What the files contain

| File | Content |
|---|---|
| `south_fork_crop_map_2023.tif` | Crop map of the South Fork Iowa River basin, Iowa, for the 2023 growing season. One band, 30 m pixels, 1461 by 1134 pixels, projection EPSG:5070. Values 1 to 13 are the land cover classes listed below and 0 is no data. Cloud optimized GeoTIFF with an embedded color table. |
| `south_fork_watershed.zip` | Boundary of the watershed upstream of USGS gauge 05451210, South Fork Iowa River NE of New Providence, Iowa, as a zipped shapefile (583 km<sup>2</sup>). |
| `south_fork_watershed.shp`, `.shx`, `.dbf`, `.prj`, `.cpg` | The same shapefile, unzipped, for QGIS or ArcGIS. Not needed for Earth Engine. |
| `south_fork_watershed.geojson` | The same boundary as GeoJSON, used by the notebooks. Not needed for Earth Engine. |

## Class values in the crop map

| Value | Class | Value | Class |
|---|---|---|---|
| 1 | Natural Vegetation | 8 | Winter Wheat |
| 2 | Forest | 9 | Alfalfa |
| 3 | Corn | 10 | Fallow/Idle Cropland |
| 4 | Soybeans | 11 | Cotton |
| 5 | Wetlands | 12 | Sorghum |
| 6 | Developed/Barren | 13 | Other |
| 7 | Open Water | 0 | No data |

## How the files were produced

The instructors ran notebooks 1 to 3 of this workshop with the default settings and the whole basin selected. The crop map comes from NASA Harmonized Landsat Sentinel-2 imagery (HLS S30 version 2.0, NASA LP DAAC) of May 1, July 10 and September 8, 2023, classified with the IBM and NASA Prithvi-EO-1.0-100M multi-temporal crop classification model (Li et al. 2023, https://doi.org/10.57967/hf/0954). The watershed boundary comes from the USGS Network Linked Data Index.

The files are shared under the CC BY 4.0 license. This work was supported by the NASA Earth Action Water Resources Program (Grant number 80NSSC26K0798).
