# -*- coding: utf-8 -*-
"""Interactive canvas point picker."""

from qgis.gui import QgsMapToolEmitPoint


class PointPickTool(QgsMapToolEmitPoint):
    """Thin named subclass so plugin ownership/cleanup is explicit."""

    pass
