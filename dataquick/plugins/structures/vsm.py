from collections import OrderedDict
from dataquick.structures import DataQuickFrame, register_data_structures


class VSM(DataQuickFrame):
    """
    A class for Vibrating Sample Magnetometer measurements.  Although these measurements can get quite complicated,
    measurements versus angle, the typical measurement is a measurement of applied field (in Gauss) versus magnetic
    moment of the sample (in emu)
    """

    label = "VSM"

    _required_metadata = DataQuickFrame._required_metadata.copy()
    _required_metadata.update({
        "mass": 1,
        "density": 1
    })

    _x = "Field"
    _y = "Moment"

    _required_columns = OrderedDict((
        ("Field", float),
        ("Moment", float),
    ))
    _column_properties = []
    _loaders = []


register_data_structures(VSM)
