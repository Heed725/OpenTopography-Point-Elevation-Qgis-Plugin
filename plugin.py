# -*- coding: utf-8 -*-
"""Main QGIS plugin class."""

import os

from qgis.PyQt.QtGui import QIcon
try:
    from qgis.PyQt.QtGui import QAction
except ImportError:
    from qgis.PyQt.QtWidgets import QAction

from qgis.core import QgsApplication
import processing

from .processing_provider import OpenTopographyPointElevationProvider


class OpenTopographyPointElevationPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.provider = None

    def initGui(self):
        self.provider = OpenTopographyPointElevationProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

        icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
        self.action = QAction(
            QIcon(icon_path),
            "OpenTopography Point Elevation",
            self.iface.mainWindow(),
        )
        self.action.setObjectName("OpenTopographyPointElevationAction")
        self.action.setToolTip(
            "Add OpenTopography elevation values to a point layer"
        )
        self.action.triggered.connect(self.run)
        self.iface.addPluginToVectorMenu(
            "&OpenTopography Point Elevation", self.action
        )
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        if self.provider:
            QgsApplication.processingRegistry().removeProvider(self.provider)
            self.provider = None
        if self.action:
            self.iface.removePluginVectorMenu(
                "&OpenTopography Point Elevation", self.action
            )
            self.iface.removeToolBarIcon(self.action)
            self.action.deleteLater()
            self.action = None

    def run(self):
        """Open the same algorithm dialog shown in the Processing Toolbox."""
        processing.execAlgorithmDialog(
            "ot_point_elevation:add_elevation_to_points",
            {},
        )
