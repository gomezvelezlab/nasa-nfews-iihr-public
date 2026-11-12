# nasa-nfews-iihr-public

Public repository of the project **Integrating NASA Earth Observations and In Situ Sensor Networks to Predict Nitrate Dynamics in Iowa's Streams and Rivers**, which develops the Nitrate Forecasting and Early Warning System (NFEWS) at IIHR Hydroscience and Engineering, University of Iowa. This work was supported by the NASA Earth Action Water Resources Program (Grant number 80NSSC26K0798).

## About the project

NFEWS is a forecasting and early warning system for nitrate in Iowa's rivers and streams. It combines NASA satellite observations with ground-based water quality measurements, including the network of 60 real-time monitoring stations operated by IIHR, to track and anticipate changes in nitrate concentration, including in places where measurements are sparse. The system is developed together with three public water suppliers: the City of Cedar Rapids, the City of Iowa City, and Des Moines Water Works. The three-year project runs as a pilot, and its model is planned for integration into the Iowa Water Quality Information System (IWQIS). The University of Iowa announcement of July 20, 2026 gives an overview: <https://iihr.uiowa.edu/node/3631>.

Satellite derived land cover is one of the inputs to that work, because the extent and timing of row crops govern nutrient export from working landscapes. This repository holds the parts of the project that are meant to be reused by others: training materials, open code, and documentation. Research data products and model code are added here as they are released.

## Contents

| Path | What it is | Status |
|---|---|---|
| [`workshops/2026-cuahsi-agricultural-remote-sensing/`](workshops/2026-cuahsi-agricultural-remote-sensing/) | Hands-on materials for the workshop *Agricultural Remote Sensing with Cloud Platforms and Geospatial Foundation Models*, CUAHSI Water Science Exchange 2026, University of Missouri, November 12, 2026. Four notebooks that run in Google Colab, a helper package, a `GEE` folder with example data and a script for publishing a crop map as a Google Earth Engine App, and setup guides for Google Colab, NASA Earthdata and Google Earth Engine. | Ready for participants |
| `CITATION.cff` | Citation metadata for this repository | |
| `LICENSE` | License for the code in this repository | |

Each workshop or product folder has its own README with the details that matter to its users: what it does, what it requires, where its data come from, and how to cite it.

## Project team

- Project lead: Jesus Gomez-Velez, Associate Professor of Civil and Environmental Engineering, IIHR Hydroscience and Engineering, University of Iowa
- Workshop leads and repository contacts: Mohamed Abdelkader and Humberto Vergara, IIHR Hydroscience and Engineering, University of Iowa
- Partner water suppliers: City of Cedar Rapids, City of Iowa City, Des Moines Water Works

## Funding acknowledgement

This work was supported by the NASA Earth Action Water Resources Program (Grant number 80NSSC26K0798). Any opinions, findings, and conclusions or recommendations expressed in this material are those of the authors and do not necessarily reflect the views of the National Aeronautics and Space Administration.

Products in this repository that reuse third party data or models carry their own attribution and license notes in the README of the folder that uses them. The principal sources are NASA Harmonized Landsat Sentinel-2 (HLS) surface reflectance, the IBM and NASA Prithvi-EO geospatial foundation models, the USDA National Agricultural Statistics Service Cropland Data Layer, and USGS water data services.

## How to cite

If you use these materials, please cite the repository (see `CITATION.cff`, which GitHub renders as a citation widget) together with the original data and model sources listed in the folder you used. A suggested form:

> Abdelkader, M., Vergara, H., and the project team (2026). *nasa-nfews-iihr-public: public materials from the project "Integrating NASA Earth Observations and In Situ Sensor Networks to Predict Nitrate Dynamics in Iowa's Streams and Rivers".* GitHub repository, https://github.com/gomezvelezlab/nasa-nfews-iihr-public.

## License

Code in this repository is released under the GNU General Public License v3.0 (see `LICENSE`). Text, figures and teaching materials are released under the Creative Commons Attribution 4.0 International license (CC BY 4.0) unless a folder states otherwise. Third party data and models keep their original licenses, which are listed where they are used.

## Contact

Questions about the materials or the project can be sent to Mohamed Abdelkader (mohamed-abdelkader@uiowa.edu) or opened as an issue on this repository.
