# coding: utf8
from __future__ import unicode_literals, print_function, division
from collections import defaultdict, OrderedDict

from pycldf import Dictionary as CldfDictionary
from clldutils.misc import lazyproperty, nfilter
from clld.db.models import common
from clld.db.fts import tsvector
from clld.db.meta import DBSession

from dictionaria.lib.ingest import BaseDictionary
from dictionaria import models


def get_foreign_keys(ds, from_table):
    """
    :param ds: A CLDF Dataset object.
    :param from_table: A csvw.metadata.Table object.
    :return: a `dict` mapping CLDF component names to `list`s of column names in `from_table`,
    which are foreign keys into the component.
    """
    res = defaultdict(list)
    for component in ['EntryTable', 'SenseTable', 'ExampleTable']:
        ref = ds[component]
        for fk in from_table.tableSchema.foreignKeys:
            if fk.reference.resource == ref.url and \
                    fk.reference.columnReference == ref.tableSchema.primaryKey and \
                    len(fk.columnReference) == 1:
                res[component].append(fk.columnReference[0])
    return res


def get_labels(table, colmap, submission, exclude=None):
    labels = OrderedDict(submission.props.get('labels', []))
    exclude = exclude or []
    exclude.extend(['Media_IDs', 'ZCom1'])
    res = OrderedDict()
    for col in table.tableSchema.columns:
        if col.name not in exclude and col.name not in colmap.values():
            res[col.name] = (col.titles.getfirst() if col.titles else col.name, False)
    if submission.props.get('entry_map'):
        for key, label in labels.items():
            if key in submission.props['entry_map']:
                res[submission.props['entry_map'][key]] = (
                    label, key in submission.props.get('process_links_in_labels', []))
    return res


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

        try:
            media = {d['ID']: d for d in self.cldf['media.csv']}
        except KeyError:
            media = {}

        metalanguages = submission.props.get('metalanguages', {})

        entries = self.cldf['EntryTable']
        colmap = {k: self.cldf['EntryTable', k].name
                  for k in ['id', 'headword', 'partOfSpeech', 'languageReference']}
        fks = get_foreign_keys(self.cldf, entries)
        elabels = get_labels(entries, colmap, submission, exclude=fks['EntryTable'][:])

        for lemma in entries:
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

            files = [(md5, media[md5]) for md5 in set(lemma.get('Media_IDs', [])) if md5 in media]
            for md5, spec in sorted(
                files,
                key=lambda i: i[1].get(submission.props.get('media_order', 'Description')) or i[1]['ID']
            ):
                submission.add_file(None, md5, common.Unit_files, word, spec)

            for index, (key, label) in enumerate(elabels.items()):
                label, with_links = label
                if lemma.get(key):
                    DBSession.add(common.Unit_data(
                        object_pk=word.pk,
                        key=label,
                        value=lemma[key],
                        ord=index,
                        jsondata=dict(with_links=with_links)))

        DBSession.flush()

        #
        # Now that all entries are in the DB and have primary keys, we can create the
        # self-referential links:
        #
        fullentries = defaultdict(list)
        for lemma in entries:
            fullentries[lemma[colmap['id']]].extend(list(lemma.items()))
            word = data['Word'][lemma[colmap['id']]]
            for col in fks['EntryTable']:
                col = self.cldf['EntryTable', col]
                label = col.titles.getfirst() if col.titles else col.name
                if label == 'Entry_IDs':
                    label = 'See also'
                for lid in lemma[col.name] or []:
                    if lid not in data['Word']:
                        print('missing entry ID: {0}'.format(lid))
                    else:
                        DBSession.add(models.SeeAlso(
                            source_pk=word.pk, target_pk=data['Word'][lid].pk, description=label))

        sense2word = {}
        colmap = {k: self.cldf['SenseTable', k].name
                  for k in ['id', 'entryReference', 'description']}
        slabels = get_labels(self.cldf['SenseTable'], colmap, submission)

        for sense in self.cldf['SenseTable']:
            fullentries[sense[colmap['entryReference']]].extend(list(sense.items()))
            sense2word[sense[colmap['id']]] = sense[colmap['entryReference']]
            try:
                w = data['Word'][sense[colmap['entryReference']]]
            except KeyError:
                print('missing entry: {0}'.format(sense[colmap['entryReference']]))
                continue
            dsc = sense[colmap['description']]
            if not isinstance(dsc, list):
                dsc = [dsc]
            kw = dict(
                id=id_(sense[colmap['id']]),
                name='; '.join(nfilter(dsc)),
                word=w)
            if 'alt_translation1' in sense and metalanguages.get('gxx'):
                kw['alt_translation1'] = sense['alt_translation1']
                kw['alt_translation_language1'] = metalanguages.get('gxx')
            if 'alt_translation2' in sense and metalanguages.get('gxy'):
                kw['alt_translation2'] = sense['alt_translation2']
                kw['alt_translation_language2'] = metalanguages.get('gxy')
            m = data.add(models.Meaning, sense[colmap['id']], **kw)
            DBSession.flush()

            for index, (key, label) in enumerate(slabels.items()):
                label, with_links = label
                if sense.get(key):
                    DBSession.add(models.Meaning_data(
                        object_pk=m.pk,
                        key=label,
                        value=sense[key],
                        ord=index,
                        jsondata=dict(with_links=with_links)))

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
            files = [(md5, media[md5]) for md5 in set(sense.get('Media_IDs', [])) if md5 in media]
            for md5, spec in sorted(
                files,
                key=lambda i: i[1].get(submission.props.get('media_order', 'Description')) or i[1]['ID']
            ):
                submission.add_file(None, md5, models.Meaning_files, m, spec)

        colmap = {k: self.cldf['ExampleTable', k].name
                  for k in ['id', 'primaryText', 'translatedText']}
        for ex in self.cldf['ExampleTable']:
            #
            # FIXME: Detect the column with sense IDs by looking at the foreign keys!
            #
            mids = ex.get('Senses') or ex.get('Sense_IDs', [])
            if not isinstance(mids, list):
                mids = mids.split(' ; ')
            for mid in mids:
                if mid not in data['Meaning']:
                    continue
                if mid in sense2word:
                    fullentries[sense2word[mid]].extend(list(ex.items()))
                    models.MeaningSentence(
                        meaning=data['Meaning'][mid],
                        sentence=data['Example'][ex[colmap['id']]])
                else:
                    print('missing sense: {0}'.format(mid))

        for wid, d in fullentries.items():
            if wid in data['Word']:
                data['Word'][wid].fts = tsvector(
                    '; '.join('{0}: {1}'.format(k, v) for k, v in d if v))
