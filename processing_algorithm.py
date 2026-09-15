# -*- coding: utf-8 -*-
"""Processing algorithm: copy points and append OpenTopography elevation."""

from qgis.PyQt import QtCore
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeature,
    QgsFeatureSink,
    QgsField,
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterString,
    QgsProject,
    QgsSettings,
)

from .api import (
    DATASETS,
    SETTINGS_KEY,
    OpenTopographyApiError,
    dataset_label,
    query_elevation,
)


try:
    FIELD_DOUBLE = QtCore.QMetaType.Type.Double
    FIELD_STRING = QtCore.QMetaType.Type.QString
except AttributeError:
    FIELD_DOUBLE = QtCore.QVariant.Double
    FIELD_STRING = QtCore.QVariant.String

try:
    POINT_SOURCE_TYPE = QgsProcessing.SourceType.TypeVectorPoint
except AttributeError:
    # QGIS 3.4 exposes the same enum member without its scoped enum name.
    POINT_SOURCE_TYPE = getattr(QgsProcessing, "TypeVectorPoint")

try:
    FAST_INSERT = QgsFeatureSink.Flag.FastInsert
except AttributeError:
    # Compatibility with the unscoped enum exposed by older QGIS 3.x builds.
    FAST_INSERT = getattr(QgsFeatureSink, "FastInsert")


class AddElevationToPointsAlgorithm(QgsProcessingAlgorithm):
    INPUT = "INPUT"
    DATASET = "DATASET"
    ACCESS_KEY_PARAMETER = "OT_AUTH_TOKEN"
    OUTPUT = "OUTPUT"

    def tr(self, text):
        return QtCore.QCoreApplication.translate(
            "OpenTopographyPointElevation", text
        )

    def createInstance(self):
        return AddElevationToPointsAlgorithm()

    def name(self):
        return "add_elevation_to_points"

    def displayName(self):
        return self.tr("Add OpenTopography elevation to points")

    def group(self):
        return self.tr("Point Elevation")

    def groupId(self):
        return "point_elevation"

    def shortHelpString(self):
        return self.tr(
            "Queries the OpenTopography Point Elevation API once per input "
            "point and creates a new output layer containing the original "
            "attributes plus ot_elev, ot_dem, ot_vcrs and ot_unit. Input "
            "coordinates are transformed to WGS84 before querying. "
            "Multipart point features use their first point. Paste your "
            "OpenTopography access key into the tool. The key is saved in "
            "this QGIS profile and pre-filled the next time, matching the "
            "OpenTopography DEM Downloader workflow. "
            "OpenTopography daily API limits apply."
        )

    def initAlgorithm(self, config=None):
        settings = QgsSettings()
        ot_auth_token = settings.value(SETTINGS_KEY, "", type=str)
        if not ot_auth_token:
            auth_prompt = self.tr("Enter OpenTopography access key")
        else:
            auth_prompt = self.tr(
                "Enter OpenTopography access key (or use existing one below)"
            )

        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT,
                self.tr("Input point layer"),
                [POINT_SOURCE_TYPE],
            )
        )
        self.addParameter(
            QgsProcessingParameterEnum(
                self.DATASET,
                self.tr("OpenTopography elevation dataset"),
                options=[dataset_label(x) for x in DATASETS],
                defaultValue=0,
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.ACCESS_KEY_PARAMETER,
                auth_prompt,
                multiLine=False,
                defaultValue=ot_auth_token,
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT, self.tr("Points with elevation")
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, self.INPUT, context)
        if source is None:
            raise QgsProcessingException(
                self.invalidSourceError(parameters, self.INPUT)
            )

        dataset_index = self.parameterAsEnum(parameters, self.DATASET, context)
        dataset = DATASETS[dataset_index][0]
        settings = QgsSettings()
        api_key = self.parameterAsString(
            parameters, self.ACCESS_KEY_PARAMETER, context
        ).strip()
        if not api_key:
            raise QgsProcessingException(
                self.tr("Enter your OpenTopography access key.")
            )

        fields = source.fields()
        output_defs = [
            ("ot_elev", FIELD_DOUBLE),
            ("ot_dem", FIELD_STRING),
            ("ot_vcrs", FIELD_STRING),
            ("ot_unit", FIELD_STRING),
        ]
        added_field_names = []
        for field_name, field_type in output_defs:
            if fields.indexOf(field_name) < 0:
                fields.append(QgsField(field_name, field_type))
                added_field_names.append(field_name)

        output_indexes = {
            name: fields.indexOf(name) for name, _ in output_defs
        }

        sink, dest_id = self.parameterAsSink(
            parameters,
            self.OUTPUT,
            context,
            fields,
            source.wkbType(),
            source.sourceCrs(),
        )
        if sink is None:
            raise QgsProcessingException(
                self.invalidSinkError(parameters, self.OUTPUT)
            )

        to_wgs84 = None
        if source.sourceCrs().authid() != "EPSG:4326":
            to_wgs84 = QgsCoordinateTransform(
                source.sourceCrs(),
                QgsCoordinateReferenceSystem("EPSG:4326"),
                QgsProject.instance(),
            )

        total = source.featureCount()
        step = 100.0 / total if total else 0

        for i, feature in enumerate(source.getFeatures()):
            if feedback.isCanceled():
                break

            out = QgsFeature(fields)
            out.setGeometry(feature.geometry())
            attrs = list(feature.attributes())
            attrs += [None] * len(added_field_names)
            result_values = {
                "ot_elev": None,
                "ot_dem": dataset,
                "ot_vcrs": "",
                "ot_unit": "",
            }

            geom = feature.geometry()
            if geom and not geom.isEmpty():
                if geom.isMultipart():
                    pts = geom.asMultiPoint()
                    pt = pts[0] if pts else None
                else:
                    pt = geom.asPoint()
                if pt is not None:
                    if to_wgs84:
                        pt = to_wgs84.transform(pt)
                    try:
                        result = query_elevation(
                            pt.x(), pt.y(), dataset, api_key
                        )
                    except OpenTopographyApiError as exc:
                        raise QgsProcessingException(str(exc)) from exc
                    if not result.no_data and result.elevation is not None:
                        result_values = {
                            "ot_elev": result.elevation,
                            "ot_dem": result.shortname,
                            "ot_vcrs": result.vcrs_epsg,
                            "ot_unit": result.unit,
                        }

            for field_name, value in result_values.items():
                attrs[output_indexes[field_name]] = value
            out.setAttributes(attrs)
            if not sink.addFeature(out, FAST_INSERT):
                raise QgsProcessingException(
                    self.tr("Could not write an output feature.")
                )

            feedback.setProgress(int((i + 1) * step))

        # Same persistence pattern as OpenTopography DEM Downloader: after a
        # run, keep the key in this QGIS profile and pre-fill it next time.
        settings.setValue(SETTINGS_KEY, api_key)
        return {self.OUTPUT: dest_id}
