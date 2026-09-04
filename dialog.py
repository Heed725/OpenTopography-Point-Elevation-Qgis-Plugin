# -*- coding: utf-8 -*-
"""Main non-modal dialog for OpenTopography Point Elevation."""

from datetime import datetime, timezone

from qgis.PyQt.QtCore import Qt, QVariant
from qgis.PyQt.QtGui import QDesktopServices
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from qgis.PyQt.QtCore import QUrl

from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeature,
    QgsField,
    QgsGeometry,
    QgsMapLayerProxyModel,
    QgsPointXY,
    QgsProject,
    QgsSettings,
    QgsVectorLayer,
    QgsWkbTypes,
)
from qgis.gui import QgsMapLayerComboBox

from .api import DATASETS, SETTINGS_KEY, OpenTopographyApiError, dataset_label, query_elevation
from .map_tool import PointPickTool


class OpenTopographyPointElevationDialog(QDialog):
    def __init__(self, iface, parent=None):
        super().__init__(parent or iface.mainWindow())
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.settings = QgsSettings()
        self.pick_tool = PointPickTool(self.canvas)
        self.pick_tool.canvasClicked.connect(self._canvas_clicked)
        self.previous_map_tool = None
        self.output_point_layer = None
        self._build_ui()
        self._refresh_dataset_info()

    def _build_ui(self):
        self.setWindowTitle("OpenTopography Point Elevation")
        self.resize(780, 610)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

        root = QVBoxLayout(self)

        intro = QLabel(
            "Query elevation for points without downloading a full DEM. "
            "Choose an OpenTopography dataset, then enrich an existing point layer "
            "or click/create new elevation points."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        api_group = QGroupBox("OpenTopography API")
        api_form = QFormLayout(api_group)
        key_row = QHBoxLayout()
        self.api_key = QLineEdit(self.settings.value(SETTINGS_KEY, "", type=str))
        self.api_key.setEchoMode(QLineEdit.Password)
        self.api_key.setPlaceholderText("Paste your OpenTopography API key")
        self.show_key = QCheckBox("Show")
        self.show_key.toggled.connect(
            lambda checked: self.api_key.setEchoMode(QLineEdit.Normal if checked else QLineEdit.Password)
        )
        key_row.addWidget(self.api_key, 1)
        key_row.addWidget(self.show_key)
        api_form.addRow("API key:", key_row)

        self.remember_key = QCheckBox("Remember API key in this QGIS profile")
        self.remember_key.setChecked(True)
        api_form.addRow("", self.remember_key)

        link_row = QHBoxLayout()
        get_key = QPushButton("Get / manage API key")
        get_key.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://portal.opentopography.org/requestService?service=api"))
        )
        docs = QPushButton("Point API documentation")
        docs.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://portal.opentopography.org/apidocs/#/Public/getPointElevation"))
        )
        link_row.addWidget(get_key)
        link_row.addWidget(docs)
        link_row.addStretch(1)
        api_form.addRow("", link_row)
        root.addWidget(api_group)

        dataset_group = QGroupBox("Elevation dataset")
        dataset_form = QFormLayout(dataset_group)
        self.dataset_combo = QComboBox()
        for item in DATASETS:
            self.dataset_combo.addItem(dataset_label(item), item[0])
        self.dataset_combo.setCurrentIndex(0)
        self.dataset_combo.currentIndexChanged.connect(self._refresh_dataset_info)
        dataset_form.addRow("DEM / dataset:", self.dataset_combo)
        self.dataset_info = QLabel()
        self.dataset_info.setWordWrap(True)
        dataset_form.addRow("Coverage:", self.dataset_info)
        root.addWidget(dataset_group)

        tabs = QTabWidget()
        tabs.addTab(self._build_layer_tab(), "Add elevation to point layer")
        tabs.addTab(self._build_create_tab(), "Create / click elevation points")
        root.addWidget(tabs, 1)

        footer = QHBoxLayout()
        credits = QPushButton("Credits")
        credits.clicked.connect(self._show_credits)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        footer.addWidget(credits)
        footer.addStretch(1)
        footer.addWidget(close_btn)
        root.addLayout(footer)

    def _build_layer_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        form = QFormLayout()

        self.layer_combo = QgsMapLayerComboBox()
        self.layer_combo.setFilters(QgsMapLayerProxyModel.PointLayer)
        form.addRow("Point layer:", self.layer_combo)

        self.selected_only = QCheckBox("Update selected features only")
        self.selected_only.setChecked(False)
        form.addRow("Features:", self.selected_only)

        self.elev_field = QLineEdit("elev_m")
        self.elev_field.setMaxLength(30)
        self.elev_field.setToolTip("Existing field is reused; otherwise a numeric field is created.")
        form.addRow("Elevation field:", self.elev_field)

        self.add_metadata = QCheckBox("Also add dataset, vertical CRS EPSG and unit fields")
        self.add_metadata.setChecked(True)
        form.addRow("Metadata:", self.add_metadata)

        layout.addLayout(form)

        note = QLabel(
            "This mode writes values directly into the selected layer's attribute table. "
            "For multipart point features, the first point is queried. API usage is one request per feature."
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        self.enrich_button = QPushButton("Add OpenTopography elevation to layer")
        self.enrich_button.clicked.connect(self._enrich_layer)
        layout.addWidget(self.enrich_button)
        layout.addStretch(1)
        return page

    def _build_create_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        coord_group = QGroupBox("Coordinate")
        form = QFormLayout(coord_group)
        self.lon = QDoubleSpinBox()
        self.lon.setRange(-180.0, 180.0)
        self.lon.setDecimals(8)
        self.lon.setSingleStep(0.0001)
        self.lat = QDoubleSpinBox()
        self.lat.setRange(-90.0, 90.0)
        self.lat.setDecimals(8)
        self.lat.setSingleStep(0.0001)
        form.addRow("Longitude (WGS84):", self.lon)
        form.addRow("Latitude (WGS84):", self.lat)

        buttons = QHBoxLayout()
        self.add_coord_button = QPushButton("Query and add point")
        self.add_coord_button.clicked.connect(self._query_and_add_manual_point)
        self.pick_button = QPushButton("Pick points on map")
        self.pick_button.setCheckable(True)
        self.pick_button.toggled.connect(self._toggle_pick_tool)
        buttons.addWidget(self.add_coord_button)
        buttons.addWidget(self.pick_button)
        buttons.addStretch(1)
        form.addRow("", buttons)
        layout.addWidget(coord_group)

        self.create_status = QLabel(
            "New points are stored in a temporary EPSG:4326 layer named “OpenTopography Elevation Points”."
        )
        self.create_status.setWordWrap(True)
        layout.addWidget(self.create_status)

        self.results = QTableWidget(0, 6)
        self.results.setHorizontalHeaderLabels(
            ["Longitude", "Latitude", "Elevation", "Dataset", "VCRS EPSG", "Unit"]
        )
        self.results.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.results.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.results.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.results, 1)
        return page

    def _refresh_dataset_info(self):
        idx = max(0, self.dataset_combo.currentIndex()) if hasattr(self, "dataset_combo") else 0
        if not hasattr(self, "dataset_info"):
            return
        code = self.dataset_combo.itemData(idx)
        item = next((x for x in DATASETS if x[0] == code), DATASETS[0])
        self.dataset_info.setText(
            f"{item[2]} • {item[3]}. Vertical CRS and units are read from the API response for each query."
        )

    def _dataset(self):
        return self.dataset_combo.currentData()

    def _api_key_value(self):
        return self.api_key.text().strip()

    def _save_key_if_requested(self):
        if self.remember_key.isChecked():
            self.settings.setValue(SETTINGS_KEY, self._api_key_value())
        else:
            self.settings.remove(SETTINGS_KEY)

    def _ensure_api_key(self):
        if not self._api_key_value():
            QMessageBox.warning(self, "API key required", "Enter your OpenTopography API key first.")
            return False
        return True

    def _feature_point_wgs84(self, layer, feature):
        geom = feature.geometry()
        if not geom or geom.isEmpty():
            return None
        if QgsWkbTypes.geometryType(geom.wkbType()) != QgsWkbTypes.PointGeometry:
            return None

        if QgsWkbTypes.isMultiType(geom.wkbType()):
            pts = geom.asMultiPoint()
            if not pts:
                return None
            point = QgsPointXY(pts[0])
        else:
            point = QgsPointXY(geom.asPoint())

        if layer.crs().authid() != "EPSG:4326":
            transform = QgsCoordinateTransform(
                layer.crs(), QgsCoordinateReferenceSystem("EPSG:4326"), QgsProject.instance()
            )
            point = transform.transform(point)
        return point

    def _ensure_fields(self, layer, elev_name, with_metadata):
        desired = [(elev_name, QVariant.Double)]
        if with_metadata:
            desired += [
                ("ot_dem", QVariant.String),
                ("ot_vcrs", QVariant.String),
                ("ot_unit", QVariant.String),
            ]
        missing = [QgsField(name, field_type) for name, field_type in desired if layer.fields().indexOf(name) < 0]
        if missing:
            if layer.isEditable():
                for field in missing:
                    if not layer.addAttribute(field):
                        raise RuntimeError(f"Could not add field {field.name()} to the layer.")
            else:
                if not layer.dataProvider().addAttributes(missing):
                    raise RuntimeError("The data provider refused to add one or more output fields.")
            layer.updateFields()
        return {name: layer.fields().indexOf(name) for name, _ in desired}

    def _enrich_layer(self):
        if not self._ensure_api_key():
            return
        layer = self.layer_combo.currentLayer()
        if not isinstance(layer, QgsVectorLayer) or QgsWkbTypes.geometryType(layer.wkbType()) != QgsWkbTypes.PointGeometry:
            QMessageBox.warning(self, "Point layer required", "Choose a vector point layer.")
            return

        elev_name = self.elev_field.text().strip()
        if not elev_name:
            QMessageBox.warning(self, "Field name required", "Enter an elevation field name, for example elev_m.")
            return

        if self.selected_only.isChecked():
            features = list(layer.getSelectedFeatures())
            feature_count = len(features)
            if not features:
                QMessageBox.information(self, "No selected points", "Select one or more point features first.")
                return
        else:
            feature_count = layer.featureCount()
            features = layer.getFeatures()

        if feature_count <= 0:
            QMessageBox.information(self, "No features", "The selected point layer has no features.")
            return

        if feature_count > 50:
            answer = QMessageBox.question(
                self,
                "API usage warning",
                f"This will make up to {feature_count} Point Elevation API requests. "
                "OpenTopography applies daily API limits. Continue?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return

        try:
            field_indexes = self._ensure_fields(layer, elev_name, self.add_metadata.isChecked())
        except Exception as exc:
            QMessageBox.critical(self, "Cannot add fields", str(exc))
            return

        progress = QProgressDialog("Querying OpenTopography…", "Cancel", 0, feature_count, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)

        changes = {}
        no_data_count = 0
        error_count = 0
        first_error = ""

        for i, feature in enumerate(features):
            progress.setValue(i)
            if progress.wasCanceled():
                break

            pt = self._feature_point_wgs84(layer, feature)
            if pt is None:
                no_data_count += 1
                continue

            try:
                result = query_elevation(pt.x(), pt.y(), self._dataset(), self._api_key_value())
            except OpenTopographyApiError as exc:
                error_count += 1
                if not first_error:
                    first_error = str(exc)
                # Authentication/rate errors are usually repeated; stop after first API error.
                break

            if result.no_data or result.elevation is None:
                no_data_count += 1
                continue

            attrs = {field_indexes[elev_name]: result.elevation}
            if self.add_metadata.isChecked():
                attrs[field_indexes["ot_dem"]] = result.shortname
                attrs[field_indexes["ot_vcrs"]] = result.vcrs_epsg
                attrs[field_indexes["ot_unit"]] = result.unit
            changes[feature.id()] = attrs

        progress.setValue(feature_count)

        if changes:
            if layer.isEditable():
                layer.beginEditCommand("Add OpenTopography elevation")
                for fid, attrs in changes.items():
                    for field_idx, value in attrs.items():
                        layer.changeAttributeValue(fid, field_idx, value)
                layer.endEditCommand()
            else:
                if not layer.dataProvider().changeAttributeValues(changes):
                    QMessageBox.critical(self, "Write failed", "The layer provider could not write the elevation values.")
                    return
            layer.updateFields()
            layer.triggerRepaint()

        self._save_key_if_requested()

        if first_error:
            QMessageBox.warning(
                self,
                "OpenTopography query stopped",
                f"Updated {len(changes)} feature(s) before an API error occurred.\n\n{first_error}",
            )
        else:
            QMessageBox.information(
                self,
                "Elevation complete",
                f"Updated {len(changes)} feature(s). No-data/skipped: {no_data_count}."
                + (" Operation was cancelled." if progress.wasCanceled() else ""),
            )

        self.iface.messageBar().pushMessage(
            "OpenTopography Point Elevation",
            f"Wrote elevation to {len(changes)} point feature(s).",
            level=Qgis.Success,
            duration=5,
        )

    def _toggle_pick_tool(self, enabled):
        if enabled:
            if not self._ensure_api_key():
                self.pick_button.blockSignals(True)
                self.pick_button.setChecked(False)
                self.pick_button.blockSignals(False)
                return
            self.previous_map_tool = self.canvas.mapTool()
            self.canvas.setMapTool(self.pick_tool)
            self.pick_button.setText("Stop picking")
            self.iface.messageBar().pushMessage(
                "OpenTopography Point Elevation",
                "Click the map to query elevation and create a point.",
                level=Qgis.Info,
                duration=4,
            )
        else:
            if self.canvas.mapTool() == self.pick_tool:
                if self.previous_map_tool:
                    self.canvas.setMapTool(self.previous_map_tool)
                else:
                    self.canvas.unsetMapTool(self.pick_tool)
            self.pick_button.setText("Pick points on map")

    def _canvas_clicked(self, point, button):
        try:
            canvas_crs = self.canvas.mapSettings().destinationCrs()
            if canvas_crs.authid() != "EPSG:4326":
                transform = QgsCoordinateTransform(
                    canvas_crs, QgsCoordinateReferenceSystem("EPSG:4326"), QgsProject.instance()
                )
                point = transform.transform(QgsPointXY(point))
            else:
                point = QgsPointXY(point)
            self.lon.setValue(point.x())
            self.lat.setValue(point.y())
            self._query_and_add_point(point.x(), point.y())
        except Exception as exc:
            QMessageBox.critical(self, "Point conversion failed", str(exc))

    def _query_and_add_manual_point(self):
        if not self._ensure_api_key():
            return
        self._query_and_add_point(self.lon.value(), self.lat.value())

    def _query_and_add_point(self, longitude, latitude):
        try:
            result = query_elevation(longitude, latitude, self._dataset(), self._api_key_value())
        except OpenTopographyApiError as exc:
            QMessageBox.warning(self, "OpenTopography API", str(exc))
            return

        if result.no_data or result.elevation is None:
            QMessageBox.information(
                self,
                "No elevation data",
                "The selected dataset returned no data at this location. Try another dataset if appropriate.",
            )
            return

        layer = self._get_or_create_output_layer()
        feature = QgsFeature(layer.fields())
        feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(longitude, latitude)))
        feature.setAttributes(
            [
                layer.featureCount() + 1,
                float(longitude),
                float(latitude),
                result.elevation,
                result.shortname,
                result.vcrs_epsg,
                result.unit,
                datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            ]
        )
        layer.dataProvider().addFeature(feature)
        layer.updateExtents()
        layer.triggerRepaint()

        row = self.results.rowCount()
        self.results.insertRow(row)
        values = [
            f"{longitude:.8f}",
            f"{latitude:.8f}",
            f"{result.elevation:.3f}",
            result.shortname,
            result.vcrs_epsg,
            result.unit,
        ]
        for col, value in enumerate(values):
            self.results.setItem(row, col, QTableWidgetItem(str(value)))
        self.results.scrollToBottom()
        self.create_status.setText(
            f"Added point: {result.elevation:.3f} {result.unit} from {result.shortname}. "
            "The temporary layer is in the Layers panel and can be exported with Save Features As…"
        )
        self._save_key_if_requested()

    def _get_or_create_output_layer(self):
        if self.output_point_layer and QgsProject.instance().mapLayer(self.output_point_layer.id()):
            return self.output_point_layer

        layer = QgsVectorLayer("Point?crs=EPSG:4326", "OpenTopography Elevation Points", "memory")
        provider = layer.dataProvider()
        provider.addAttributes(
            [
                QgsField("id", QVariant.Int),
                QgsField("longitude", QVariant.Double),
                QgsField("latitude", QVariant.Double),
                QgsField("elev_m", QVariant.Double),
                QgsField("ot_dem", QVariant.String),
                QgsField("ot_vcrs", QVariant.String),
                QgsField("ot_unit", QVariant.String),
                QgsField("queried_utc", QVariant.String),
            ]
        )
        layer.updateFields()
        QgsProject.instance().addMapLayer(layer)
        self.output_point_layer = layer
        return layer

    def _show_credits(self):
        QMessageBox.information(
            self,
            "Credits",
            "OpenTopography Point Elevation\n\n"
            "Uses the OpenTopography Point Elevation API.\n"
            "Inspired by the OpenTopography DEM Downloader QGIS plugin by Kyaw Naing Win.\n"
            "This plugin is a separate implementation designed for point elevation workflows.\n\n"
            "OpenTopography: https://opentopography.org/\n"
            "Inspiration: https://github.com/knwin/OpenTopography-DEM-Downloader-qgis-plugin",
        )

    def closeEvent(self, event):
        if self.pick_button.isChecked():
            self.pick_button.setChecked(False)
        event.accept()
