# coding: utf8
from __future__ import unicode_literals

from dictionaria.scripts.util import default_value_converter


MARKER_MAP = dict(
    mr=('morphology', default_value_converter),
    sc=('scientific', default_value_converter),
)
