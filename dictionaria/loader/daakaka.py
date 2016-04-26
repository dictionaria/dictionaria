# coding: utf8
from __future__ import unicode_literals

from dictionaria.scripts.util import default_value_converter


MARKER_MAP = dict(
    ue=('usage', default_value_converter),
    et=('et', default_value_converter),
    es=('es', default_value_converter),
    ee=('ee', default_value_converter),
)
