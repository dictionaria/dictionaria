"""
>>> d.markers
[
u'lg',
u'exylat',
u'ge',
u'bzns',
u'lex',
u'gn',
u'sem',
u'src',
u'crossref',
u'ps',
u'ety',
u'pc',
u'intstr',
u'gram',
u'exyeng',
u'bzn',
u'eth',
u'ct']

>>> for k, v in sorted(list(d.values('ps').items()), key=lambda i: -i[1]):
...   print k, v
...
n 975
vt 564
adv 297
vi 211
adj 140
vlab 79
pro 51
vtrimp 25
ptcl 25
interj 21
postp 12
gm 9
num 8
conn 6
onom 5
quant 1
"""
import re
from collections import defaultdict

from path import path
from clld.db.models import common
from clld.db.meta import DBSession

from dictionaria.lib.sfm import Dictionary, Entry
from dictionaria import models

POS_MAP = {
    'n': 'noun',
    'vt': 'transitive verb',
    'adv': 'adverb',
    'vi': 'intransitive verb',
    'adj': 'adjective',
    'vlab': 'verb',
    'pro': 'pronoun',
    'num': 'numeral',
    'vtrimp': 'verb',
    'ptcl': 'particle',
    'interj': 'particle',
    'postp': 'adposition',
    'gm': 'other',
    'conn': 'other',
    'onom': 'other',
    'quant': 'quantifier',
}


MARKER_MAP = {
    'lexdev': 'devanagri',
    'intstr': 'internal structure',
    'gn': 'Nepali gloss',
    'eth': 'ethnographic notes',
    'bzn': 'botanical or zoological name',
    'sem': 'semantic categories',
}


class YakkhaEntry(Entry):
    def get_meanings(self):
        for m in self.get('ge', '').split(';'):
            m = m.strip().replace('.', ' ').replace('_', ' ')
            if m:
                yield m

    def get_example(self):
        if self.get('exylat'):
            return self.get('exylat'), self.get('exyeng'), self.get('exydev')


def load(id_, data, files_dir):
    d = Dictionary(
        path(__file__).dirname().joinpath('Yakkha_WB2013_for-archive.db'),
        validate=False,
        entry_impl=YakkhaEntry,
        entry_sep='\\lex ')
    d.entries = filter(lambda r: r.get('lex'), d.entries)
    lang = data['Language'][id_]
    vocab = data['Dictionary'][id_]

    sep = re.compile('\.|,|;')
    cats = defaultdict(lambda: 0)
    #homonyms = defaultdict(list)
    for entry in d.entries:
        sem = entry.get('sem')
        if sem:
            if not sem.startswith('e.g.') and sep.search(sem):
                cat, note = [s.strip() for s in sep.split(sem, 1)]
            else:
                cat = sem.strip()
            cats[cat] += 1
    #just_one = 0
    #for cat, count in sorted(list(cats.items()), key=lambda i: i[1], reverse=True):
    #    if count > 1:
    #        print cat, count
    #    else:
    #        just_one += 1
    #print just_one, 'semantic categories(?) with just one entry'
        #homonyms[entry.get('lex')].append((entry.get('ps'), entry.get('ge')))
    #for lex, ps in homonyms.items():
    #    if len(ps) > 1:
    #        print '%s\t%s' % (lex, ','.join(p for p, g in ps))

    rel = []

    for i, row in enumerate(d.entries):
        if not row.get('ge'):
            print row.get('lex')
            continue
        w = data.add(
            models.Word, row.get('lex'),
            id='%s-%s' % (id_, i),
            name=row.get('lex'),
            description=row.get('ge'),
            dictionary=vocab)
        w.language = lang

        if row.get('crossref'):
            rel.append((row.get('lex'), row.get('crossref')))

        DBSession.flush()

        for index, pair in enumerate(row):
            key, value = pair
            if key in MARKER_MAP:
                DBSession.add(common.Unit_data(
                    object_pk=w.pk,
                    key=MARKER_MAP[key],
                    value=value,
                    ord=index))

        ex = row.get_example()
        if ex:
            s = common.Sentence(
                id='%s-%s' % (id_, i + 1),
                name=ex[0],
                language=lang,
                original_script=ex[2],
                description=ex[1])
            DBSession.add(s)
            DBSession.add(models.WordSentence(word=w, sentence=s))

        meaning_prefix = ''
        for j, name in enumerate(row.getall('ps')):
            name = POS_MAP[name]
            if name == 'verb' or ' verb' in name:
                meaning_prefix = 'to '
            elif name == 'noun':
                meaning_prefix = 'the '
            if j > 0:
                # only one part-of-speech value per entry!
                raise ValueError
            DBSession.add(common.UnitValue(
                id='pos-%s-%s' % (id_, i + 1),
                unit=w,
                unitparameter=data['UnitParameter']['pos'],
                unitdomainelement=data['UnitDomainElement'][name],
                contribution=vocab,
            ))

        for j, name in enumerate(row.get_meanings()):
            name = name.strip()
            key = '%s%s' % (meaning_prefix, name.lower())
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
                    id='%s-%s-%s' % (id_, i, j),
                    name=row.get('lx'),
                    valueset=vs,
                    word=w))

    for s, t in rel:
        if s in data['Word'] and t in data['Word']:
            DBSession.add(models.SeeAlso(
                source_pk=data['Word'][s].pk,
                target_pk=data['Word'][t].pk))
