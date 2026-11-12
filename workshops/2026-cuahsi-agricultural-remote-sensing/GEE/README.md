# Share a crop map as a Google Earth Engine App

A map that stays on your laptop reaches nobody. This folder shows the simplest way to put a result online: upload two files to Google Earth Engine, paste one short script, and publish an app. The app is a web page with your map, a legend and a click inspector. Anyone can open it from a link, with no account and no GIS software.

The whole exercise takes about 15 minutes.

## The data: two files to download

The data shown in the app are in this repository, in the folder [`GEE/data`](data). Click each link below and your browser saves the file on your computer. No GitHub account is needed.

| Click to download | What it is | Size |
|---|---|---|
| [**south_fork_crop_map_2023.tif**](https://github.com/gomezvelezlab/nasa-nfews-iihr-public/raw/main/workshops/2026-cuahsi-agricultural-remote-sensing/GEE/data/south_fork_crop_map_2023.tif) | The crop map, a GeoTIFF image. This is the layer that the app displays. | 94 KB |
| [**south_fork_watershed.zip**](https://github.com/gomezvelezlab/nasa-nfews-iihr-public/raw/main/workshops/2026-cuahsi-agricultural-remote-sensing/GEE/data/south_fork_watershed.zip) | The watershed boundary, a zipped shapefile. Keep it zipped: Earth Engine takes the zip file as it is. | 15 KB |

The rest of this page is three moves:

1. **Download** the two files above (Step 1).
2. **Upload** them to Google Earth Engine (Steps 2 to 5).
3. **Paste** the script, **run** it and **publish** the app (Steps 6 to 9).

## What is in this folder

| File | What it is |
|---|---|
| `data/south_fork_crop_map_2023.tif` | The classified image: South Fork Iowa River basin, Iowa, 2023 growing season. One band, 30 m pixels, values 1 to 13 are the land cover classes, 0 is no data. Produced by the instructors with notebooks 1 to 3 (whole basin, default settings). Corn covers 55 percent of the basin and soybeans 30 percent. |
| `data/south_fork_watershed.zip` | The watershed boundary as a zipped shapefile, ready to upload. |
| `data/south_fork_watershed.shp`, `.shx`, `.dbf`, `.prj`, `.cpg` | The same shapefile, unzipped, for QGIS or ArcGIS. |
| `data/south_fork_watershed.geojson` | The same boundary as GeoJSON, used by the notebooks. |
| `crop_map_app.js` | The script to copy and paste into the Earth Engine Code Editor. |

Only the first two files of the `data` folder are uploaded to Earth Engine. The others are there for readers who want to open the boundary in QGIS, ArcGIS or Python.

## Before you start

You need a Google account with Earth Engine enabled. If you have not registered yet, follow [docs/google_earth_engine_account.md](../docs/google_earth_engine_account.md) first. Registration is free for noncommercial use.

## Step 1. Get the two files on your computer

Click the two links in the table at the top of this page, or these:

- [south_fork_crop_map_2023.tif](https://github.com/gomezvelezlab/nasa-nfews-iihr-public/raw/main/workshops/2026-cuahsi-agricultural-remote-sensing/GEE/data/south_fork_crop_map_2023.tif)
- [south_fork_watershed.zip](https://github.com/gomezvelezlab/nasa-nfews-iihr-public/raw/main/workshops/2026-cuahsi-agricultural-remote-sensing/GEE/data/south_fork_watershed.zip)

Both files land in the *Downloads* folder of your computer. Do not open them and do not unzip the zip file. You only need to know where they are, because Steps 3 and 4 ask you to select them.

If a link opens a GitHub page instead of saving the file, click the download button on that page (the arrow pointing down, labeled *Download raw file*).

**Using your own map instead.** Notebook 3 saves `crop_map_<year>_cog.tif` and `watershed.zip` on your computer in its section 6. Use these two files in place of the example files. All the steps below are the same.

## Step 2. Open the Code Editor

Go to <https://code.earthengine.google.com> and sign in. Your Cloud project name appears in the top right corner. The left panel has three tabs: *Scripts*, *Docs* and *Assets*. Click **Assets**.

## Step 3. Upload the GeoTIFF as an image asset

1. In the Assets tab, click **NEW**, then **Image Upload**, then **GeoTIFF (.tif, .tiff)**.
2. Click **SELECT** and choose `south_fork_crop_map_2023.tif`.
3. In **Asset ID**, type a short name without spaces: `south_fork_crop_map_2023`.
4. Open **Advanced options** and set two things:
   - **Pyramiding policy: MODE.** The map holds class numbers, not measurements. The default (MEAN) would average class 3 and class 4 into 3.5 when you zoom out, which is no class at all. MODE keeps the most frequent class.
   - **Masking mode: No-data value**, and enter `0`. Pixels outside the watershed become transparent.
5. Click **UPLOAD**.

## Step 4. Upload the shapefile as a table asset

1. In the Assets tab, click **NEW**, then **Table Upload**, then **Shape files (.shp, .shx, .dbf, .prj, or .zip)**.
2. Click **SELECT** and choose `south_fork_watershed.zip`. The zip already holds all the parts.
3. In **Asset ID**, type `south_fork_watershed`.
4. Click **UPLOAD**.

## Step 5. Wait for the two uploads to finish

Open the **Tasks** tab on the right side of the Code Editor. Two tasks named *Ingest image* and *Ingest table* are running. Each takes about a minute. When both turn blue with a check mark, click the refresh button in the Assets tab. The two assets appear in the list.

Click each asset once to see its details. The line that starts with `projects/` is its **asset id**. You need both ids in the next step.

## Step 6. Paste the script

1. Click the **Scripts** tab, then **NEW**, then **File**. Give it a name, for example `crop_map_app`.
2. Open [`crop_map_app.js`](crop_map_app.js) in this folder, copy everything, and paste it in the editor.
3. In section 1 of the script, replace the two asset ids with yours, and adjust the title if you used your own map:

```javascript
var CROP_MAP  = 'projects/your-project-id/assets/south_fork_crop_map_2023';
var WATERSHED = 'projects/your-project-id/assets/south_fork_watershed';
var TITLE     = 'Crop map 2023, South Fork Iowa River';
```

4. Click **Save**, then **Run**.

The map moves to the watershed and shows the crop map over satellite imagery, the watershed boundary in black, and a panel with the title and the legend. Click any field: the panel names the class at that point.

## Step 7. Let anyone read your two assets

A public app can only show data that is public.

1. In the Assets tab, hover over `south_fork_crop_map_2023` and click the **share** icon.
2. Tick **Anyone can read**, then click **Done**.
3. Repeat for `south_fork_watershed`.

## Step 8. Publish the app

1. Above the script, click **Apps**, then **NEW APP**.
2. Give the app a name, for example `south-fork-crop-map`.
3. Select your Cloud project, and keep the source set to the current contents of the editor.
4. Leave the access unrestricted, so that anyone with the link can open the app.
5. Click **PUBLISH**. Earth Engine shows the address of the app. It ends in `earthengine.app/view/south-fork-crop-map`.

A new app can first show a page saying that it is not ready yet. Wait a few minutes and reload the page.

## Step 9. Test the link, then share it

Open the address in a private browser window, where you are not signed in to Google. If the map, the legend and the click inspector all work, the link is ready to send to a colleague, a stakeholder, or a thesis committee.

## If something goes wrong

| What you see | Likely cause | What to do |
|---|---|---|
| The script stops with *asset not found* | The asset id in section 1 does not match | Click the asset in the Assets tab and copy its id exactly |
| The map is empty or black | The upload task has not finished, or the image was uploaded without the no-data value | Check the Tasks tab; the script masks value 0 in any case, so a finished upload should display |
| Colors look blurred or wrong when zoomed out | The pyramiding policy was left at MEAN | Delete the asset and upload it again with MODE |
| The app opens for you but asks others to sign in | One of the two assets is not shared | Repeat Step 7 for both assets |
| *NEW APP* is grayed out or the project is refused | The Cloud project is not registered for Earth Engine | See [docs/google_earth_engine_account.md](../docs/google_earth_engine_account.md) |
| The shapefile upload fails | A part is missing | Upload the `.zip`, which holds the `.shp`, `.shx`, `.dbf` and `.prj` together |

## What the script does, in six short sections

1. **Your two assets.** The only lines you edit.
2. **Classes and colors.** The 13 class names of the model and one color each, the same as in the notebooks.
3. **Load the data.** Reads the image and the table, hides value 0, and draws the watershed outline.
4. **Draw the map.** Satellite background, crop map, boundary.
5. **Title and legend.** A panel built from the two lists in section 2.
6. **Click to read a pixel.** Asks Earth Engine for the class at the clicked point and writes its name in the panel.

Inside the script, each section opens with a short note that says what the section does and what it defines, and every line of code is explained by the comment above it. You can read the script from top to bottom without knowing JavaScript.

Everything else you see in a published app, such as zooming, panning and the layer list, comes from Earth Engine itself.

## Going further

- Notebook 4 (optional) compares the same asset with the USDA Cropland Data Layer, class by class. For this example map the two agree on 86 percent of the pixels.
- Upload maps of several years and add one `Map.addLayer` line per year to show crop rotation.
- Google's guide to Earth Engine Apps: <https://developers.google.com/earth-engine/guides/apps>.

## Data credits

The crop map was produced from NASA Harmonized Landsat Sentinel-2 imagery (HLS S30 version 2.0, NASA LP DAAC) with the IBM and NASA Prithvi-EO-1.0-100M multi-temporal crop classification model (Li et al. 2023, https://doi.org/10.57967/hf/0954). The watershed boundary comes from the USGS Network Linked Data Index for gauge USGS-05451210, South Fork Iowa River NE of New Providence, Iowa. This work was supported by the NASA Earth Action Water Resources Program (Grant number 80NSSC26K0798).
