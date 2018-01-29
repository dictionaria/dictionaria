# coding: utf8
from __future__ import unicode_literals, print_function, division
from collections import defaultdict
import re
from itertools import chain

from pycldf import Dictionary as CldfDictionary
from clldutils.misc import lazyproperty, nfilter
from clld.db.models import common
from clld.db.fts import tsvector
from clld.db.meta import DBSession

from dictionaria.lib.ingest import MeaningDescription, split, BaseDictionary
from dictionaria import models

ASSOC_PATTERN = re.compile('rel_(?P<rel>[a-z]+)')


class Dictionary(BaseDictionary):
    @lazyproperty
    def cldf(self):
        return CldfDictionary.from_metadata(self.dir.parent / 'cldf-md.json')

    def load(self,
             submission,
             data,
             vocab,
             lang,
             comparison_meanings,
             labels):
        def id_(oid):
            return '%s-%s' % (submission.id, oid)

        metalanguages = submission.props.get('metalanguages', {})
        colmap = {k: self.cldf['EntryTable', k].name
                  for k in ['id', 'headword', 'partOfSpeech']}
        for lemma in self.cldf['EntryTable']:
            oid = lemma.pop(colmap['id'])
            word = data.add(
                models.Word,
                oid,
                id=id_(oid),
                name=lemma.pop(colmap['headword']),
                pos=lemma.pop(colmap['partOfSpeech']),
                dictionary=vocab,
                language=lang)
            DBSession.flush()
            for attr, type_ in [('picture', 'image'), ('sound', 'audio')]:
                fnames = lemma.pop(attr, None)
                if fnames is None:
                    fnames = lemma.pop(type_, None)
                if fnames:
                    fnames = [fnames] if not isinstance(fnames, list) else fnames
                    for fname in fnames:
                        submission.add_file(type_, fname, common.Unit_files, word)

            for index, (key, value) in enumerate(lemma.items()):
                if value:
                    DBSession.add(common.Unit_data(
                        object_pk=word.pk,
                        key=labels.get(key, key),
                        value=value,
                        ord=index))

        DBSession.flush()

        fullentries = defaultdict(list)
        for lemma in self.cldf['EntryTable']:
            fullentries[lemma[colmap['id']]].extend(list(lemma.items()))
            word = data['Word'][lemma[colmap['id']]]
            for key in lemma:
                assoc = ASSOC_PATTERN.match(key)
                if assoc:
                    for lid in split(lemma.get(key, '')):
                        # Note: we correct invalid references, e.g. "lx 13" and "Lx13".
                        lid = lid.replace(' ', '').lower()
                        DBSession.add(models.SeeAlso(
                            source_pk=word.pk,
                            target_pk=data['Word'][lid].pk,
                            description=assoc.group('rel')))

        sense2word = {}
        colmap = {k: self.cldf['SenseTable', k].name
                  for k in ['id', 'entryReference', 'description']}
        for sense in self.cldf['SenseTable']:
            fullentries[sense[colmap['entryReference']]].extend(list(sense.items()))
            sense2word[sense[colmap['id']]] = sense[colmap['entryReference']]
            w = data['Word'][sense[colmap['entryReference']]]
            kw = dict(
                id=id_(sense[colmap['id']]),
                name='; '.join(nfilter(sense[colmap['description']])),
                word=w)
            if 'alt_translation1' in sense and metalanguages.get('gxx'):
                kw['alt_translation1'] = sense['alt_translation1']
                kw['alt_translation_language1'] = metalanguages.get('gxx')
            m = data.add(models.Meaning, sense[colmap['id']], **kw)

            for i, md in enumerate(nfilter(sense[colmap['description']])):
                key = md.lower()
                if key in comparison_meanings:
                    concept = comparison_meanings[key]
                else:
                    continue

                vsid = '%s-%s' % (m.id, i)
                vs = data['ValueSet'].get(vsid)
                if not vs:
                    vs = data.add(
                        common.ValueSet, vsid,
                        id=vsid,
                        language=lang,
                        contribution=vocab,
                        parameter_pk=concept)

                DBSession.add(models.Counterpart(
                    id=vsid, name=w.name, valueset=vs, word=w))

            DBSession.flush()
            for attr, type_ in [('picture', 'image'), ('sound', 'audio')]:
                fnames = sense.pop(attr, None)
                if fnames is None:
                    fnames = sense.pop(type_, None)
                if fnames:
                    fnames = [fnames] if not isinstance(fnames, list) else fnames
                    fnames = nfilter(chain(*[f.split(';') for f in fnames]))
                    for fname in set(fnames):
                        submission.add_file(type_, fname, models.Meaning_files, m)

        colmap = {k: self.cldf['ExampleTable', k].name
                  for k in ['id', 'primaryText', 'translatedText']}
        for ex in self.cldf['ExampleTable']:
            for mid in ex['Senses']:
                if mid in sense2word:
                    fullentries[sense2word[mid]].extend(list(ex.items()))
                    models.MeaningSentence(
                        meaning=data['Meaning'][mid],
                        sentence=data['Example'][ex[colmap['id']]])
                else:
                    print('missing sense: {0}'.format(mid))

        for wid, d in fullentries.items():
            data['Word'][wid].fts = tsvector(
                '; '.join('{0}: {1}'.format(k, v) for k, v in d if v))
