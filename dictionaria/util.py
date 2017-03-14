# coding: utf8
from __future__ import unicode_literals
from collections import OrderedDict

from clld.web.util.htmllib import HTML
from bs4 import BeautifulSoup
from clldmpg import cdstar
from clld.web.util.helpers import link
assert cdstar and link

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


def toc(s):
    if not s:
        return '', ''

    def link(id_, label):
        return HTML.a(label, href='#{0}'.format(id_))

    def toplink(html):
        a = html.new_tag(
            'a',
            href='#top',
            title='go to top of the page',
            style="vertical-align: bottom")
        a.string = '⇫'
        return a

    def permalink(html, id_):
        a = html.new_tag(
            'a',
            **{
                'href': '#{0}'.format(id_),
                'title': 'Permalink to this headline',
                'class': "headerlink"})
        a.string = '¶'
        return a

    toc_, count = [], 0
    text = BeautifulSoup(s)
    for d in text.descendants:
        if d.name in ['h1', 'h2', 'h3', 'h4', 'h5']:
            count += 1
            id_ = 'section{0}'.format(count)
            toc_.append((id_, int(d.name[1:]), d.get_text()))
            d.insert(0, text.new_tag('a', id=id_))
            d.append(toplink(text))
            d.append(permalink(text, id_))

    if toc_:
        top_level = min(t[1] for t in toc_)
        nt = OrderedDict()
        curr = []
        for id_, level, label in toc_:
            if level == top_level:
                curr = nt[(id_, label)] = []
            elif level == top_level + 1:
                curr.append((id_, label))
        toc_ = HTML.ul(*[HTML.li(link(*t), HTML.ul(*[HTML.li(link(*tt)) for tt in ns]))
                         for t, ns in nt.items()])
    else:
        toc_ = ''
    return '{0}'.format(text), toc_
