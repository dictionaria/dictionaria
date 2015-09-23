# coding: utf8
from __future__ import unicode_literals

from clld.web.util.htmllib import HTML


def concepticon_link(request, meaning):
    return HTML.a(
        HTML.img(
            src=request.static_url('dictionaria:static/concepticon_logo.png'),
            height=20,
            width=30),
        title='corresponding concept set at Concepticon',
        href=meaning.concepticon_url)
