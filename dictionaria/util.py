# coding: utf8
from __future__ import unicode_literals
from collections import OrderedDict, defaultdict
import re

from clldutils.text import truncate_with_ellipsis
from clldutils.misc import UnicodeMixin
from clld.web.util.htmllib import HTML
from clld.db.models import common
from clld.db.meta import DBSession
from bs4 import BeautifulSoup
from clldmpg import cdstar
from clld.web.util.helpers import link
assert cdstar and link

MULT_VALUE_SEP = ' ; '


def add_links2(sid, ids, desc, type_):
    if not desc:
        return
    if not ids:
        return desc
    p = re.compile(
        '((?<=\W)|^)(?P<id>{0})(?=\W|$)'.format('|'.join(re.escape(id_) for id_ in ids if id_)),
        flags=re.MULTILINE)
    return p.sub(lambda m: '{0}'.format(Link(sid + '-' + m.group('id'), type_)), desc)


def unit_detail_html(request=None, context=None, **kw):
    labels = {}
    for type_, cls in [('source', common.Source), ('unit', common.Unit)]:
        labels[type_] = defaultdict(set)
        for r in DBSession.query(cls.id):
            sid, _, lid = r[0].partition('-')
            labels[type_][sid].add(lid)

    res = {}
    for k, v in context.datadict().items():
        if k.endswith('_links'):
            v = v.replace('<', '&lt;').replace('>', '&gt;')
            for type_ in ['source', 'unit']:
                v = add_links2(
                    context.dictionary.id, labels[type_][context.dictionary.id], v, type_)
            res[k.replace('_links', '')] = add_links(request, v)
    return dict(links=res)


def truncate(s):
    return truncate_with_ellipsis(s, width=70)


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


class Link(UnicodeMixin):
    def __init__(self, id, type):
        self.id = id
        self.type = type

    def __unicode__(self):
        return '**{0.type}:{0.id}**'.format(self)

    def sub(self, s, req, labels=None):
        if not labels:
            cls = getattr(common, self.type.capitalize())
            labels = {r[0]: r[1] for r in DBSession.query(cls.id, cls.name)}

        def _repl(m):
            if m.group('id') in labels:
                return '<a href="{0}">{1}</a>'.format(
                    req.route_url(self.type, id=m.group('id')), labels[m.group('id')])
            return m.string

        return re.sub('\*\*{0}:(?P<id>[^*]+)\*\*'.format(self.type), _repl, s)


def add_links(req, s):
    for type_ in ['source', 'unit']:
        s = Link(None, type_).sub(s, req)
    return s


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
    text = BeautifulSoup(s, 'html5lib')
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
