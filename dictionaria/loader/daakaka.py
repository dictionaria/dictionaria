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
    ue=('usage', lambda d: d['ue']),
    sd=('semantic domain', lambda d: d['sd']),
    et=('et', lambda d: d['et']),
    es=('es', lambda d: d['es']),
    ee=('ee', lambda d: d['ee']),
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


class DaakakaWord(object):
    def __init__(self, form):
        self.form = form
        for marker in 'hm ph ps'.split():
            setattr(self, marker, None)
        self.data = OrderedDict()
        self.rel = []
        self.examples = []
        self.de = None
        self.ge = None

    @property
    def id(self):
        return self.form + (self.hm or '')


class DaakakaEntry(Entry):
    """
    Implements specifics of the daakaka toolbox format.
    """
    def get_words(self):
        word = None
        form = None
        pos = None
        xv = None
        for k, v in self:
            if k == 'lx' or k == 'se':
                if word:
                    yield word
                word = DaakakaWord(v)
                if pos:
                    word.ps = pos
                form = v
            if k == 'sn' and v:
                if word:
                    yield word
                word = DaakakaWord(form)
            if not word:
                continue
            for key in ['hm', 'ph', 'de', 'ge']:
                if k == key and v:
                    setattr(word, k, v)
            for key in 'ue et es ee sd'.split():
                if k == key and v:
                    word.data[k] = v
            if k == 'ps':
                pos = word.ps = v
            if k == 'cf':
                word.rel.append((k, v))
            if k == 'xv':
                xv = v
            if k == 'xe' and xv:
                word.examples.append((xv, v))
                xv = None
        if word:
            yield word


def load(id_, data, files_dir, datadir):
    d = Dictionary(
        datadir.joinpath('KvP_Daakaka.txt'),
        entry_impl=DaakakaEntry,
        entry_sep='\\lx ')
    d.entries = filter(lambda r: r.get('lx'), d.entries)

    #d.stats()
    #return

    lang = data['Language'][id_]
    vocab = data['Dictionary'][id_]

    rel = []

    for i, entry in enumerate(d.entries):
        words = list(entry.get_words())

        # FIXME: each word for an entry must be related to all others!

        for j, word in enumerate(words):
            #if j == 0:
            #    headword = word.form
            #else:
            #    rel.append((word.id, 'sub', headword))

            for tw in word.rel:
                rel.append((word.id, tw[0], tw[1]))

            if not word.de and not word.ge:
                print('no gloss for word %s' % word.form)
                continue

            w = data.add(
                models.Word,
                word.id,
                id='%s-%s-%s' % (id_, i + 1, j + 1),
                name=word.form,
                number=int(word.hm) if word.hm else 0,
                phonetic=word.ph,
                description=word.de or word.ge,
                dictionary=vocab,
                language=lang)

            DBSession.flush()

            for index, (key, value) in enumerate(word.data.items()):
                if key in MARKER_MAP:
                    label, converter = MARKER_MAP[key]
                    DBSession.add(common.Unit_data(
                        object_pk=w.pk,
                        key=label,
                        value=converter(word.data),
                        ord=index))

            for k, (ex, trans) in enumerate(word.examples):
                s = common.Sentence(
                    id='%s-%s-%s-%s' % (id_, i + 1, j + 1, k + 1),
                    name=ex,
                    language=lang,
                    description=trans)
                DBSession.add(s)
                DBSession.add(models.WordSentence(word=w, sentence=s))

            meaning_prefix = ''
            pos = POS_MAP.get(word.ps, 'other')
            if pos == 'verb' or (pos and ' verb' in pos):
                meaning_prefix = 'to '
            elif pos == 'noun':
                meaning_prefix = 'the '

            if pos:
                DBSession.add(common.UnitValue(
                    id='pos-%s-%s-%s' % (id_, i + 1, j + 1),
                    name=word.ps,
                    unit=w,
                    unitparameter=data['UnitParameter']['pos'],
                    unitdomainelement=data['UnitDomainElement'][pos],
                    contribution=vocab,
                ))

            key = (word.ge or word.de).replace('.', ' ')
            if not key.startswith(meaning_prefix):
                key = '%s%s' % (meaning_prefix, key)
            if key in data['Meaning']:
                meaning = data['Meaning'][key]
                vsid = '%s-%s' % (key, id_),
                if vsid in data['ValueSet']:
                    vs = data['ValueSet'][vsid]
                else:
                    vs = data.add(
                        common.ValueSet, vsid,
                        id='%s-%s' % (id_, meaning.id),
                        language=lang,
                        contribution=vocab,
                        parameter=meaning)

                DBSession.add(models.Counterpart(
                    id='%s-%s-%s' % (id_, i + 1, j + 1),
                    name=w.name,
                    valueset=vs,
                    word=w))

    for s, d, t in rel:
        if s in data['Word'] and t in data['Word']:
            DBSession.add(models.SeeAlso(
                source_pk=data['Word'][s].pk,
                target_pk=data['Word'][t].pk,
                description=d))
        else:
            if s not in data['Word']:
                print '---m---', s
            else:
                print '---m---', t
