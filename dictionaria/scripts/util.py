# coding: utf8
from __future__ import unicode_literals
import re

from path import path
from clld.util import jsonload
from clld.scripts.util import Data
from clld.db.models import common
from clld.db.meta import DBSession

from dictionaria import models
from dictionaria.lib.dictionaria_sfm import Dictionary


datadir = path('/home/robert/venvs/dictionaria/dictionaria-intern/submissions')


class Submission(object):
    def __init__(self, id_):
        if isinstance(id_, path):
            self.dir = id_
            self.id = id_.namebase
        else:
            self.id = id_
            self.dir = datadir.joinpath(id_)
        sfm = self.dir.files('*.txt')
        md = self.dir.files('*.json')
        self.active = True if md else False
        self.type = 'sfm' if sfm else None
        self.db = None

        if self.active:
            assert len(md) == 1
            self.md = jsonload(md[0])

        if self.type == 'sfm':
            assert len(sfm) == 1
            self.db = sfm[0]

    @property
    def dict(self):
        if self.db:
            if self.type == 'sfm':
                return Dictionary(
                    self.db,
                    marker_map=self.md.get('marker_map', {}),
                    encoding=self.md.get('encoding', 'utf8'))


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

                m = models.Meaning(
                    id='%s-%s' % (w.id, k + 1),
                    name=meaning.de or meaning.ge,
                    description=meaning.de,
                    gloss=meaning.ge,
                    word=w,
                    semantic_domain=', '.join(meaning.sd))

                for l, ex in enumerate(meaning.x):
                    s = data['Sentence'].get((ex.xv, ex.xe))
                    if not s:
                        s = data.add(
                            common.Sentence,
                            (ex.xv, ex.xe),
                            id='%s-%s-%s' % (w.id, k + 1, l + 1),
                            name=ex.xv,
                            language=lang,
                            analyzed=igt(ex.xvm),
                            gloss=igt(ex.xeg),
                            description=ex.xe)
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
