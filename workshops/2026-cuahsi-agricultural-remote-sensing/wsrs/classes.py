"""
The 13 land cover classes the Prithvi crop model predicts, and their colors.

Kept in its own module with no dependencies so that notebooks which only make
maps do not have to import torch.

Palette follows USDA Cropland Data Layer conventions, matching the official
model demo: corn yellow, soybeans dark green, water blue, developed gray.
"""

CLASSES = (
    "Natural Vegetation", "Forest", "Corn", "Soybeans", "Wetlands",
    "Developed/Barren", "Open Water", "Winter Wheat", "Alfalfa",
    "Fallow/Idle Cropland", "Cotton", "Sorghum", "Other",
)

# Class id (1..13) -> RGB, same palette as the official HF demo Space.
# 0 is reserved for nodata (black).
CLASS_COLORS = {
    0: (0, 0, 0),
    1: (233, 255, 190),   # Natural Vegetation
    2: (149, 206, 147),   # Forest
    3: (255, 212, 0),     # Corn
    4: (38, 115, 0),      # Soybeans
    5: (128, 179, 179),   # Wetlands
    6: (156, 156, 156),   # Developed/Barren
    7: (77, 112, 163),    # Open Water
    8: (168, 112, 0),     # Winter Wheat
    9: (255, 168, 227),   # Alfalfa
    10: (191, 191, 122),  # Fallow/Idle Cropland
    11: (255, 38, 38),    # Cotton
    12: (255, 158, 15),   # Sorghum
    13: (0, 175, 77),     # Other
}

# USDA Cropland Data Layer codes grouped into the 13 classes above.
#
# The model's training labels were derived from the CDL, but the exact
# crosswalk was not published. This table follows the CDL class definitions:
# the named crops map to their own class, the land cover codes map to the
# matching land cover class, and every other CDL value (minor crops, double
# crops, undefined) maps to Other. Background (0) and Clouds/No Data (81) map
# to no data. Used by notebook 4.
CDL_TO_CLASS = {
    1: 3,                                     # Corn
    5: 4,                                     # Soybeans
    2: 11,                                    # Cotton
    4: 12,                                    # Sorghum
    24: 8,                                    # Winter Wheat
    36: 9,                                    # Alfalfa
    61: 10,                                   # Fallow/Idle Cropland
    111: 7,                                   # Open Water
    121: 6, 122: 6, 123: 6, 124: 6, 131: 6,   # Developed (four intensities), Barren
    141: 2, 142: 2, 143: 2,                   # Deciduous, Evergreen, Mixed Forest
    152: 1, 176: 1,                           # Shrubland, Grassland/Pasture
    190: 5, 195: 5,                           # Woody Wetlands, Herbaceous Wetlands
    0: 0, 81: 0,                              # Background, Clouds/No Data
}
CDL_DEFAULT_CLASS = 13   # any CDL code not listed above is Other


def cdl_remap_lists():
    """The crosswalk as two parallel lists, the form Earth Engine's remap wants."""
    codes = sorted(CDL_TO_CLASS)
    return codes, [CDL_TO_CLASS[c] for c in codes]
