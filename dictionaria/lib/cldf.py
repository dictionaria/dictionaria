from collections import defaultdict
import re

from pycldf import iter_datasets
from clldutils.misc import lazyproperty, nfilter
from clld.db.models import common
from clld.db.fts import tsvector
from clld.db.meta import DBSession

from dictionaria.lib.ingest import BaseDictionary
from dictionaria import models


def read_media_table(cldf):
    media = {}

    if cldf.get('MediaTable'):
        tablename = 'MediaTable'
    elif cldf.get('media.csv'):
        tablename = 'media.csv'
    else:
        return media

    property_map = {
        cldf[tablename, prop].name: fallback
        for prop, fallback in (
            ('id', 'ID'),
            ('name', 'Filename'),
            ('description', 'Description'),
            ('languageReference', 'Language_ID'),
            ('mediaType', 'mimetype'),
            ('downloadUrl', 'URL'))
        if cldf.get((tablename, prop))}

    for row in cldf[tablename]:
        media_item = {property_map.get(k) or k: v for k, v in row.items()}
        media[media_item['ID']] = media_item

    return media


def get_foreign_keys(ds, from_table):
    """
    :param ds: A CLDF Dataset object.
    :param from_table: A csvw.metadata.Table object.
    :return: a `dict` mapping CLDF component names to `list`s of column names in `from_table`,
    which are foreign keys into the component.
    """
    res = defaultdict(list)
    for component in ['EntryTable', 'SenseTable', 'ExampleTable']:
        ref = ds.get(component)
        if not ref:
            continue
        for fk in from_table.tableSchema.foreignKeys:
            if fk.reference.resource == ref.url and \
                    fk.reference.columnReference == ref.tableSchema.primaryKey and \
                    len(fk.columnReference) == 1:
                res[component].append(fk.columnReference[0])
    return res


def get_labels(type_, table, colmap, submission, exclude=None):
    labels = dict(submission.props.get('labels', []))
    exclude = exclude or []
    exclude.extend([colmap.get('mediaReference', 'Media_IDs'), 'ZCom1'])
    res = {}
    for col in table.tableSchema.columns:
        if col.name not in exclude and col.name not in colmap.values():
            res[col.name] = (col.titles.getfirst() if col.titles else col.name, False)
    map_name = f'{type_}_map'
    if submission.props.get(map_name):
        for key, label in labels.items():
            if key in submission.props[map_name]:
                res[submission.props[map_name][key]] = (
                    label, key in submission.props.get('process_links_in_labels', []))
    order_name = f'{type_}_custom_order'
    if submission.props.get(order_name):
        res = {k: res[k] for k in submission.props[order_name] if k in res}
    return res


class Dictionary(BaseDictionary):
    @lazyproperty
    def cldf(self):
        try:
            return next(
                ds
                for ds in iter_datasets(self.dir)
                if ds.module == 'Dictionary')
        except StopIteration:
            raise ValueError(f'no cldf metadata found in {self.dir}')

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
            return f'{submission.id}-{oid}'

        print('######\n a CLDF dict! \n####')

        media = read_media_table(self.cldf)

        metalanguages = submission.props.get('metalanguages', {})
        entries = self.cldf['EntryTable']
        colmap = {k: self.cldf['EntryTable', k].name
                  for k in [
                      'id', 'headword', 'partOfSpeech', 'languageReference',
                      'mediaReference', 'source']
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

            media_ids = set(
                lemma.get(colmap.get('mediaReference', 'Media_IDs'))
                or [])
            files = sorted(
                ((md5, media[md5]) for md5 in media_ids if md5 in media),
                key=lambda i: i[1].get(submission.props.get('media_order', 'Description')) or i[1]['ID'])
            for md5, spec in files:
                submission.add_file(None, md5, common.Unit_files, word, spec)

            self.add_refs(data, 'EntryTable', lemma, word, elabels)

            for index, (key, label) in enumerate(elabels.items()):
                label, with_links = label
                if lemma.get(key):
                    DBSession.add(common.Unit_data(
                        object_pk=word.pk,
                        key=label.replace('_', ' '),
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
                        print('missing entry ID:', lid)
                    else:
                        DBSession.add(models.SeeAlso(
                            source_pk=word.pk, target_pk=data['Word'][lid].pk, description=label))

        sense2word = {}
        colmap = {
            k: self.cldf['SenseTable', k].name
            for k in [
                'id', 'entryReference', 'description', 'mediaReference',
                'concepticonReference', 'source']
            if self.cldf.get(('SenseTable', k))}
        fks = get_foreign_keys(self.cldf, self.cldf['SenseTable'])

        slabels = get_labels(
            'sense',
            self.cldf['SenseTable'],
            colmap,
            submission,
            exclude=['alt_translation1', 'alt_translation2'] + fks['EntryTable'][:])

        for sense_index, sense in enumerate(self.cldf['SenseTable']):
            fullentries[sense[colmap['entryReference']]].extend(list(sense.items()))
            sense2word[sense[colmap['id']]] = sense[colmap['entryReference']]
            try:
                w = data['Word'][sense[colmap['entryReference']]]
            except KeyError:
                print('missing entry:', sense[colmap['entryReference']])
                continue
            dsc = sense[colmap['description']]
            if not isinstance(dsc, list):
                dsc = [dsc]
            kw = dict(
                id=id_(sense[colmap['id']]),
                name='; '.join(nfilter(dsc)),
                semantic_domain=sense.pop('Semantic_Domain', None),
                ord=sense_index,
                word=w)
            if 'alt_translation1' in sense and metalanguages.get('gxx'):
                kw['alt_translation1'] = sense['alt_translation1']
                kw['alt_translation_language1'] = metalanguages.get('gxx')
            if 'alt_translation2' in sense and metalanguages.get('gxy'):
                kw['alt_translation2'] = sense['alt_translation2']
                kw['alt_translation_language2'] = metalanguages.get('gxy')
            meaning = data.add(models.Meaning, sense[colmap['id']], **kw)
            DBSession.flush()

            self.add_refs(data, 'SenseTable', sense, meaning, slabels)

            for index, (key, label) in enumerate(slabels.items()):
                label, with_links = label
                if sense.get(key):
                    DBSession.add(models.Meaning_data(
                        object_pk=meaning.pk,
                        key=label.replace('_', ' '),
                        value=sense[key],
                        ord=index,
                        jsondata=dict(with_links=with_links)))

            concepticon_id_field = (
                sense.get(colmap.get('concepticonReference', 'Concepticon_ID'))
                or '')
            concepticon_gloss_field = sense.get('Comparison_Meaning') or ''

            concepticon_ids = {
                elem.strip()
                for elem in concepticon_id_field.split(';')
                if elem.strip()}
            for gloss in concepticon_gloss_field.split(';'):
                gloss = gloss.strip()
                match = re.fullmatch(r'(?:[^[]*)\[(\d+)\]', gloss)
                if match:
                    concepticon_ids.add(match.group(1))

            for i, cid in enumerate(sorted(concepticon_ids)):
                if cid not in comparison_meanings:
                    continue
                concept = comparison_meanings[cid]

                vsid = f'{lang.id}-{concept}'
                vs = data['ValueSet'].get(vsid)
                if not vs:
                    vs = data.add(
                        common.ValueSet, vsid,
                        id=vsid,
                        language=lang,
                        contribution=vocab,
                        parameter_pk=concept)

                DBSession.add(models.Counterpart(
                    id=f'{meaning.id}-{i}', name=w.name, valueset=vs, word=w))

            DBSession.flush()
            media_ids = set(
                sense.get(colmap.get('mediaReference', 'Media_IDs'))
                or [])
            files = sorted(
                ((md5, media[md5]) for md5 in media_ids if md5 in media),
                key=lambda i: i[1].get(submission.props.get('media_order', 'Description')) or i[1]['ID'])
            for md5, spec in files:
                submission.add_file(None, md5, models.Meaning_files, meaning, spec)

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
                            print('missing entry ID:', eid)
                        else:
                            DBSession.add(models.Nym(
                                source_pk=meaning.pk, target_pk=data['Word'][eid].pk, description=label))

        colmap = {k: self.cldf['ExampleTable', k].name
                  for k in ['id', 'primaryText', 'translatedText']
                  if self.cldf.get(('ExampleTable', k))}
        for ex in self.cldf.get('ExampleTable', ()):
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
                    print('missing sense:', mid)

        for wid, d in fullentries.items():
            if wid in data['Word']:
                data['Word'][wid].fts = tsvector(
                    '; '.join('{0}: {1}'.format(k, v) for k, v in d if v))
