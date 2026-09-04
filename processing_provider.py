# -*- coding: utf-8 -*-

import os

from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsProcessingProvider

from .processing_algorithm import AddElevationToPointsAlgorithm


class OpenTopographyPointElevationProvider(QgsProcessingProvider):
    def loadAlgorithms(self):
        self.addAlgorithm(AddElevationToPointsAlgorithm())

    def id(self):
        return "ot_point_elevation"

    def name(self):
        return "OpenTopography"

    def longName(self):
        return "OpenTopography Point Elevation"

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__), "icon.png"))
