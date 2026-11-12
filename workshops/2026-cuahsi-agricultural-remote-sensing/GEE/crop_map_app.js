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

  THE SCRIPT IN SIX SECTIONS
    1. Your two assets     where your two uploaded files are (the only part you edit)
    2. Classes and colors  the 13 class names and one color for each
    3. Load the data       read the crop map and the watershed boundary
    4. Draw the map        background, crop map layer, boundary layer
    5. Legend box          title, legend, a line for the clicked class, credits
    6. Click to read       name the class at the point that is clicked

  HOW TO READ THE CODE
    //        starts a comment. Earth Engine ignores it. It is there for you.
              The boxed notes, like this one, are comments too.
    var       gives a name to something, so that later lines can use it.
    ee.       an Earth Engine object: data that lives on Google's servers.
    ui.       a piece of the interface: a box, a line of text.
    Map       the map at the bottom of the Code Editor, and of the app.
    Names in capital letters (CROP_MAP, NAMES) are settings.
    Names in small letters (cropMap, panel) are things the script builds.
==============================================================================*/


/*------------------------------------------------------------------------------
  SECTION 1. YOUR TWO ASSETS

  What it does    Tells the script where your two uploaded files are.
  What we define  CROP_MAP   the asset id of the crop map image (the GeoTIFF)
                  WATERSHED  the asset id of the watershed boundary (the zip)
                  TITLE      the text shown at the top of the legend box
  What to change  These three lines, and nothing else in the script.
                  To find an asset id, click the asset in the Assets tab and
                  copy the line that starts with "projects/".
------------------------------------------------------------------------------*/
var CROP_MAP  = 'projects/YOUR-PROJECT-ID/assets/south_fork_crop_map_2023';
var WATERSHED = 'projects/YOUR-PROJECT-ID/assets/south_fork_watershed';
var TITLE     = 'Crop map 2023, South Fork Iowa River';


/*------------------------------------------------------------------------------
  SECTION 2. THE 13 CLASSES OF THE MODEL AND THEIR COLORS

  What it does    Lists what each number in the crop map means, and the color
                  used to draw it. Nothing is drawn yet.
  What we define  NAMES   the 13 class names, in the order of the class numbers
                  COLORS  one color per class, in the same order
  How to read it  The two lists go together. The first name and the first
                  color belong to class 1, the second ones to class 2, and so
                  on up to class 13. For example class 3 is Corn, drawn in
                  yellow (ffd400).
                  A color is written as six characters, two each for red,
                  green and blue, the way colors are written on web pages.
------------------------------------------------------------------------------*/
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


/*------------------------------------------------------------------------------
  SECTION 3. LOAD THE DATA

  What it does    Reads your two assets and prepares them for display.
  What we define  watershed  the watershed boundary (a polygon)
                  cropMap    the crop map (an image with one class number,
                             1 to 13, in every pixel)
                  outline    a drawing of the watershed border, to lay over
                             the map
------------------------------------------------------------------------------*/
// Read the watershed boundary from the table asset.
// A "FeatureCollection" is Earth Engine's name for a set of shapes.
var watershed = ee.FeatureCollection(WATERSHED);

// Read the crop map from the image asset. An image can hold several layers,
// called bands. Ours has one. We keep it (band number 0, the first) and name
// it 'class', so that later lines can ask for it by name.
var cropMap = ee.Image(CROP_MAP).select(0).rename('class');

// Hide the pixels with the value 0. They are outside the watershed.
// cropMap.gt(0) means "greater than 0", and updateMask keeps only the pixels
// where that is true. The hidden pixels become transparent.
cropMap = cropMap.updateMask(cropMap.gt(0));          // 0 means no data

// Turn the watershed polygon into a drawing of its border only.
// We start from an empty image and paint the border on it, 3 pixels wide.
// Without this step the polygon would be drawn filled and would hide the map.
var outline = ee.Image().byte().paint({
  featureCollection: watershed, color: 1, width: 3
});


/*------------------------------------------------------------------------------
  SECTION 4. DRAW THE MAP

  What it does    Chooses the background, moves the view to the watershed and
                  adds two layers: the crop map, then the border on top.
  What we define  Nothing new. This section uses cropMap, outline and COLORS.
  Good to know    Layers are stacked in the order they are added. The last
                  one added is on top.
------------------------------------------------------------------------------*/
// Use the satellite image as the background.
Map.setOptions('SATELLITE');

// Move the view to the watershed. The number 10 is the zoom level.
// A larger number zooms in, a smaller number zooms out.
Map.centerObject(watershed, 10);

// Add the crop map as a layer. The settings between { } say how to color it:
// class 1 (min) gets the first color of COLORS and class 13 (max) the last.
// 'Crop map' is the name shown in the Layers list of the map.
// true means the layer is visible when the app opens.
// 0.85 is the opacity: slightly transparent, so the fields show through.
Map.addLayer(cropMap, {min: 1, max: 13, palette: COLORS}, 'Crop map', true, 0.85);

// Add the watershed border on top, in black (000000).
Map.addLayer(outline, {palette: ['000000']}, 'Watershed boundary');


/*------------------------------------------------------------------------------
  SECTION 5. TITLE, CREDITS AND LEGEND

  What it does    Builds the white box in the lower left corner of the map and
                  fills it from top to bottom: title, one sentence about the
                  map, the legend, a line for the clicked class, the credits.
  What we define  panel    the white box itself
                  swatch   a small colored square (one per class)
                  name     the name written next to the square
                  readout  the line of text that section 6 will update
  Good to know    A "Panel" is a box that holds other things. A "Label" is a
                  line of text. The words between { } are style settings:
                  size of the letters, bold or not, space around the text.
------------------------------------------------------------------------------*/
// Create the box: lower left corner, 290 pixels wide, a little space inside.
var panel = ui.Panel({style: {position: 'bottom-left', width: '290px', padding: '10px'}});

// First line of the box: the title, in bold. TITLE comes from section 1.
panel.add(ui.Label(TITLE, {fontWeight: 'bold', fontSize: '16px', margin: '0 0 6px 0'}));

// Second line: one sentence that says what the map shows and where the
// data come from. The + sign joins two pieces of text into one.
panel.add(ui.Label(
  'Crop type at 30 m from NASA Harmonized Landsat Sentinel-2 imagery, ' +
  'classified with the IBM and NASA Prithvi-EO foundation model.',
  {fontSize: '12px', margin: '0 0 8px 0'}));

// The legend. This loop runs 13 times, once per class. The counter i goes
// from 0 to 12, because lists are counted from 0. Each turn adds one line to
// the box: a colored square followed by the name of the class.
for (var i = 0; i < NAMES.length; i++) {
  // The colored square: a label with no text and a background color.
  // COLORS[i] is the color of this class. The # in front is how web pages
  // mark a color.
  var swatch = ui.Label('', {
    backgroundColor: '#' + COLORS[i], padding: '8px', margin: '0 8px 4px 0',
    border: '1px solid #555555'
  });

  // The name of this class, taken from the list NAMES.
  var name = ui.Label(NAMES[i], {fontSize: '12px', margin: '0 0 4px 0'});

  // Put the square and the name side by side ('horizontal') in a small box,
  // and add that small box to the big one.
  panel.add(ui.Panel([swatch, name], ui.Panel.Layout.flow('horizontal')));
}

// A line of text under the legend. For now it invites a click.
// Section 6 replaces this text with the class of the clicked point.
var readout = ui.Label('Click the map to read the class at a point.',
                       {fontSize: '12px', fontWeight: 'bold', margin: '8px 0 6px 0'});
panel.add(readout);

// Last lines of the box: the credits, in small print.
panel.add(ui.Label(
  'CUAHSI Water Science Exchange 2026 workshop, University of Iowa. ' +
  'Supported by the NASA Earth Action Water Resources Program ' +
  '(Grant number 80NSSC26K0798).',
  {fontSize: '10px', margin: '0'}));

// The box is complete. Place it on the map.
Map.add(panel);


/*------------------------------------------------------------------------------
  SECTION 6. CLICK THE MAP TO READ A PIXEL

  What it does    When someone clicks the map, finds the class of the crop map
                  at that place and writes its name in the box.
  What we define  coords  the place that was clicked (longitude and latitude)
                  point   the same place, as an Earth Engine point
                  value   the class number of the crop map at that point
                  v       the same number, once it has come back from the
                          servers
  Good to know    The data are on Google's servers, so the answer takes a
                  moment. The script asks, shows "Reading ...", and writes the
                  class name when the answer arrives.
------------------------------------------------------------------------------*/
// Show a cross instead of a hand over the map, to invite a click.
Map.style().set('cursor', 'crosshair');

// Map.onClick says: "every time the map is clicked, run the lines between
// { and }". Earth Engine fills in coords with the clicked place.
Map.onClick(function (coords) {
  // Make an Earth Engine point from the clicked longitude and latitude.
  var point = ee.Geometry.Point([coords.lon, coords.lat]);

  // Ask for the value of the crop map at that point.
  // reduceRegion summarizes an image over a place. Here the place is one
  // point, and the summary is "the first value found" (Reducer.first).
  // scale: 30 reads the map at its own pixel size, 30 m.
  // .get('class') takes the answer for the band we named 'class'.
  var value = cropMap.reduceRegion({
    reducer: ee.Reducer.first(), geometry: point, scale: 30
  }).get('class');

  // Tell the user that the answer is on its way.
  readout.setValue('Reading ...');

  // evaluate sends the question to the servers. When the answer comes back,
  // it runs the lines between { and }, with the answer in v.
  value.evaluate(function (v) {
    // v is the class number, 1 to 13. Lists are counted from 0, so the name
    // of class v is NAMES[v - 1]. If v is empty, the click was outside the
    // crop map, and we say so.
    // Read "condition ? A : B" as "if the condition holds, A, otherwise B".
    readout.setValue(v ? 'Class at this point: ' + NAMES[v - 1]
                       : 'No data at this point.');
  });
});
