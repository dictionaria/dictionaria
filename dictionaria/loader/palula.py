# coding: utf8
"""
 lx             Palula lexeme (lexical representation) = main entry
 +-  hm         Homonym number
 +-  va         Variant form, usually (but not exclusively) a phonological variant form
 |   |          used within the target dialect or in the other main dialect
 |   +-  ve     The domain of the form in  va, usually the name of the geographical
 |              location, e.g. Biori
 +-  se         Used liberally for multi-word constructions in which the lexeme occurs
     +-  ph     Phonetic form (surface representation)
     +-  gv     Vernacular form
     +-  mn     Reference to a main entry, especially in cases where a variant form or an
     |          irregular form needs a separate listing
     +-  mr     Morphemic form (underlying representation, if different from lexical)
     +-  xv     Example phrase or sentence
     |   +-  xe Translation of above  xv
     |   +-  xvm Morphemes of IGT
     |   +-  xeg Gloss of IGT
     +-  bw     Indicating that it is a borrowed word, but by using the label Comp I
     |          don’t make any specific claims as to the route of borrowing, instead just
     |          mentioning the language that has a similar form and citing the source form
     |          itself
     +-  ps     Part of speech label
         +-  pd Paradigm label (e.g. i-decl)
         |   +-  pdl    Specifying the form category of the following pdv
         |       +-  pdv    The word form
         +-  sn Sense number (for a lexeme having clearly different senses). I use this
             |  very sparingly, trying to avoid too much of an English or Western bias
             +-  re Word(s) used in English (reversed) index.
             +-  de Gloss(es) or multi-word definition
             +-  oe Restrictions, mainly grammatical (e.g. With plural reference)
             +-  ue Usage (semantic or grammatical)
             +-  cf Cross-reference, linking it to another main entry
             +-  et Old Indo-Aryan proto-form (I’m restricting this to Turner 1966)
                 +-  eg The published gloss of  et
                 +-  es The reference to Turner, always in the form T: (referring to the
                        entry number in Turner, not the page number)

n.masc 369
n.fem 292
v.tr 123
adj 82
adj.inv 81
v.intr 75
v.tr:cjt.ninc 61
pron:dem 53
sfx 45
quant 45
adv.sp 39
v.intr:cjt.inc 34
post 33
v.tr:cjt.inc 31
n.masc:pn 25
det 25
adv.tm 24
pron:ind 23
host 20
det:dem 17
adv.mann 17
adv.deg 15
conj 13
pron:pers 11
adv.sp:dem 10
v.intr:cjt.ninc 9
n.fem:pn 8
aux 7
disc 6
v.cop 6
interj 5
v.intr:pass 5
mood 5
adv.sent 4
adv.sp:ind 3
det:ind 3
v:cop 3
n 3
adv.tm:ind 2
adj:dem 2
adv.mann:ind 2
adj:ind 2
v.tr:caus 2
adj.inv:dem 2
v:mod 2
hon 2
clause:ind 2
pron:refl 2
adv.deg:ind 1
quant:dem 1
v:cjt 1
pron:recp 1
adv.tm:dem 1
neg 1
adj.inv:ind 1
nf 1
adv:mann 1
adv.deg:dem 1
quant:ind 1
ritual 1
v.tr:cjt:ninc 1
pron:det 1
"""
from __future__ import unicode_literals
import re
from collections import OrderedDict
from path import path
from clld.db.models import common
from clld.db.meta import DBSession

from dictionaria.lib.sfm import Dictionary, Entry
from dictionaria import models

POS_MAP = {
    'n': 'noun',
    'n.masc': 'noun',
    'n.fem': 'noun',
    'adv.': 'adverb',
    'adj': 'adjective',
    'adj.inv': 'adjective',
    'adj.inv:dem': 'adjective',
    'adj.inv:ind': 'adjective',
    'adj:dem': 'adjective',
    'adj:ind': 'adjective',
    'adv.deg': 'adverb',
    'adv.deg:dem': 'adverb',
    'adv.deg:ind': 'adverb',
    'adv.mann': 'adverb',
    'adv.mann:ind': 'adverb',
    'adv.sent': 'adverb',
    'adv.sp': 'adverb',
    'adv.sp:dem': 'adverb',
    'adv.sp:ind': 'adverb',
    'adv.tm': 'adverb',
    'adv.tm:dem': 'adverb',
    'adv.tm:ind': 'adverb',
    'adv:mann': 'adverb',
    'aux': 'auxiliary verb',
    'clause:ind': 'other',
    'conj': 'conjunction',
    'det': 'determiner',
    'det:dem': 'determiner',
    'det:ind': 'determiner',
    'disc': 'other',
    'hon': 'other',
    'host': 'other',
    'interj': 'particle',
    'mood': 'other',
    'n': 'noun',
    'n.fem': 'noun',
    'n.fem:pn': 'noun',
    'n.masc': 'noun',
    'n.masc:pn': 'noun',
    'neg': 'particle',
    'nf': 'other',
    'post': 'adposition',
    'pron:dem': 'pronoun',
    'pron:det': 'pronoun',
    'pron:ind': 'pronoun',
    'pron:pers': 'pronoun',
    'pron:recp': 'pronoun',
    'pron:refl': 'pronoun',
    'quant': 'quantifier',
    'quant:dem': 'quantifier',
    'quant:ind': 'quantifier',
    'ritual': 'other',
    'sfx': 'other',
    'v.cop': 'auxiliary verb',
    'v.intr': 'intransitive verb',
    'v.intr:cjt.inc': 'intransitive verb',
    'v.intr:cjt.ninc': 'intransitive verb',
    'v.intr:pass': 'intransitive verb',
    'v.tr': 'transitive verb',
    'v.tr:caus': 'transitive verb',
    'v.tr:cjt.inc': 'transitive verb',
    'v.tr:cjt.ninc': 'transitive verb',
    'v.tr:cjt:ninc': 'transitive verb',
    'v:cjt': 'verb',
    'v:cop': 'auxiliary verb',
    'v:mod': 'auxiliary verb',
}


def et(d):
    res = d['et']
    if d.get('eg'):
        res += " '%s'" % d['eg']
    if d.get('es'):
        res += " (%s)" % d['es']
    return res


MARKER_MAP = dict(
    va=('variant form', lambda d: d['va'] + (' (%s)' % d['ve'] if d.get('ve') else '')),
    gv=('vernacular form', lambda d: d['gv']),
    mr=('morphemic form', lambda d: d['mr']),
    bw=('borrowed', lambda d: d['bw']),
    oe=('restrictions', lambda d: d['oe']),
    ue=('usage', lambda d: d['ue']),
    et=('old Indo-Aryan proto-form', et),
)


class PalulaWord(object):
    def __init__(self, form):
        self.form = form
        for marker in 'hm ph ps'.split():
            setattr(self, marker, None)
        self.data = OrderedDict()
        self.des = []
        self.rel = []
        self.examples = []

    @property
    def id(self):
        return self.form + (self.hm or '')


class PalulaEntry(Entry):
    """
    Implements specifics of the palula toolbox format.
    """
    def get_words(self):
        """
        Each value for markers lx or se is regarded as a word.
        """
        word = None
        xv, xvm, xeg = None, None, None
        for k, v in self:
            if k == 'lx' or k == 'se':
                if word:
                    yield word
                word = PalulaWord(v)
            if not word:
                continue
            if k == 'de':
                word.des.append(v)
            for key in ['hm', 'ph']:
                if k == key and v:
                    setattr(word, k, v)
            for key in 'gv bw mr va ve oe ue et eg es'.split():
                if k == key and v:
                    word.data[k] = v
            if k == 'ps':
                if word and word.ps and word.ps != v:
                    print '--- split ---'
                    # new part of speech for a word, split this!
                    form = word.form
                    yield word
                    word = PalulaWord(form)
                word.ps = POS_MAP[v]
            if k in ['cf', 'mn']:
                word.rel.append((k, v))
            if k == 'xvm':
                xvm = v
            if k == 'xeg':
                xeg = v
            if k == 'xv':
                xv = v
            if k == 'xe' and xv:
                word.examples.append((xv, v, xvm, xeg))
                xv, xvm, xeg = None, None, None
        if word:
            yield word


def igt(s):
    if s:
        return re.sub('\s+', '\t', s)


def load(id_, data, files_dir, data_dir):
    d = Dictionary(
        data_dir.joinpath('PalulaVocabulary.db'),
        entry_impl=PalulaEntry,
        entry_sep='\\lx ')
    print len(d.entries)
    d.entries = filter(lambda r: r.get('lx'), d.entries)
    print len(d.entries)
    lang = data['Language'][id_]
    vocab = data['Dictionary'][id_]

    rel = []

    for i, entry in enumerate(d.entries):
        for j, word in enumerate(entry.get_words()):
            if j == 0:
                headword = word.form
            else:
                rel.append((word.id, 'sub', headword))

            for tw in word.rel:
                rel.append((word.id, tw[0], tw[1]))

            w = data.add(
                models.Word, word.id,
                id='%s-%s-%s' % (id_, i + 1, j + 1),
                name=word.form,
                number=int(word.hm) if word.hm else 0,
                phonetic=word.ph,
                description='; '.join(word.des),
                dictionary=vocab,
                language=lang)

            DBSession.flush()

            for index, pair in enumerate(word.data.items()):
                key, value = pair
                if key in MARKER_MAP:
                    label, converter = MARKER_MAP[key]
                    DBSession.add(common.Unit_data(
                        object_pk=w.pk,
                        key=label,
                        value=converter(word.data),
                        ord=index))

            for k, ex in enumerate(word.examples):
                s = common.Sentence(
                    id='%s-%s-%s-%s' % (id_, i + 1, j + 1, k + 1),
                    name=ex[0],
                    language=lang,
                    analyzed=igt(ex[2]),
                    gloss=igt(ex[3]),
                    description=ex[1])
                DBSession.add(s)
                DBSession.add(models.WordSentence(word=w, sentence=s))

            meaning_prefix = ''
            if word.ps == 'verb' or (word.ps and ' verb' in word.ps):
                meaning_prefix = 'to '
            elif word.ps == 'noun':
                meaning_prefix = 'the '

            if word.ps:
                DBSession.add(common.UnitValue(
                    id='pos-%s-%s-%s' % (id_, i + 1, j + 1),
                    unit=w,
                    unitparameter=data['UnitParameter']['pos'],
                    unitdomainelement=data['UnitDomainElement'][word.ps],
                    contribution=vocab,
                ))

            for k, de in enumerate(word.des):
                for l, name in enumerate(de.split(',')):
                    name = name.strip()
                    key = name.lower()
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
                            id='%s-%s-%s-%s-%s' % (id_, i + 1, j + 1, k + 1, l + 1),
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
