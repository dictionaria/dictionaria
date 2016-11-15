# coding: utf8
from __future__ import unicode_literals

from clld.web.util.htmllib import HTML
from clldmpg import cdstar
from clld.web.util.helpers import link

MULT_VALUE_SEP = ' ; '


def split(s):
    return [ss.strip() for ss in s.split(MULT_VALUE_SEP) if ss.strip()]


def join(iterable):
    return MULT_VALUE_SEP.join(iterable)


def concepticon_link(request, meaning):
    return HTML.a(
        HTML.img(
            src=request.static_url('dictionaria:static/concepticon_logo.png'),
            height=20,
            width=30),
        title='corresponding concept set at Concepticon',
        href=meaning.concepticon_url)
