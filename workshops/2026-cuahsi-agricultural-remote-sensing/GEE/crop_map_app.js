/*==============================================================================
  SHARE A CROP MAP AS A GOOGLE EARTH ENGINE APP

  Workshop  Agricultural Remote Sensing with Cloud Platforms and Geospatial
            Foundation Models. CUAHSI Water Science Exchange 2026.
  Leads     Mohamed Abdelkader and Humberto Vergara, IIHR Hydroscience and
            Engineering, University of Iowa.
  Funding   This work was supported by the NASA Earth Action Water Resources
            Program (Grant number 80NSSC26K0798).

  HOW TO USE (the full steps are in GEE/README.md)
    1. Upload the GeoTIFF and the watershed shapefile as assets.
    2. Paste this script in the Code Editor, https://code.earthengine.google.com
    3. Put your two asset ids in section 1 below.
    4. Click Run. Then Apps, NEW APP, to publish.
==============================================================================*/


// ---- 1. YOUR TWO ASSETS (copy each id from the Assets tab) ------------------
var CROP_MAP  = 'projects/YOUR-PROJECT-ID/assets/south_fork_crop_map_2023';
var WATERSHED = 'projects/YOUR-PROJECT-ID/assets/south_fork_watershed';
var TITLE     = 'Crop map 2023, South Fork Iowa River';


// ---- 2. THE 13 CLASSES OF THE MODEL AND THEIR COLORS -----------------------
var NAMES = [
  'Natural Vegetation', 'Forest', 'Corn', 'Soybeans', 'Wetlands',
  'Developed/Barren', 'Open Water', 'Winter Wheat', 'Alfalfa',
  'Fallow/Idle Cropland', 'Cotton', 'Sorghum', 'Other'
];
var COLORS = [
  'e9ffbe', '95ce93', 'ffd400', '267300', '80b3b3',
  '9c9c9c', '4d70a3', 'a87000', 'ffa8e3',
  'bfbf7a', 'ff2626', 'ff9e0f', '00af4d'
];


// ---- 3. LOAD THE DATA --------------------------------------------------------
var watershed = ee.FeatureCollection(WATERSHED);
var cropMap = ee.Image(CROP_MAP).select(0).rename('class');
cropMap = cropMap.updateMask(cropMap.gt(0));          // 0 means no data
var outline = ee.Image().byte().paint({
  featureCollection: watershed, color: 1, width: 3
});


// ---- 4. DRAW THE MAP ---------------------------------------------------------
Map.setOptions('SATELLITE');
Map.centerObject(watershed, 10);
Map.addLayer(cropMap, {min: 1, max: 13, palette: COLORS}, 'Crop map', true, 0.85);
Map.addLayer(outline, {palette: ['000000']}, 'Watershed boundary');


// ---- 5. TITLE, CREDITS AND LEGEND --------------------------------------------
var panel = ui.Panel({style: {position: 'bottom-left', width: '290px', padding: '10px'}});
panel.add(ui.Label(TITLE, {fontWeight: 'bold', fontSize: '16px', margin: '0 0 6px 0'}));
panel.add(ui.Label(
  'Crop type at 30 m from NASA Harmonized Landsat Sentinel-2 imagery, ' +
  'classified with the IBM and NASA Prithvi-EO foundation model.',
  {fontSize: '12px', margin: '0 0 8px 0'}));

for (var i = 0; i < NAMES.length; i++) {
  var swatch = ui.Label('', {
    backgroundColor: '#' + COLORS[i], padding: '8px', margin: '0 8px 4px 0',
    border: '1px solid #555555'
  });
  var name = ui.Label(NAMES[i], {fontSize: '12px', margin: '0 0 4px 0'});
  panel.add(ui.Panel([swatch, name], ui.Panel.Layout.flow('horizontal')));
}

var readout = ui.Label('Click the map to read the class at a point.',
                       {fontSize: '12px', fontWeight: 'bold', margin: '8px 0 6px 0'});
panel.add(readout);
panel.add(ui.Label(
  'CUAHSI Water Science Exchange 2026 workshop, University of Iowa. ' +
  'Supported by the NASA Earth Action Water Resources Program ' +
  '(Grant number 80NSSC26K0798).',
  {fontSize: '10px', margin: '0'}));
Map.add(panel);


// ---- 6. CLICK THE MAP TO READ A PIXEL ----------------------------------------
Map.style().set('cursor', 'crosshair');
Map.onClick(function (coords) {
  var point = ee.Geometry.Point([coords.lon, coords.lat]);
  var value = cropMap.reduceRegion({
    reducer: ee.Reducer.first(), geometry: point, scale: 30
  }).get('class');
  readout.setValue('Reading ...');
  value.evaluate(function (v) {
    readout.setValue(v ? 'Class at this point: ' + NAMES[v - 1]
                       : 'No data at this point.');
  });
});
