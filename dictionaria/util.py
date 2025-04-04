"""Misc. utility functions for Dictionaria."""

import re
import textwrap
from collections import defaultdict

from clld.db.meta import DBSession
from clld.db.models import common
from clld.web.util import concepticon
from clld.web.util.helpers import link
from clld.web.util.htmllib import HTML, escape
from clldmpg import cdstar
from clldutils.misc import UnicodeMixin

assert cdstar
assert link

MULT_VALUE_SEP = ' ; '
MARKDOWN_LINK_PATTERN = re.compile(r'\[(?P<label>[^\]]+)\]\((?P<uid>[^)]+)\)')


def last_first(contributor):
    """Reformat contributor name to Last, First."""
    if contributor.id == 'baezgabriela':
        parts = contributor.name.split()
        first = parts[0]
        last = ' '.join(parts[1:])
        return f'{last}, {first}'
    else:
        return contributor.last_first()


def add_word_links(req, contrib, text):
    """Replace markdown links with HTML links to the respective word."""
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


def drop_word_links(text):
    """Replace markdown links with some placeholder text."""
    return MARKDOWN_LINK_PATTERN.sub(lambda m: m.group('label'), text)


def truncate(s):
    """Limit text to 70 characters."""
    return textwrap.shorten(s, width=70)


def split(s):
    """Split string based on our project-wide default separator."""
    return [ss.strip() for ss in s.split(MULT_VALUE_SEP) if ss.strip()]


def join(iterable):
    """Join string based on our project-wide default separator."""
    return MULT_VALUE_SEP.join(iterable)


def concepticon_link(request, meaning):
    """Generate link to Concepticon."""
    return concepticon.link(request, meaning.concepticon_url.split('/')[-1])


def toc(soup):
    """Generate table of contents for an introduction text (HTML)."""
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
