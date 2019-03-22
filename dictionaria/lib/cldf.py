# coding: utf8
from __future__ import unicode_literals, print_function, division
from collections import defaultdict, OrderedDict
import re
from itertools import chain

from csvw import dsv
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
        return CldfDictionary.from_metadata(self.dir / 'cldf-md.json')

    def load(self,
             submission,
             data,
             vocab,
             lang,
             comparison_meanings,
             labels):
        def id_(oid):
            return '%s-%s' % (submission.id, oid)

        print('######\n a CLDF dict! \n####')

        media = self.dir.parent / 'media.csv'
        if media.exists():
            media = {d['ID']: d for d in dsv.reader(media, dicts=True)}
        else:
            media = {}

        metalanguages = submission.props.get('metalanguages', {})
        colmap = {k: self.cldf['EntryTable', k].name
                  for k in ['id', 'headword', 'partOfSpeech']}
        if 'EntryTable' in labels:
            elabels = OrderedDict(labels['EntryTable'])
        else:
            elabels = OrderedDict()
            for key, label in labels.items():
                if key in submission.md['properties']['entry_map']:
                    elabels[submission.md['properties']['entry_map'][key]] = label

        for lemma in self.cldf['EntryTable']:
            """
ID,Language_ID,Headword,Part_Of_Speech,
    Contains,
    Possessed_Plural,
    Related_Dialectal_Form,
    Phonetic_Form,
    Homonym,
    Related_Dialectal_Form_BibRef,
    Dialectal_Distribution,
    Agentive_Noun,
    Diffusive_Form,
    Morphological_Segmentation_BibRef,
    Alternative_Form,
    Predictable_Dialectal_Variants,
    Morphological_Segmentation,
    Related_Form,
    Associated_Phrasemes,
    NonPossessed_Form,
    Abstract_Noun,
    Attributive,
    MarkedPossession,
    NonPredictable_Variants,
    Etymology,
    Plural,
    Media_IDs,
    Infinititve
LX000001,tzh,,,,,,,,,,,,,,,,,,,,,,,,,,
LX000002,tzh,a,part.,,,,,1,,,,,,,,,,,,,,,,,,,
LX000003,tzh,a,part.,,,,,3,,,,,,,,,,,,,,,,,,,
LX000004,tzh,a,aux.,,,,,2,,,,,,,,,,,,,,,,,,,
LX000005,tzh,a',n2.,,,,,,,,,,,,,,,,-il,,,,,,,,
LX000006,tzh,a'al,n2.,,,,,,,,,,,,,(h)a' -al,,,,,,,,de [ha'](LX001760),,,
LX000007,tzh,a'lel,n2.,,,,,,,,,,,,,(h)a' -al,,,,,,,,,,,
LX000008,tzh,a'an,agt.i.v.,,,,,1,,,,,,,,a'iy -an,,,,,,,,,,,
LX000009,tzh,a'an,t.v.,,,,,2,,,,,,,,a'iy -an,[a'an](LX000008),,,,,,,,,,
            """

            #
            # FIXME: handle Sources!
            #
            if not lemma[colmap['headword']]:
                continue
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

            for index, (key, label) in enumerate(elabels.items()):
                if lemma[key]:
                    DBSession.add(common.Unit_data(
                        object_pk=word.pk,
                        key=label,
                        value=lemma[key],
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

        #
        # FIXME: start from here!
        #
        sense2word = {}
        colmap = {k: self.cldf['SenseTable', k].name
                  for k in ['id', 'entryReference', 'description']}
        for sense in self.cldf['SenseTable']:
            slabels = labels.get('SenseTable', {})
            fullentries[sense[colmap['entryReference']]].extend(list(sense.items()))
            sense2word[sense[colmap['id']]] = sense[colmap['entryReference']]
            w = data['Word'][sense[colmap['entryReference']]]
            kw = dict(
                id=id_(sense[colmap['id']]),
                name='; '.join(nfilter(sense[colmap['description']])),
                jsondata={slabels[k]: v for k, v in sense.items() if v and k in slabels},
                word=w)
            if 'alt_translation1' in sense and metalanguages.get('gxx'):
                kw['alt_translation1'] = sense['alt_translation1']
                kw['alt_translation_language1'] = metalanguages.get('gxx')
            if 'alt_translation2' in sense and metalanguages.get('gxy'):
                kw['alt_translation2'] = sense['alt_translation2']
                kw['alt_translation_language2'] = metalanguages.get('gxy')
            m = data.add(models.Meaning, sense[colmap['id']], **kw)

            for i, md in enumerate(nfilter(sense[colmap['description']]), start=1):
                key = md.lower()
                if key in comparison_meanings:
                    concept = comparison_meanings[key]
                else:
                    continue

                vsid = '%s-%s' % (lang.id, concept)
                vs = data['ValueSet'].get(vsid)
                if not vs:
                    vs = data.add(
                        common.ValueSet, vsid,
                        id=vsid,
                        language=lang,
                        contribution=vocab,
                        parameter_pk=concept)

                DBSession.add(models.Counterpart(
                    id='{0}-{1}'.format(m.id, i), name=w.name, valueset=vs, word=w))

            DBSession.flush()
            for attr, type_ in [('picture', 'image'), ('sound', 'audio')]:
                fnames = sense.pop(attr, None)
                if fnames is None:
                    fnames = sense.pop(type_, None)
                if fnames:
                    fnames = [fnames] if not isinstance(fnames, list) else fnames
                    fnames = nfilter(chain(*[f.split(';') for f in fnames]))
                    files = [(fname, media[fname]) for fname in set(fnames) if fname in media]
                    for fname, spec in sorted(
                        files,
                        key=lambda i: i[1].get(submission.props.get('media_order', 'Description')) or i[1]['ID']
                    ):
                        submission.add_file(type_, fname, models.Meaning_files, m, spec)

        colmap = {k: self.cldf['ExampleTable', k].name
                  for k in ['id', 'primaryText', 'translatedText']}
        for ex in self.cldf['ExampleTable']:
            for mid in ex.get('Senses') or ex.get('Sense_IDs', []):
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
