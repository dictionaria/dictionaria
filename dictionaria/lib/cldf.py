# coding: utf8
from __future__ import unicode_literals, print_function, division
from collections import defaultdict, OrderedDict
from itertools import chain

from csvw import dsv
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

        media = self.dir / 'media.csv'
        if media.exists():
            media = {d['ID']: d for d in dsv.reader(media, dicts=True)}
        else:
            media = {}

        metalanguages = submission.props.get('metalanguages', {})

        entries = self.cldf['EntryTable']

        colmap = {k: self.cldf['EntryTable', k].name
                  for k in ['id', 'headword', 'partOfSpeech', 'languageReference']}
        fks = get_foreign_keys(self.cldf, entries)

        elabels = OrderedDict()
        for col in entries.tableSchema.columns:
            if col not in fks['EntryTable'] and col.name not in colmap.values():
                elabels[col.name] = (col.titles.getfirst() if col.titles else col.name, False)
        if submission.md['properties'].get('entry_map'):
            for key, label in labels.items():
                if key in submission.md['properties']['entry_map']:
                    elabels[submission.md['properties']['entry_map'][key]] = (
                        label,
                        key in submission.md['properties'].get('process_links_in_labels', []))

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
            for attr, type_ in [('picture', 'image'), ('sound', 'audio')]:
                fnames = lemma.pop(attr, None)
                if fnames is None:
                    fnames = lemma.pop(type_, None)
                if fnames:
                    fnames = [fnames] if not isinstance(fnames, list) else fnames
                    for fname in fnames:
                        submission.add_file(type_, fname, common.Unit_files, word)

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
                for lid in lemma[col.name] or []:
                    DBSession.add(models.SeeAlso(
                        source_pk=word.pk,
                        target_pk=data['Word'][lid].pk,
                        description=col.titles.getfirst() if col.titles else col.name))

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
            dsc = sense[colmap['description']]
            if not isinstance(dsc, list):
                dsc = [dsc]
            kw = dict(
                id=id_(sense[colmap['id']]),
                name='; '.join(nfilter(dsc)),
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
            for attr, type_ in [('picture', 'image'), ('sound', 'audio'), ('Media_IDs', 'image')]:
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
            #
            # FIXME: Detect the column with sense IDs by looking at the foreign keys!
            #
            mids = ex.get('Senses') or ex.get('Sense_IDs', [])
            if not isinstance(mids, list):
                mids = mids.split(' ; ')
            for mid in mids:
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
