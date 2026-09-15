# OpenTopography Point Elevation — QGIS Plugin

**Version 0.0.1**  
**QGIS:** 3.4 through QGIS 4.x

A QGIS plugin for querying the **OpenTopography Point Elevation API** and putting elevation directly into point data.

## What it does

### Add elevation to an existing point layer

Choose any point layer, select an OpenTopography elevation dataset, enter your API key and run the algorithm. The plugin creates a new output layer and leaves the input unchanged.

The plugin can write:

- `ot_elev` — elevation value
- `ot_dem` — dataset shortname actually returned by the API
- `ot_vcrs` — vertical CRS EPSG code returned by the API
- `ot_unit` — elevation unit returned by the API

> Multipart point features are supported by querying the first point in each feature.

### Processing Toolbox support

The plugin adds:

**OpenTopography → Point Elevation → Add OpenTopography elevation to points**

This is useful in Processing Modeler and repeatable workflows. The Processing tool includes an **Enter OpenTopography access key** parameter. After a run, the key is stored in the current QGIS profile and pre-filled on the next run, just like the OpenTopography DEM Downloader.

## Selectable elevation datasets

The current plugin list follows the OpenTopography Point Elevation API dataset shortnames and includes:

- Copernicus: `COP30`, `COP90`
- SRTM: `SRTM_GL1`, `SRTM_GL3`, `SRTM_GL1_Ellip`
- `NASADEM`
- ALOS: `AW3D30`, `AW3D30_E`
- `GEDTM30`
- `GEDI_L3`
- `SRTM15Plus`
- `GEBCOIceTopo`, `GEBCOSubIceTopo`
- `ANADEM`
- `EU_DTM`
- `USGS10m`, `USGS30m`
- `CA_MRDEM`
- `LINZ1m_DSM`, `LINZ1m_DTM`
- `ArcticDEM2m`, `ArcticDEM10m`, `ArcticDEM32m`
- `REMA2m`, `REMA10m`, `REMA32m`

Regional datasets return no data when the point is outside their coverage.

## API key

OpenTopography requires a personal API key for the Point Elevation API.

1. Create/login to an OpenTopography account.
2. Request/manage the API key from the OpenTopography portal.
3. Paste the key into the plugin's **OpenTopography access key** field.
4. Run the tool/query once. The key is saved in QGIS settings and will automatically appear in the same field next time, matching the OpenTopography DEM Downloader behavior.

The API key is **not hard-coded in the plugin** and is not written into output layers.

## API usage and limits

Point querying is lightweight, but it is still **one API request per input point**. OpenTopography applies daily API limits, so split very large datasets into sensible batches.

## Vertical CRS matters

Different elevation products may use different vertical reference systems. The Point Elevation API returns vertical CRS information with its result. This plugin stores the API-returned EPSG identifier in `ot_vcrs` instead of assuming every DEM uses the same vertical datum.

## Installation

1. Download `OpenTopography-Point-Elevation.zip`.
2. In QGIS open **Plugins → Manage and Install Plugins…**.
3. Choose **Install from ZIP**.
4. Select the ZIP and install it.
5. Open the plugin from the toolbar or **Vector → OpenTopography Point Elevation**. Both entries launch the same **Add OpenTopography elevation to points** algorithm dialog found in the Processing Toolbox.

## Credits

This plugin is a **new, separate implementation** for point elevation workflows.

- Elevation service and dataset access: **OpenTopography** — https://opentopography.org/
- Point Elevation API documentation: https://portal.opentopography.org/apidocs/#/Public/getPointElevation
- Architectural/workflow inspiration: **OpenTopography DEM Downloader QGIS plugin** by **Kyaw Naing Win** — https://github.com/knwin/OpenTopography-DEM-Downloader-qgis-plugin

The inspiration plugin downloads raster DEMs for extents. This plugin instead focuses on the single-coordinate Point Elevation API through a QGIS Processing workflow.

## License

GNU General Public License v3.0 or later. See `LICENSE`.

## Compatibility and security

- QGIS 3.4+ with Qt5 is supported through compatibility fallbacks.
- QGIS 4 with Qt6 uses `QMetaType` and `Qgis.ProcessingSourceType`.
- Python 3.6 and newer are supported without `dataclasses`.
- API keys are never hard-coded or included in output layers.
- Connection errors do not display request URLs that may contain API keys.
- The release is checked with Bandit, detect-secrets and Flake8.
