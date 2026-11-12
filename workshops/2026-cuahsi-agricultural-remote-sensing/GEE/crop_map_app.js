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
// These three lines are the only ones you need to change.
// CROP_MAP is the image you uploaded, WATERSHED is the shapefile you
// uploaded, and TITLE is the text shown at the top of the legend box.
var CROP_MAP  = 'projects/YOUR-PROJECT-ID/assets/south_fork_crop_map_2023';
var WATERSHED = 'projects/YOUR-PROJECT-ID/assets/south_fork_watershed';
var TITLE     = 'Crop map 2023, South Fork Iowa River';


// ---- 2. THE 13 CLASSES OF THE MODEL AND THEIR COLORS -----------------------
// Two lists in the same order. The first name goes with class 1 and with
// the first color, the second name with class 2, and so on.
// A color is written as six characters (red, green, blue), as on web pages.
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
// The watershed boundary, read from the table asset.
var watershed = ee.FeatureCollection(WATERSHED);

// The crop map, read from the image asset. We keep its first band and
// name it 'class'.
var cropMap = ee.Image(CROP_MAP).select(0).rename('class');

// Hide the pixels with the value 0, so that they are transparent.
cropMap = cropMap.updateMask(cropMap.gt(0));          // 0 means no data

// Turn the watershed polygon into a drawing of its outline, 3 pixels wide.
var outline = ee.Image().byte().paint({
  featureCollection: watershed, color: 1, width: 3
});


// ---- 4. DRAW THE MAP ---------------------------------------------------------
// Use the satellite background, and move the view to the watershed.
// The number 10 is the zoom level. A larger number zooms in.
Map.setOptions('SATELLITE');
Map.centerObject(watershed, 10);

// Add the crop map. Class 1 gets the first color of the list and class 13
// the last one. The value 0.85 makes the layer slightly transparent.
Map.addLayer(cropMap, {min: 1, max: 13, palette: COLORS}, 'Crop map', true, 0.85);

// Add the watershed outline on top, in black.
Map.addLayer(outline, {palette: ['000000']}, 'Watershed boundary');


// ---- 5. TITLE, CREDITS AND LEGEND --------------------------------------------
// A white box in the lower left corner of the map. Everything below is
// added to this box, from top to bottom.
var panel = ui.Panel({style: {position: 'bottom-left', width: '290px', padding: '10px'}});

// The title, then one sentence that says what the map shows.
panel.add(ui.Label(TITLE, {fontWeight: 'bold', fontSize: '16px', margin: '0 0 6px 0'}));
panel.add(ui.Label(
  'Crop type at 30 m from NASA Harmonized Landsat Sentinel-2 imagery, ' +
  'classified with the IBM and NASA Prithvi-EO foundation model.',
  {fontSize: '12px', margin: '0 0 8px 0'}));

// The legend. The loop runs once per class and adds one line to the box:
// a small colored square, followed by the name of the class.
for (var i = 0; i < NAMES.length; i++) {
  // The colored square.
  var swatch = ui.Label('', {
    backgroundColor: '#' + COLORS[i], padding: '8px', margin: '0 8px 4px 0',
    border: '1px solid #555555'
  });
  // The class name.
  var name = ui.Label(NAMES[i], {fontSize: '12px', margin: '0 0 4px 0'});
  // Put the square and the name side by side, and add them to the box.
  panel.add(ui.Panel([swatch, name], ui.Panel.Layout.flow('horizontal')));
}

// A line of text that will show the class of the point you click.
var readout = ui.Label('Click the map to read the class at a point.',
                       {fontSize: '12px', fontWeight: 'bold', margin: '8px 0 6px 0'});
panel.add(readout);

// The credits, in small print.
panel.add(ui.Label(
  'CUAHSI Water Science Exchange 2026 workshop, University of Iowa. ' +
  'Supported by the NASA Earth Action Water Resources Program ' +
  '(Grant number 80NSSC26K0798).',
  {fontSize: '10px', margin: '0'}));

// Place the finished box on the map.
Map.add(panel);


// ---- 6. CLICK THE MAP TO READ A PIXEL ----------------------------------------
// Show a cross instead of a hand, to invite a click.
Map.style().set('cursor', 'crosshair');

// The function below runs every time someone clicks the map.
// "coords" holds the longitude and the latitude of the click.
Map.onClick(function (coords) {
  // The clicked place, as a point.
  var point = ee.Geometry.Point([coords.lon, coords.lat]);

  // Ask for the value of the crop map at that point.
  var value = cropMap.reduceRegion({
    reducer: ee.Reducer.first(), geometry: point, scale: 30
  }).get('class');

  // Earth Engine computes the answer on its servers, which takes a moment.
  // Show a waiting message, then write the class name when the answer comes.
  readout.setValue('Reading ...');
  value.evaluate(function (v) {
    // v is the class number, 1 to 13. The names are counted from 0 in the
    // list, hence v - 1. An empty answer means there is no data there.
    readout.setValue(v ? 'Class at this point: ' + NAMES[v - 1]
                       : 'No data at this point.');
  });
});
