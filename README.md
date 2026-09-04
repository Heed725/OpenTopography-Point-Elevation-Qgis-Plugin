# OpenTopography Point Elevation — QGIS Plugin

**Version 1.0.0**  
**QGIS:** 3.22+ and prepared for QGIS 4.x API differences

A QGIS plugin for querying the **OpenTopography Point Elevation API** and putting elevation directly into point data.

## What it does

### 1. Add elevation to an existing point layer

Choose any point layer already loaded in QGIS, choose an OpenTopography elevation dataset, and click **Add OpenTopography elevation to layer**.

The plugin can write:

- `elev_m` — elevation value (field name is editable)
- `ot_dem` — dataset shortname actually returned by the API
- `ot_vcrs` — vertical CRS EPSG code returned by the API
- `ot_unit` — elevation unit returned by the API

You can update the entire layer or **selected features only**.

> Multipart point features are supported by querying the first point in each feature.

### 2. Create a point with elevation

Open the **Create / click elevation points** tab and either:

- type longitude and latitude in WGS84, or
- click **Pick points on map** and click anywhere on the QGIS canvas.

The plugin transforms the clicked map coordinate to EPSG:4326, queries OpenTopography, then creates a point in a temporary layer named **OpenTopography Elevation Points** with coordinates, elevation, dataset, vertical CRS and query timestamp.

### 3. Processing Toolbox support

The plugin adds:

**OpenTopography → Point Elevation → Add OpenTopography elevation to points**

This creates a new output point layer containing all original attributes plus:

- `ot_elev`
- `ot_dem`
- `ot_vcrs`
- `ot_unit`

This is useful in Processing Modeler and repeatable workflows. The Processing tool reads the API key saved by the main plugin dialog instead of exposing the key as a Processing parameter.

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
3. Paste the key into the plugin.
4. Optionally allow the plugin to remember it in the current QGIS profile settings.

The API key is **not hard-coded in the plugin** and is not written into output layers.

## API usage and limits

Point querying is lightweight, but it is still **one API request per point per selected dataset**. OpenTopography applies daily API limits, so for large datasets use **selected features only** or split the work into sensible batches.

## Vertical CRS matters

Different elevation products may use different vertical reference systems. The Point Elevation API returns vertical CRS information with its result. This plugin stores the API-returned EPSG identifier in `ot_vcrs` when metadata fields are enabled instead of assuming every DEM uses the same vertical datum.

## Installation

1. Download `OpenTopography-Point-Elevation.zip`.
2. In QGIS open **Plugins → Manage and Install Plugins…**.
3. Choose **Install from ZIP**.
4. Select the ZIP and install it.
5. Open the plugin from the toolbar or **Vector → OpenTopography Point Elevation**.

## Credits

This plugin is a **new, separate implementation** for point elevation workflows.

- Elevation service and dataset access: **OpenTopography** — https://opentopography.org/
- Point Elevation API documentation: https://portal.opentopography.org/apidocs/#/Public/getPointElevation
- Architectural/workflow inspiration: **OpenTopography DEM Downloader QGIS plugin** by **Kyaw Naing Win** — https://github.com/knwin/OpenTopography-DEM-Downloader-qgis-plugin

The inspiration plugin downloads raster DEMs for extents. This plugin instead focuses on the newer single-coordinate Point Elevation API and point-attribute workflows.

## License

GNU General Public License v3.0 or later. See `LICENSE`.
