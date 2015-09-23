# coding: utf8
from __future__ import unicode_literals
from collections import OrderedDict

from path import path
from clld.db.meta import DBSession
from clld.db.models import common
from clld.util import slug

import dictionaria
from dictionaria import models
from dictionaria.lib.sfm import Dictionary, Entry


MARKER_MAP = dict(
    sd=('semantic domain', lambda d: d['sd']),
    mr=('morphology', lambda d: d['mr']),
    re=('translation equivalent', lambda d: d['re']),
    sc=('scientific', lambda d: d['sc']),
)

POS_MAP = {
    'adj': 'adjective',
    'adj1': 'adjective',
    'adj2': 'adjective',
    'adv': 'adverb',
    'al': 'other',
    'art': 'determiner',
    'aux': 'auxiliary verb',
    'class': 'other',
    'comp': 'other',
    'conj': 'conjunction',
    'contpart': 'other',
    'cop': 'other',
    'dem': 'determiner',
    'det': 'determiner',
    'disc': 'other',
    'intj': 'other',
    'intr': 'intransitive verb',
    'intrr': 'intransitive verb',
    'mod': 'other',
    'modal.tag': 'other',
    'n': 'noun',
    'n.pre': 'noun',
    'n.pref': 'noun',
    'n.rel': 'noun',
    'n.rel.b': 'noun',
    'n.suf': 'noun',
    'name': 'noun',
    'nom': 'other',
    'num': 'numeral',
    'number': 'other',
    'p.rel.b': 'other',
    'place': 'other',
    'poss.pron': 'pronoun',
    'pref': 'other',
    'prep': 'adposition',
    'prepp': 'adposition',
    'pron': 'pronoun',
    'pron.poss': 'pronoun',
    'q': 'quantifier',
    'qu': 'quantifier',
    'radj1': 'other',
    'redup': 'other',
    'redup-v': 'other',
    'ref.pron': 'other',
    'res': 'other',
    's.pron': 'pronoun',
    'tam': 'function word',
    'towo': 'other',
    'trans': 'transitive verb',
    'v': 'verb',
    'v,tr': 'transitive verb',
    'v.': 'verb',
    'v.imp': 'verb',
    'v.itr': 'verb',
    'v.itr.': 'verb',
    'v.pre': 'verb',
    'v.suf': 'verb',
    'v.tr': 'verb',
    'v.tr.b': 'verb',
    'w': 'other',
    '()': 'other',
}


class Meaning(object):
    def __init__(self):
        self.de = None
        self.ge = None
        self.sd = []
        self.examples = []


class TeopWord(object):
    def __init__(self, form):
        self.form = form
        for marker in 'hm ph ps lx'.split():
            setattr(self, marker, None)
        self.data = OrderedDict()
        self.rel = []
        self.meanings = []

    @property
    def id(self):
        return self.form + (self.hm or '')


class TeopEntry(Entry):
    """
    Implements specifics of the teop toolbox format.

    test:
    \lx ...
    """
    def checked_word(self, word, meaning):
        if meaning:
            if meaning.de or meaning.ge:
                word.meanings.append(meaning)
            else:
                print('meaning without description for %s' % word.form)
        return word

    def get_words(self):
        word = None
        pos = None
        xv = None
        meaning = None
        alt_sn = False

        for k, v in self:
            if k == 'lx' or k == 'se':
                if word:
                    yield self.checked_word(word, meaning)
                word = TeopWord(v)
                if pos:
                    word.ps = pos
                meaning = Meaning()

            if k == 'sn' and v:
                if alt_sn:
                    self.checked_word(word, meaning)
                    meaning = Meaning()
                alt_sn = True

            if not word:
                continue

            if k in ['de', 'ge']:
                setattr(meaning, k, v)

            if k == 'sd':
                meaning.sd.append(v)

            for key in ['hm', 'ph']:
                if k == key and v:
                    setattr(word, k, v)
            for key in 'sc mr re'.split():
                if k == key and v:
                    word.data[k] = v
            if k == 'ps':
                pos = word.ps = v
            if k == 'cf':
                for vv in v.split(','):
                    if vv.strip():
                        word.rel.append((k, vv.strip()))
            if k == 'xv':
                xv = v
            if k == 'xe' and xv:
                try:
                    assert meaning
                    meaning.examples.append((xv, v))
                    xv = None
                except AssertionError:
                    print('no meanings for (sense or subentry of) word %s' % word.form)
        if word:
            yield self.checked_word(word, meaning)


def load(id_, data, files_dir, datadir, comparison_meanings, **kw):
    d = Dictionary(
        datadir.joinpath('Teop.txt'),
        entry_impl=TeopEntry,
        encoding=kw.get('encoding', 'utf8'),
        entry_sep='\\lx ')
    d.entries = filter(lambda r: r.get('lx'), d.entries)

    #d.stats()
    #return

    lang = data['Language'][id_]
    vocab = data['Dictionary'][id_]

    rel = []

    for i, entry in enumerate(d.entries):
        words = list(entry.get_words())
        headword = None

        for j, word in enumerate(words):
            if not word.meanings:
                print('no meanings for word %s' % word.form)
                continue

            if not headword:
                headword = word.id
            else:
                rel.append((word.id, 'sub', headword))

            for tw in word.rel:
                rel.append((word.id, tw[0], tw[1]))

            w = data.add(
                models.Word,
                word.id,
                id='%s-%s-%s' % (id_, i + 1, j + 1),
                name=word.form,
                number=int(word.hm) if word.hm else 0,
                phonetic=word.ph,
                pos=word.ps,
                #description=word.de or word.ge,
                dictionary=vocab,
                language=lang)

            for k, meaning in enumerate(word.meanings):
                if not (meaning.ge or meaning.de):
                    print('meaning without description for word %s' % w.name)
                    continue

                m = models.Meaning(
                    id='%s-%s' % (w.id, k + 1),
                    name=meaning.de or meaning.ge,
                    description=meaning.de,
                    gloss=meaning.ge,
                    word=w,
                    semantic_domain=meaning.sd)

                for l, (ex, trans) in enumerate(meaning.examples):
                    # FIXME: we should collect examples across a dictionary and identify!
                    s = common.Sentence(
                        id='%s-%s-%s' % (w.id, k + 1, l + 1),
                        name=ex,
                        language=lang,
                        description=trans)
                    models.MeaningSentence(meaning=m, sentence=s)

                key = (meaning.ge or meaning.de).replace('.', ' ').lower()
                if key in comparison_meanings:
                    meaning = comparison_meanings[key]
                    vsid = '%s-%s' % (key, id_),
                    if vsid in data['ValueSet']:
                        vs = data['ValueSet'][vsid]
                    else:
                        vs = data.add(
                            common.ValueSet, vsid,
                            id='%s-%s' % (id_, m.id),
                            language=lang,
                            contribution=vocab,
                            parameter=meaning)

                    DBSession.add(models.Counterpart(
                        id='%s-%s' % (w.id, k + 1),
                        name=w.name,
                        valueset=vs,
                        word=w))

            DBSession.flush()

            for index, (key, value) in enumerate(word.data.items()):
                if key in MARKER_MAP:
                    label, converter = MARKER_MAP[key]
                    DBSession.add(common.Unit_data(
                        object_pk=w.pk,
                        key=label,
                        value=converter(word.data),
                        ord=index))

    # FIXME: vgroup words by description and add synonym relationships!

    for s, d, t in rel:
        if s in data['Word'] and t in data['Word']:
            DBSession.add(models.SeeAlso(
                source_pk=data['Word'][s].pk,
                target_pk=data['Word'][t].pk,
                description=d))
        else:
            if s not in data['Word']:
                #pass
                print '---m---', s
            else:
                #pass
                print '---m---', t


if __name__ == '__main__':
    e = TeopEntry.from_string(r"""
\lx ap
\ps n
\sd fauna
\sd fish
\dn blak krab
\de shore crab
\ge shore.crab
\dr
\dt 29/Mar/2010
""")
    words = list(e.get_words())
    assert len(words) == 1
    word = words[0]
    assert word.ps == 'n'
    assert word.meanings
    assert word.meanings[0].de and word.meanings[0].ge
    assert len(word.meanings[0].sd) == 2

    e = TeopEntry.from_string(r"""
\lx a
\ps conj
\sn 1
\dn be
\ge but
\dr
\sn 2
\dn mo
\de and
\ge and
\dt 13/Nov/2009
""")
    words = list(e.get_words())
    assert len(words) == 1
    word = words[0]
    assert len(word.meanings) == 2
    assert word.meanings[0].ge == 'but' and word.meanings[1].ge == 'and'

    e = TeopEntry.from_string(r"""
\lx aa
\ps n
\sd plants
\dn nanggalat
\de nettle
\ge nettle
\dr
\sc

\se aa ne tes
\dn nanggalat blong solwota
\de jellyfish (lit. "nettle of the sea")
\dr

\se laa
\dn stampa blong nanggalat
\de nettle tree
\dr

\dt 29/Mar/2010
""")
    words = list(e.get_words())
    assert len(words) == 3
    assert words[1].ps == words[0].ps

    e = TeopEntry.from_string(r"""
\lx bweang
\ps n
\sn 1
\sd plants
\dn hea blong wan plan
\de hairy parts of a plant
\ge treefern.hair
\dr
\xv bweang ane leevy'o
\xn hea blong blak palm
\xe fiber of the tree fern
\xr

\sn 2
\sd kastom
\dn fes rang, rang blong kapenta
\de the first rank, the rank of the carpenter
\ge carpenter.rank
\dr

\dt 14/Jul/2010""")
    words = list(e.get_words())
    assert len(words) == 1
    word = words[0]
    m1, m2 = word.meanings
    assert m1.examples and m1.sd == ['plants']
    assert not m2.examples
    assert m2.sd == ['kastom']

    e = TeopEntry.from_string(r"""
\lx bwee
\ps n.rel
\pd 2
\dn olgeta samting we yu save fulum ap samting insaed, olsem plet, sospen, baket
\de container, vessel
\ge container
\dr

\xv bwee matyis
\xn bokis blong majis
\xe match box
\xr

\xv bwee tin
\xn tin
\xe a can containing fish or meat
\xr

\se bwee vini 'o
\dn skin blong kokonas
\de the fibrous husk of a coconut
\dr

\se bwee ne s'o'os'o'oan
\dn sospen, marmit
\de pot
\dr
\nt suggestion by Domatien

\se bwee ne enan
\dn pelet
\de plate
\dr

\se bwee bek
\dn grin snel
\de green snail
\dr

\dt 08/Sep/2011""")
    words = list(e.get_words())
    assert len(words) == 5
