# coding: utf8
from __future__ import unicode_literals
import re

from clldutils.path import Path
from clldutils.jsonlib import load
from clld.scripts.util import Data
from clld.db.models import common
from clld.db.meta import DBSession

from dictionaria import models
from dictionaria.lib.sfm import Dictionary, Examples, ElanExamples


datadir = Path('/home/robert/venvs/dictionaria/dictionaria-intern/submissions')


class Corpus(object):
    #
    # FIXME: refactor using clldutils.sfm.SFM:
    # sfm = SFM()
    # for f in d.glob(...)
    #     sfm.read(f)
    #
    def __init__(self, d):
        self.files = [ElanExamples(f) for f in d.glob('*.eaf.tb')]

    def get(self, item):
        for f in self.files:
            res = f.get(item)
            if res:
                return res

    def keys(self):
        res = []
        for f in self.files:
            res.extend(list(f._map.keys()))
        return sorted(res)


class Submission(object):
    def __init__(self, id_):
        if isinstance(id_, Path):
            self.dir = id_
            self.id = id_.name
        else:
            self.id = id_
            self.dir = datadir.joinpath(id_)

        md = list(self.dir.glob('*.json'))
        self.active = True if md else False
        self.db = None
        self.raw = None

        if self.active:
            self.db = self.dir.joinpath('processed', 'db.txt')

            if self.db.exists():
                self.type = 'sfm'
                self.raw = list(self.dir.glob('*.txt'))[0]
            else:
                self.db = None

            assert len(md) == 1
            self.md = load(md[0])

    @property
    def dict(self):
        if self.db:
            if self.type == 'sfm':
                # make sure to ignore custom encoding of the original file, because the
                # pre-processed file is already UTF-8.
                return Dictionary(
                    self.db,
                    marker_map=self.md.get('marker_map', {}))


def default_value_converter(value, _):
    return value


def igt(s):
    if s:
        return re.sub('\s+', '\t', s)


def load_sfm(did,
             lid,
             submission,
             comparison_meanings,
             comparison_meanings_alt_labels,
             marker_map):
    data = Data()
    rel = []

    vocab = models.Dictionary.get(did)
    lang = models.Variety.get(lid)
    examples = Examples(submission.dir.joinpath('processed', 'examples.txt'))
    seen = {}
    for ex in examples:
        ex = Examples.as_example(ex)
        assert ex.id not in seen
        data.add(
            common.Sentence,
            ex.id,
            id=ex.id,
            name=ex.xv,
            language=lang,
            analyzed=igt(ex.xvm),
            gloss=igt(ex.xeg),
            description=ex.xe)
        seen[ex.id] = True

    for i, entry in enumerate(submission.dict):
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
                id='%s-%s-%s' % (submission.id, i + 1, j + 1),
                name=word.form,
                number=int(word.hm) if word.hm else 0,
                phonetic=word.ph,
                pos=word.ps,
                dictionary=vocab,
                language=lang)
            DBSession.flush()

            concepts = []

            for k, meaning in enumerate(word.meanings):
                if not (meaning.ge or meaning.de):
                    print('meaning without description for word %s' % w.name)
                    continue

                if meaning.ge:
                    meaning.ge = meaning.ge.replace('.', ' ')

                m = models.Meaning(
                    id='%s-%s' % (w.id, k + 1),
                    name=meaning.de or meaning.ge,
                    description=meaning.de,
                    gloss=meaning.ge,
                    word=w,
                    semantic_domain=', '.join(meaning.sd))

                assert not meaning.x
                for xref in meaning.xref:
                    s = data['Sentence'].get(xref)
                    assert s
                    models.MeaningSentence(meaning=m, sentence=s)

                key = (meaning.ge or meaning.de).replace('.', ' ').lower()
                concept = None
                if key in comparison_meanings:
                    concept = comparison_meanings[key]
                elif key in comparison_meanings_alt_labels:
                    concept = comparison_meanings_alt_labels[key]

                if concept and concept not in concepts:
                    concepts.append(concept)
                    vsid = '%s-%s' % (key, submission.id),
                    if vsid in data['ValueSet']:
                        vs = data['ValueSet'][vsid]
                    else:
                        vs = data.add(
                            common.ValueSet, vsid,
                            id='%s-%s' % (submission.id, m.id),
                            language=lang,
                            contribution=vocab,
                            parameter_pk=concept)

                    DBSession.add(models.Counterpart(
                        id='%s-%s' % (w.id, k + 1),
                        name=w.name,
                        valueset=vs,
                        word=w))

            for _lang, meanings in word.non_english_meanings.items():
                assert _lang in submission.md['metalanguages']
                for meaning in meanings:
                    k += 1
                    models.Meaning(
                        id='%s-%s' % (w.id, k + 1),
                        name=meaning,
                        gloss=meaning,
                        language=submission.md['metalanguages'][_lang],
                        word=w)

            for index, (key, values) in enumerate(word.data.items()):
                if key in marker_map:
                    label = marker_map[key]
                    converter = default_value_converter
                    if isinstance(label, (list, tuple)):
                        label, converter = label
                    for value in values:
                        DBSession.add(common.Unit_data(
                            object_pk=w.pk,
                            key=label,
                            value=converter(value, word.data),
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
