# -*- coding: utf-8 -*-
"""OpenTopography Point Elevation API helpers."""

from dataclasses import dataclass
from typing import Optional

import requests

BASE_URL = "https://portal.opentopography.org/API/v1/elevation"
SETTINGS_KEY = "OpenTopographyPointElevation/api_key"


# Dataset shortnames are from the OpenTopography Point Elevation API docs.
# Coverage/resolution are display hints only; the API response remains the
# authority for vertical CRS and units.
DATASETS = [
    ("COP30", "Copernicus Global DSM 30 m", "Global", "30 m"),
    ("COP90", "Copernicus Global DSM 90 m", "Global", "90 m"),
    ("SRTM_GL1", "SRTM GL1", "Global", "30 m"),
    ("SRTM_GL1_Ellip", "SRTM GL1 Ellipsoidal", "Global", "30 m"),
    ("SRTM_GL3", "SRTM GL3", "Global", "90 m"),
    ("NASADEM", "NASADEM", "Global", "30 m"),
    ("AW3D30", "ALOS World 3D", "Global", "30 m"),
    ("AW3D30_E", "ALOS World 3D Ellipsoidal", "Global", "30 m"),
    ("GEDTM30", "Global Ensemble Digital Terrain Model", "Global", "30 m"),
    ("SRTM15Plus", "SRTM15+", "Global land + ocean", "~500 m"),
    ("GEBCOIceTopo", "GEBCO IceTopo", "Global land + ocean", "~500 m"),
    ("GEBCOSubIceTopo", "GEBCO SubIceTopo", "Global land + ocean", "~500 m"),
    ("GEDI_L3", "GEDI L3", "Approx. 52°S to 52°N", "1 km"),
    ("ANADEM", "ANADEM", "South America", "30 m"),
    ("EU_DTM", "EU DTM", "Europe", "30 m"),
    ("USGS10m", "USGS 3DEP", "USA / North America", "10 m"),
    ("USGS30m", "USGS 3DEP", "USA / North America", "30 m"),
    ("CA_MRDEM", "Canada MRDEM", "Canada", "30 m"),
    ("LINZ1m_DSM", "LINZ DSM", "New Zealand", "1 m"),
    ("LINZ1m_DTM", "LINZ DTM", "New Zealand", "1 m"),
    ("ArcticDEM2m", "ArcticDEM", "Arctic", "2 m"),
    ("ArcticDEM10m", "ArcticDEM", "Arctic", "10 m"),
    ("ArcticDEM32m", "ArcticDEM", "Arctic", "32 m"),
    ("REMA2m", "REMA", "Antarctica", "2 m"),
    ("REMA10m", "REMA", "Antarctica", "10 m"),
    ("REMA32m", "REMA", "Antarctica", "32 m"),
]


def dataset_label(item):
    code, name, coverage, resolution = item
    return f"{name} ({code}) — {resolution} — {coverage}"


class OpenTopographyApiError(RuntimeError):
    """A safe API error that never exposes the user's API key."""


@dataclass
class ElevationResult:
    elevation: Optional[float]
    shortname: str
    vcrs_epsg: str
    vcrs_wkt: str
    unit: str
    no_data: bool = False


def _response_message(response):
    """Extract a short useful message without including the request URL/API key."""
    try:
        data = response.json()
        if isinstance(data, dict):
            for key in ("detail", "message", "error", "Error"):
                if data.get(key):
                    return str(data[key])[:500]
    except Exception:
        pass
    text = (response.text or "").strip().replace("\n", " ")
    return text[:500] if text else "No additional error details were returned."


def query_elevation(longitude, latitude, dataset, api_key, timeout=30):
    """Query one coordinate and one OpenTopography dataset."""
    if not api_key or not api_key.strip():
        raise OpenTopographyApiError("An OpenTopography API key is required.")

    params = {
        "longitude": f"{float(longitude):.10f}",
        "latitude": f"{float(latitude):.10f}",
        "dataset": dataset,
        "API_Key": api_key.strip(),
    }

    try:
        response = requests.get(BASE_URL, params=params, timeout=timeout)
    except requests.RequestException as exc:
        raise OpenTopographyApiError(f"Could not connect to OpenTopography: {exc}") from exc

    # Documented expected responses for no-data/out-of-coverage point queries.
    if response.status_code in (404, 422):
        return ElevationResult(None, dataset, "", "", "", no_data=True)

    if not response.ok:
        raise OpenTopographyApiError(
            f"OpenTopography returned HTTP {response.status_code}: {_response_message(response)}"
        )

    try:
        data = response.json()
    except ValueError as exc:
        raise OpenTopographyApiError("OpenTopography returned a non-JSON response.") from exc

    elev = data.get("Elevation")
    if elev in (None, "", "null"):
        value = None
        no_data = True
    else:
        try:
            value = float(elev)
            no_data = False
        except (TypeError, ValueError) as exc:
            raise OpenTopographyApiError(
                f"Unexpected Elevation value returned by OpenTopography: {elev!r}"
            ) from exc

    return ElevationResult(
        elevation=value,
        shortname=str(data.get("Shortname") or dataset),
        vcrs_epsg=str(data.get("VCRS_EPSG") or ""),
        vcrs_wkt=str(data.get("VCRS_WKT") or ""),
        unit=str(data.get("Unit") or "Meters"),
        no_data=no_data,
    )
