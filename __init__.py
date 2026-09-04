# -*- coding: utf-8 -*-
"""QGIS entry point for OpenTopography Point Elevation."""


def classFactory(iface):  # pylint: disable=invalid-name
    from .plugin import OpenTopographyPointElevationPlugin
    return OpenTopographyPointElevationPlugin(iface)
