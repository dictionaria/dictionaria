from collections import defaultdict, OrderedDict
import re

from pycldf import Dictionary as CldfDictionary, Sources
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


def get_labels(type_, table, colmap, submission, exclude=None):
    labels = OrderedDict(submission.props.get('labels', []))
    exclude = exclude or []
    exclude.extend(['Media_IDs', 'ZCom1'])
    res = OrderedDict()
    for col in table.tableSchema.columns:
        if col.name not in exclude and col.name not in colmap.values():
            res[col.name] = (col.titles.getfirst() if col.titles else col.name, False)
    map_name = '{0}_map'.format(type_)
    if submission.props.get(map_name):
        for key, label in labels.items():
            if key in submission.props[map_name]:
                res[submission.props[map_name][key]] = (
                    label, key in submission.props.get('process_links_in_labels', []))
    order_name = '{0}_custom_order'.format(type_)
    if submission.props.get(order_name):
        res = OrderedDict([(k, res[k]) for k in submission.props[order_name] if k in res])
    return res


class Dictionary(BaseDictionary):
    @lazyproperty
    def cldf(self):
        return CldfDictionary.from_metadata(self.dir / 'cldf-md.json')

    def add_refs(self, data, table, row, obj, labels):
        if table == 'EntryTable':
            model, kw = models.WordReference, dict(word=obj)
        elif table == 'SenseTable':
            model, kw = models.MeaningReference, dict(meaning=obj)
        else:
            raise ValueError(table)
        refs_col = self.cldf.get((table, 'source'))
        if refs_col:
            for sid, context in map(self.cldf.sources.parse, row.get(refs_col.name, [])):
                if sid in data['DictionarySource']:
                    DBSession.add(model(
                        source=data['DictionarySource'][sid],
                        description=labels.get(context, (context, None))[0], **kw))

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
                  for k in ['id', 'headword', 'partOfSpeech', 'languageReference', 'source']
                  if self.cldf.get(('EntryTable', k))}
        fks = get_foreign_keys(self.cldf, entries)
        elabels = get_labels('entry', entries, colmap, submission, exclude=fks['EntryTable'][:])

        for lemma in entries:
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

            self.add_refs(data, 'EntryTable', lemma, word, elabels)

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
                label = label.replace('_', ' ')
                for lid in lemma[col.name] or []:
                    if lid not in data['Word']:
                        print('missing entry ID: {0}'.format(lid))
                    else:
                        DBSession.add(models.SeeAlso(
                            source_pk=word.pk, target_pk=data['Word'][lid].pk, description=label))

        sense2word = {}
        colmap = {k: self.cldf['SenseTable', k].name
                  for k in ['id', 'entryReference', 'description', 'source']
                  if self.cldf.get(('SenseTable', k))}
        fks = get_foreign_keys(self.cldf, self.cldf['SenseTable'])

        slabels = get_labels(
            'sense',
            self.cldf['SenseTable'],
            colmap,
            submission,
            exclude=['alt_translation1', 'alt_translation2'] + fks['EntryTable'][:])

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
                semantic_domain=sense.pop('Semantic_Domain', None),
                word=w)
            if 'alt_translation1' in sense and metalanguages.get('gxx'):
                kw['alt_translation1'] = sense['alt_translation1']
                kw['alt_translation_language1'] = metalanguages.get('gxx')
            if 'alt_translation2' in sense and metalanguages.get('gxy'):
                kw['alt_translation2'] = sense['alt_translation2']
                kw['alt_translation_language2'] = metalanguages.get('gxy')
            m = data.add(models.Meaning, sense[colmap['id']], **kw)
            DBSession.flush()

            self.add_refs(data, 'SenseTable', sense, m, slabels)

            for index, (key, label) in enumerate(slabels.items()):
                label, with_links = label
                if sense.get(key):
                    DBSession.add(models.Meaning_data(
                        object_pk=m.pk,
                        key=label,
                        value=sense[key],
                        ord=index,
                        jsondata=dict(with_links=with_links)))

            concepticon_field = sense.get('Concepticon_ID') or ''
            concepticon_ids = [
                elem.strip()
                for elem in concepticon_field.split(';')
                if elem.strip()]
            for i, concepticon_id in enumerate(concepticon_ids):
                match = re.fullmatch(r'([^]]*)\s*\[(\d+)\]', concepticon_id)
                if not match:
                    continue
                _, cid = match.groups()
                if cid not in comparison_meanings:
                    continue
                concept = comparison_meanings[cid]

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

            for col in fks['EntryTable']:
                col = self.cldf['SenseTable', col]
                if col.name == colmap['entryReference']:
                    continue
                label = col.titles.getfirst() if col.titles else col.name
                label = label.replace('_', ' ')
                entry_ids = sense[col.name]
                if entry_ids:
                    if not isinstance(entry_ids, list):
                        entry_ids = [entry_ids]
                    for eid in entry_ids:
                        if eid not in data['Word']:
                            print('missing entry ID: {0}'.format(eid))
                        else:
                            DBSession.add(models.Nym(
                                source_pk=m.pk, target_pk=data['Word'][eid].pk, description=label))

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
