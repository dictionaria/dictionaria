# coding: utf8
from __future__ import unicode_literals

from clld.scripts.util import Data
from clld.db.models import common
from clld.db.meta import DBSession

from dictionaria import models
from dictionaria.lib.dictionaria_sfm import Dictionary


def default_value_converter(value, _):
    return value


def load_sfm(id_,
             vocab,
             lang,
             filename,
             comparison_meanings,
             comparison_meanings_alt_labels,
             marker_map,
             **md):
    d = Dictionary(filename, encoding=md.get('encoding', 'utf8'))
    data = Data()
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
                dictionary=vocab,
                language=lang)

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

                for l, (ex, trans) in enumerate(meaning.x):
                    s = data['Sentence'].get((ex, trans))
                    if not s:
                        s = data.add(
                            common.Sentence,
                            (ex, trans),
                            id='%s-%s-%s' % (w.id, k + 1, l + 1),
                            name=ex,
                            language=lang,
                            description=trans)
                    models.MeaningSentence(meaning=m, sentence=s)

                key = (meaning.ge or meaning.de).replace('.', ' ').lower()
                concept = None
                if key in comparison_meanings:
                    concept = comparison_meanings[key]
                elif key in comparison_meanings_alt_labels:
                    concept = comparison_meanings_alt_labels[key]

                if concept and concept not in concepts:
                    concepts.append(concept)
                    vsid = '%s-%s' % (key, id_),
                    if vsid in data['ValueSet']:
                        vs = data['ValueSet'][vsid]
                    else:
                        vs = data.add(
                            common.ValueSet, vsid,
                            id='%s-%s' % (id_, m.id),
                            language=lang,
                            contribution=vocab,
                            parameter=concept)

                    DBSession.add(models.Counterpart(
                        id='%s-%s' % (w.id, k + 1),
                        name=w.name,
                        valueset=vs,
                        word=w))

            DBSession.flush()

            for index, (key, values) in enumerate(word.data.items()):
                if key in marker_map:
                    label, converter = marker_map[key]
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
