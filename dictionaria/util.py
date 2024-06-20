from collections import defaultdict
import re
import textwrap

from clldutils.misc import UnicodeMixin
from clld.db.models import common
from clld.db.meta import DBSession
from clldmpg import cdstar
from clld.web.util.helpers import link
from clld.web.util.htmllib import HTML, escape
from clld.web.util import concepticon
assert cdstar and link

MULT_VALUE_SEP = ' ; '
MARKDOWN_LINK_PATTERN = re.compile(r'\[(?P<label>[^\]]+)\]\((?P<uid>[^)]+)\)')


def last_first(contrib):
    if contrib.id == 'baezgabriela':
        return '{}, {}'.format(
            ' '.join(contrib.name.split()[1:]),
            contrib.name.split()[0])
    return contrib.last_first()


def add_unit_links(req, contrib, text):
    res, pos = [], 0
    for m in MARKDOWN_LINK_PATTERN.finditer(text):
        if m.start() > pos:
            res.append(escape(text[pos:m.start()]))
        res.append(HTML.a(
            m.group('label'),
            href=req.route_url('unit', id='{}-{}'.format(contrib.id, m.group('uid')))))
        pos = m.end()
    if pos < len(text):
        res.append(escape(text[pos:]))
    return HTML.span(*res)


def drop_unit_links(text):
    return MARKDOWN_LINK_PATTERN.sub(lambda m: m.group('label'), text)


def add_links2(sid, ids, desc, type_):
    if not desc:
        return
    if not ids:
        return desc
    p = re.compile(
        r'((?<=\W)|^)(?P<id>{0})(?=\W|$)'.format('|'.join(re.escape(id_) for id_ in ids if id_)),
        flags=re.MULTILINE)
    return p.sub(lambda m: str(Link(sid + '-' + m.group('id'), type_)), desc)


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
    return textwrap.shorten(s, width=70)


def split(s):
    return [ss.strip() for ss in s.split(MULT_VALUE_SEP) if ss.strip()]


def join(iterable):
    return MULT_VALUE_SEP.join(iterable)


def concepticon_link(request, meaning):
    return concepticon.link(request, meaning.concepticon_url.split('/')[-1])


class Link(UnicodeMixin):
    def __init__(self, id, type):
        self.id = id
        self.type = type

    def __unicode__(self):
        return f'**{self.type}:{self.id}**'

    def sub(self, s, req, labels=None):
        if not labels:
            cls = getattr(common, self.type.capitalize())
            labels = {r[0]: r[1] for r in DBSession.query(cls.id, cls.name)}

        def _repl(m):
            if m.group('id') in labels:
                return '<a href="{}">{}</a>'.format(
                    req.route_url(self.type, id=m.group('id')),
                    labels[m.group('id')])
            return m.string

        return re.sub(r'\*\*{0}:(?P<id>[^*]+)\*\*'.format(self.type), _repl, s)


def add_links(req, s):
    for type_ in ['source', 'unit']:
        s = Link(None, type_).sub(s, req)
    return s


def toc(soup):
    def link(id_, label):
        return HTML.a(label, href=f'#{id_}')

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
                'href': f'#{id_}',
                'title': 'Permalink to this headline',
                'class': "headerlink"})
        a.string = '¶'
        return a

    toc_, count = [], 0
    for d in soup.descendants:
        if d.name in ['h1', 'h2', 'h3', 'h4', 'h5']:
            count += 1
            id_ = f'section{count}'
            toc_.append((id_, int(d.name[1:]), d.get_text()))
            d.insert(0, soup.new_tag('a', id=id_))
            d.append(toplink(soup))
            d.append(permalink(soup, id_))

    if toc_:
        top_level = min(t[1] for t in toc_)
        nt = {}
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
    return str(soup), toc_
