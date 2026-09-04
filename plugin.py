# -*- coding: utf-8 -*-
"""Main QGIS plugin class."""

import os

from qgis.PyQt.QtGui import QIcon
try:
    from qgis.PyQt.QtGui import QAction
except ImportError:
    from qgis.PyQt.QtWidgets import QAction

from qgis.core import QgsApplication

from .dialog import OpenTopographyPointElevationDialog
from .processing_provider import OpenTopographyPointElevationProvider


class OpenTopographyPointElevationPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.dialog = None
        self.provider = None

    def initGui(self):
        self.provider = OpenTopographyPointElevationProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

        icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
        self.action = QAction(QIcon(icon_path), "OpenTopography Point Elevation", self.iface.mainWindow())
        self.action.setObjectName("OpenTopographyPointElevationAction")
        self.action.setToolTip("Query OpenTopography elevation for point layers or clicked points")
        self.action.triggered.connect(self.run)
        self.iface.addPluginToVectorMenu("&OpenTopography Point Elevation", self.action)
        self.iface.addToolBarIcon(self.action)

    def unload(self):
        if self.dialog:
            self.dialog.close()
            self.dialog.deleteLater()
            self.dialog = None
        if self.provider:
            QgsApplication.processingRegistry().removeProvider(self.provider)
            self.provider = None
        if self.action:
            self.iface.removePluginVectorMenu("&OpenTopography Point Elevation", self.action)
            self.iface.removeToolBarIcon(self.action)
            self.action.deleteLater()
            self.action = None

    def run(self):
        if self.dialog is None:
            self.dialog = OpenTopographyPointElevationDialog(self.iface)
            # The original OpenTopography DEM Downloader always persists the
            # entered access key in QgsSettings. Keep the same user experience
            # here: there is no separate remember-key decision for the user.
            if hasattr(self.dialog, "remember_key"):
                self.dialog.remember_key.setChecked(True)
                self.dialog.remember_key.hide()
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()
