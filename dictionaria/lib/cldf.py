"""Helper functions for dictionaria."""
import json
import re
from collections import Counter, defaultdict, namedtuple
from itertools import chain

from clld.cliutil import bibtex2source
from clld.db.fts import tsvector
from clld.db.meta import DBSession
from clld.db.models import common
from clld.lib import bibtex
from pycldf import Sources, iter_datasets

from dictionaria import models


def shorten_url(property_url):
    """Only return the anchor of a property url."""
    _, anchor = property_url.split('#')
    return anchor


def get_labels(props, map_type):
    """Extract a map from columns to labels from the json metadata."""
    labels = props.get('labels') or {}
    marker_map = props.get(map_type) or {}
    return {
        colname: label
        for sfm_marker, label in labels.items()
        if (colname := marker_map.get(sfm_marker))}


class ColumnNameMap:
    """Mapper object that returns human readable labels from CLDF columns."""

    def __init__(self, cldf_table, labels):
        """Construct a column map from CLDF meta data and some custom labels.

        This also hardcodes some cases where dictionaries are older than the
        actual CLDF properties themselves.
        """
        self.labels = labels
        self.properties = {
            column.name: shorten_url(column.propertyUrl.uri)
            for column in cldf_table.tableSchema.columns
            if column.propertyUrl}
        # some dictionaries don't know about the mediaReference property, yet
        if 'Media_IDs' not in self.properties:
            self.properties['Media_IDs'] = 'mediaReference'
        if 'Entry_IDs' not in self.properties:
            self.properties['Entry_IDs'] = 'entryReference'
        # some dictionaries also don't know about the media table itself, yet
        if 'mimetype' not in self.properties:
            self.properties['mimetype'] = 'mediaType'
        if 'URL' not in self.properties:
            self.properties['URL'] = 'downloadUrl'
        self.titles = {
            column.name: column.titles.getfirst()
            for column in cldf_table.tableSchema.columns
            if column.name != 'alt_translation1'
            and column.name != 'alt_translation2'
            and column.titles}

    def map(self, colname):
        """Return human readable label for a CLDF column."""
        label = (
            self.properties.get(colname)
            or self.labels.get(colname, colname))
        return self.titles.get(label, label)


def read_table(cldf, table_name, labels):
    """Iterate over rows of a table in a CLDF data set.

    This maps .
    """
    table = cldf.get(table_name)
    if not table:
        return
    colmap = ColumnNameMap(table, labels)
    for row in table:
        yield {
            colmap.map(colname): cell
            for colname, cell in row.items()
            if cell != [] and cell != '' and cell is not None}


CldfRecord = namedtuple('CldfRecord', 'std free')
CldfRecord.__doc__ = """A single record from a CLDF table.

std:  dictionary of 'standard' fields that are handled explicitly.
free: dictionary of 'free' fields that are dumped into *_data objects.
"""


def make_cldf_record(csv_row, standard_fields, custom_order):
    """Return a cldf record from a bare dictionary.

    This sorts the elements of `csv_row` in to the `std` and `free` attributes
    of the record according to `standard_fields`.
    """
    std = {k: v for k, v in csv_row.items() if k in standard_fields}
    free_fields = {}
    free_fields.update((k, True) for k in (custom_order or ()))
    free_fields.update(
        (k, True)
        for k in csv_row
        if k not in standard_fields and k not in free_fields)
    free = {k: csv_row[k] for k in free_fields if k in csv_row}
    return CldfRecord(std, free)


def read_cldf_entries(cldf, labels, custom_order):
    """Return entry records from a cldf data set."""
    standard_fields = {
        'id',
        'languageReference',
        'headword',
        'partOfSpeech',
        'mediaReference',
        'source',
    }
    return [
        make_cldf_record(entry, standard_fields, custom_order)
        for entry in read_table(cldf, 'EntryTable', labels)
        if entry.get('headword')]


def read_cldf_senses(cldf, labels, custom_order):
    """Return sense records from a cldf data set."""
    standard_fields = {
        'id',
        'description',
        'entryReference',
        'alt_translation1',
        'alt_translation2',
        'mediaReference',
        'source',
        'Semantic_Domain',
    }
    return [
        make_cldf_record(sense, standard_fields, custom_order)
        for sense in read_table(cldf, 'SenseTable', labels)]


def read_cldf_examples(cldf, labels, custom_order):
    """Return example records from a cldf data set."""
    standard_fields = {
        'id',
        'primaryText',
        'analyzedWord',
        'gloss',
        'translatedText',
        'alt_translation1',
        'alt_translation2',
        'comment',
        'languageReference',
        'metaLanguageReference',
        'mediaReference',
        'Sense_IDs',
        'original_script',
        'Corpus_Reference',
        'source',
    }
    return [
        make_cldf_record(example, standard_fields, custom_order)
        for example in read_table(cldf, 'ExampleTable', labels)]


def _fix_media_fields(kvpair):
    if kvpair[0] == 'downloadUrl':
        return 'URL', kvpair[1]
    else:
        return kvpair


def fix_media_fields(piece_of_media):
    return dict(map(_fix_media_fields, piece_of_media.items()))


def read_cldf_media(cldf):
    """Return media file information from a cldf data set.

    Note that unlike the functions above, this just returns the records as
    standard Python dictionaries, rather than CldfRecord objects.
    """
    table_name = 'MediaTable' if 'MediaTable' in cldf else 'media.csv'
    return {
        piece_of_media['id']: fix_media_fields(piece_of_media)
        for piece_of_media in read_table(cldf, table_name, {})}


def make_sources(cldf_sources, dictionary):
    """Create Source objects from a cldf data set's bibliography."""
    if not cldf_sources:
        return {}
    print('loading sources ...')
    sources = {}
    for record in cldf_sources:
        bibrecord = bibtex.Record(record.genre, record.id, **record)
        source = bibtex2source(bibrecord, models.DictionarySource)
        source.dictionary_pk = dictionary.pk
        original_id = source.id
        source.id = f'{dictionary.id}-{source.id}'
        sources[original_id] = source
    return sources


def get_crossref_fields(cldf, table_name, labels):
    """Return column names, which are foreign keys into the entry table."""
    table = cldf.get(table_name)
    if not table:
        return []
    entry_table = cldf['EntryTable']
    colmap = ColumnNameMap(table, labels)
    return [
        colmap.map(fk.columnReference[0])
        for fk in table.tableSchema.foreignKeys
        if fk.reference.resource == entry_table.url
        and fk.reference.columnReference == entry_table.tableSchema.primaryKey
        and len(fk.columnReference) == 1]


def collect_full_entries(cldf_entries, cldf_senses, cldf_examples):
    """Return contents of all fields for all entries for full-text search."""
    sense2word = {
        cldf_sense.std['id']: cldf_sense.std['entryReference']
        for cldf_sense in cldf_senses}
    fullentries = defaultdict(list)
    for cldf_entry in cldf_entries:
        fullentries[cldf_entry.std['id']].extend(chain(
            cldf_entry.std.items(),
            cldf_entry.free.items()))
    for cldf_sense in cldf_senses:
        fullentries[cldf_sense.std['entryReference']].extend(chain(
            cldf_sense.std.items(),
            cldf_sense.free.items()))
    for cldf_example in cldf_examples:
        exdata = list(chain(
            cldf_example.std.items(),
            cldf_example.free.items()))
        for mid in example_sense_ids(cldf_example):
            if (entry_id := sense2word.get(mid)):
                fullentries[entry_id].extend(exdata)
    return fullentries


def collect_custom_field_data(cldf_entries, entry_senses, field_names, metalanguages):
    """Return data necessary to fill the custom fields of an entry."""
    if not field_names:
        return {}

    # NOTE(johannes): The 'lang-' prefix was added earlier in the process.
    altlang1 = 'lang-{}'.format(metalanguages.get('gxx'))
    altlang2 = 'lang-{}'.format(metalanguages.get('gxy'))

    def sense_field_value(cldf_sense, field):
        if field == altlang1:
            return cldf_sense.std.get('alt_translation1', '')
        elif field == altlang2:
            return cldf_sense.std.get('alt_translation2', '')
        else:
            return cldf_sense.free.get(field, '')

    tab_data = defaultdict(dict)
    for cldf_entry in cldf_entries:
        entry_id = cldf_entry.std['id']
        for field in field_names:
            if (val := cldf_entry.free.get(field)):
                tab_data[entry_id][field] = val
            else:
                sense_vals = [
                    sense_field_value(s, field)
                    for s in entry_senses.get(entry_id, ())]
                if any(sense_vals):
                    sep = ' ; ' if field in (altlang1, altlang2) else ' / '
                    tab_data[entry_id][field] = sep.join(filter(None, sense_vals))
    return tab_data


class HomonymCounter:
    """Object assigning homonym numbers to dictionary entries."""

    def __init__(self, names):
        """Initialise homonym counter with all known headwords.

        We need to feed in all headwords ahead of time, because we need to be
        able to tell unique headwords apart from duplicates when we first look
        at them.
        """
        duplicates = Counter(names)
        self.duplicates = {name for name, freq in duplicates.items() if freq > 1}
        self.visited = Counter()

    def homonym_no(self, name):
        """Return homonym number of a headword or 0 if a headword is unique."""
        if name in self.duplicates:
            self.visited[name] += 1
            return self.visited[name]
        else:
            # unique forms don't have a homonym number
            return 0


def make_entries(
    cldf_entries, cldf_senses, cldf_examples, language, dictionary,
    custom_fields, second_tab, metalanguages,
):
    """Create ORM entries from entry records.

    Entries are mapped to their original ids for future reference.
    """
    fullentries = collect_full_entries(cldf_entries, cldf_senses, cldf_examples)

    entry_senses = defaultdict(list)
    descriptions = defaultdict(list)
    semantic_domains = defaultdict(set)
    for cldf_sense in cldf_senses:
        entry_id = cldf_sense.std['entryReference']
        entry_senses[entry_id].append(cldf_sense)
        descriptions[entry_id].append(cldf_sense.std.get('description', ''))
        if (semdom := cldf_sense.std.get('Semantic_Domain')):
            semantic_domains[entry_id].add(semdom)

    # NOTE(johannes): An older version of the code assumed that custom fields
    # are handled *way* later than they are now so the json file works on the
    # actual *HTML column titles* rather than the tables themselves.
    custom_fields = [field.replace(' ', '_') for field in custom_fields]
    second_tab = [field.replace(' ', '_') for field in second_tab]

    tab1_data = collect_custom_field_data(
        cldf_entries, entry_senses, custom_fields, metalanguages)
    tab2_data = collect_custom_field_data(
        cldf_entries, entry_senses, second_tab, metalanguages)

    def get_tab_value(entry_id, tab_data, fields, index):
        if index < len(fields) and (tab := tab_data.get(entry_id)):
            field = fields[index]
            return tab.get(field)
        else:
            return None

    homonym_counter = HomonymCounter(
        cldf_entry.std['headword'] for cldf_entry in cldf_entries)

    return {
        cldf_entry.std['id']: models.Word(
            id='{}-{}'.format(dictionary.id, (eid := cldf_entry.std['id'])),
            name=cldf_entry.std['headword'],
            pos=cldf_entry.std.get('partOfSpeech'),
            number=homonym_counter.homonym_no(cldf_entry.std['headword']),
            description=' / '.join(descriptions.get(eid) or ()),
            semantic_domain=' ; '.join(sorted(semantic_domains.get(eid) or ())),
            fts=tsvector('; '.join(
                f'{k}: {v}'
                for k, v in fullentries.get(cldf_entry.std['id'], ())
                if v)),
            language_pk=language.pk,
            dictionary_pk=dictionary.pk,
            custom_field1=get_tab_value(eid, tab1_data, custom_fields, 0),
            custom_field2=get_tab_value(eid, tab1_data, custom_fields, 1),
            second_tab1=get_tab_value(eid, tab2_data, second_tab, 0),
            second_tab2=get_tab_value(eid, tab2_data, second_tab, 1),
            second_tab3=get_tab_value(eid, tab2_data, second_tab, 2))
        for cldf_entry in cldf_entries}


def entry_id_exists(entries, eid):
    """Return true iff. an entry exists.

    Prints an error message if it doesn't.
    """
    if eid in entries:
        return True
    else:
        print(f"missing entry ID: '{eid}'")
        return False


def collect_example_custom_fields(cldf_example, field_names, metalanguages):
    """Return custom fields for a cldf example."""
    if not field_names:
        return {}

    # NOTE(johannes): No 'lang-' prefix here, apparently
    altlang1 = metalanguages.get('gxx')
    altlang2 = metalanguages.get('gxy')

    def example_field_value(cldf_example, field):
        if field == altlang1:
            return cldf_example.std.get('alt_translation1', '')
        elif field == altlang2:
            return cldf_example.std.get('alt_translation2', '')
        else:
            return cldf_example.free.get(field, '')

    return {
        field: val
        for field in field_names
        if (val := example_field_value(cldf_example, field))}


def make_example(
    cldf_example, language, dictionary, metalanguages, number, custom_fields,
):
    """Create ORM object for an example record."""
    abbrev_pattern = re.compile(r'\$(?P<abbr>[a-z1-3][a-z]*(\.[a-z]+)?)')
    altlang1 = metalanguages.get('gxx')
    altlang2 = metalanguages.get('gxy')
    alttrans1 = cldf_example.std.get('alt_translation1')
    alttrans2 = cldf_example.std.get('alt_translation2')

    tab_data = collect_example_custom_fields(
        cldf_example, custom_fields, metalanguages)

    def get_tab_value(index):
        if index < len(custom_fields):
            field = custom_fields[index]
            return tab_data.get(field)
        else:
            return None

    return models.Example(
        id='{}-{}'.format(dictionary.id, cldf_example.std['id'].replace('.', '_')),
        name=cldf_example.std['primaryText'],
        number=str(number),
        source=cldf_example.std.get('Corpus_Reference'),
        comment=cldf_example.std.get('comment'),
        original_script=cldf_example.std.get('original_script'),
        language_pk=language.pk,
        dictionary_pk=dictionary.pk,
        analyzed='\t'.join([
            w for w in cldf_example.std.get('analyzedWord') or () if w]) or None,
        gloss='\t'.join([
            abbrev_pattern.sub(lambda m: m.group('abbr').upper(), w or '')
            for w in cldf_example.std.get('gloss', ())]) or None,
        description=cldf_example.std.get('translatedText'),
        alt_translation_language1=altlang1 if alttrans1 else None,
        alt_translation_language2=altlang2 if alttrans2 else None,
        alt_translation1=alttrans1 if altlang1 else None,
        alt_translation2=alttrans2 if altlang2 else None,
        custom_field1=get_tab_value(0),
        custom_field2=get_tab_value(1))


def make_examples(
    cldf_examples, language, dictionary, metalanguages, custom_fields,
):
    """Return ORM examples for example records.

    Examples are mapped to their original ids for future reference.
    """
    return {
        cldf_example.std['id']: make_example(
            cldf_example, language, dictionary, metalanguages, number,
            custom_fields)
        for number, cldf_example in enumerate(cldf_examples, 1)}


def md5_in_cdstar(md5, cdstar, type_):
    """Return true if checksum is found in cdstar.

    Print error message if it doesn't.
    """
    if md5 in cdstar:
        return True
    else:
        print(type_, 'file missing:', md5)
        return False


def make_entry_file(entry, md5, piece_of_media, fileinfo):
    """Create ORM object for an entry--file association."""
    jsondata = {}
    jsondata.update(fileinfo.items())
    jsondata.update(piece_of_media.items())
    return common.Unit_files(
        id=f'{entry.id}-{md5}',
        name=fileinfo['original'],
        object_pk=entry.pk,
        mime_type=fileinfo['mimetype'],
        jsondata=jsondata)


def iter_entry_files(cldf_entries, cldf_media, entries, cdstar, media_order_by):
    """Return ORM objects associating media files with dictionary entries."""
    entry_media_ids = {
        entry.std['id']: sorted(
            {md5
             for md5 in set(entry.std.get('mediaReference') or ())
             if md5_in_cdstar(md5, cdstar, 'Entry')},
            key=lambda md5: cldf_media[md5].get(media_order_by) or '')
        for entry in cldf_entries}
    return (
        make_entry_file(entries[eid], md5, cldf_media[md5], cdstar[md5])
        for eid, media_ids in entry_media_ids.items()
        for md5 in media_ids)


def iter_entry_refs(cldf_entries, entries, sources):
    """Return ORM objects associating dictionary entries with the bibliography."""
    for cldf_entry in cldf_entries:
        for ref in cldf_entry.std.get('source') or ():
            source_id, context = Sources.parse(ref)
            if source_id not in sources:
                continue
            yield models.WordReference(
                word_pk=entries[cldf_entry.std['id']].pk,
                source_pk=sources[source_id].pk,
                description=context)


def iter_entry_data_points(
    entry, free_fields, field_order, blacklist, labels_with_links,
):
    """Return ORM objects for arbitrary data attached to a dictionary entry."""
    if field_order:
        fields = {
            key: value
            for key in field_order
            if (value := free_fields.get(key))}
    else:
        fields = free_fields
    return (
        common.Unit_data(
            object_pk=entry.pk,
            key=key.replace('_', ' '),
            value=value,
            ord=number,
            jsondata={'with_links': key in labels_with_links})
        for number, (key, value) in enumerate(fields.items())
        if value and key not in blacklist)


def iter_entry_data(
    cldf_entries, entries, field_order, blacklist, labels_with_links,
):
    """Return ORM objects for arbitrary data attached to dictionary entries."""
    return (
        entry_data
        for cldf_entry in cldf_entries
        for entry_data in iter_entry_data_points(
            entries[cldf_entry.std['id']], cldf_entry.free, field_order,
            blacklist, labels_with_links))


def iter_entry_alttranslations(cldf_senses, entries, metalanguages):
    """Return ORM objects for non-English translations of entries.

    Non-English translations are added to the Unit_data table along with other
    additional entry information.
    """
    altlang1 = metalanguages.get('gxx')
    altlang2 = metalanguages.get('gxy')
    entry_alttrans1 = defaultdict(list)
    entry_alttrans2 = defaultdict(list)
    for cldf_sense in cldf_senses:
        entry_id = cldf_sense.std['entryReference']
        alttrans1 = cldf_sense.std.get('alt_translation1')
        alttrans2 = cldf_sense.std.get('alt_translation2')
        if alttrans1 and altlang1:
            entry_alttrans1[entry_id].append(alttrans1)
        if alttrans2 and altlang2:
            entry_alttrans2[entry_id].append(alttrans2)

    for entry_id, entry in entries.items():
        if (alttrans1 := entry_alttrans1.get(entry_id)):
            yield common.Unit_data(
                object_pk=entry.pk,
                key=f'lang-{altlang1}',
                value=' ; '.join(alttrans1))
        if (alttrans2 := entry_alttrans2.get(entry_id)):
            yield common.Unit_data(
                object_pk=entry.pk,
                key=f'lang-{altlang2}',
                value=' ; '.join(alttrans2))


def seealso_label(column_name):
    """Return label used for a cross reference."""
    return 'See also' if column_name == 'entryReference' else column_name.replace('_', ' ')


def iter_entry_seealso(cldf_entries, entries, entry_crossrefs):
    """Return ORM objects associating entries with each other."""
    return (
        models.SeeAlso(
            source_pk=entries[cldf_entry.std['id']].pk,
            target_pk=entries[ref].pk,
            description=seealso_label(key))
        for cldf_entry in cldf_entries
        for key, refs in chain(cldf_entry.std.items(), cldf_entry.free.items())
        for ref in (refs if isinstance(refs, list) else [refs])
        if key in entry_crossrefs and entry_id_exists(entries, ref))


def make_example_file(example, md5, fileinfo):
    """Create example--file association object."""
    return common.Sentence_files(
        id=f'{example.id}-{md5}',
        name=fileinfo['original'],
        object_pk=example.pk,
        mime_type=fileinfo['mimetype'],
        jsondata=fileinfo)


def iter_example_files(cldf_examples, examples, cdstar):
    """Return ORM objects associating media files with examples."""
    example_media_ids = {
        ex.std['id']: sorted({
            md5
            for md5 in set(ex.std.get('mediaReference') or ())
            if md5_in_cdstar(md5, cdstar, 'Example')})
        for ex in cldf_examples}
    return (
        make_example_file(examples[ex_id], md5, cdstar[md5])
        for ex_id, media_ids in example_media_ids.items()
        for md5 in media_ids)


def iter_example_data_points(example, free_fields, field_order):
    """Return ORM objects for arbitrary data associated to an example."""
    blacklist = ['languageReference', 'mediaReference', 'Media_IDs', 'ZCom1']
    if field_order:
        fields = {
            key: value
            for key in field_order
            if (value := free_fields.get(key))}
    else:
        fields = free_fields
    return (
        common.Sentence_data(
            object_pk=example.pk,
            key=key.replace('_', ' '),
            value=value)
        for key, value in fields.items()
        if value and key not in blacklist)


def iter_example_data(cldf_examples, examples, field_order):
    """Return ORM objects for arbitrary data associated to examples."""
    return (
        ex_data
        for ex in cldf_examples
        for ex_data in iter_example_data_points(
            examples[ex.std['id']], ex.free, field_order))


def iter_example_refs(cldf_examples, examples, sources):
    """Return ORM objects associating dictionary examples with the bibliography."""
    for cldf_example in cldf_examples:
        for ref in cldf_example.std.get('source') or ():
            source_id, context = Sources.parse(ref)
            if source_id not in sources:
                continue
            yield common.SentenceReference(
                sentence_pk=examples[cldf_example.std['id']].pk,
                source_pk=sources[source_id].pk,
                description=context)


def make_meaning(cldf_sense, entry, dictionary, metalanguages, number):
    """Create ORM object for a meaning description."""
    description = cldf_sense.std.get('description')
    altlang1 = metalanguages.get('gxx')
    altlang2 = metalanguages.get('gxy')
    alttrans1 = cldf_sense.std.get('alt_translation1')
    alttrans2 = cldf_sense.std.get('alt_translation2')
    return models.Meaning(
        id='{}-{}'.format(dictionary.id, cldf_sense.std['id']),
        word_pk=entry.pk,
        ord=number,
        name=description,
        semantic_domain=cldf_sense.std.get('Semantic_Domain'),
        alt_translation_language1=altlang1 if alttrans1 else None,
        alt_translation_language2=altlang2 if alttrans2 else None,
        alt_translation1=alttrans1 if altlang1 else None,
        alt_translation2=alttrans2 if altlang2 else None)


def make_meanings(cldf_senses, entries, dictionary, metalanguages):
    """Return ORM objects for meaning descriptions."""
    return {
        cldf_sense.std['id']: make_meaning(
            cldf_sense, entries[cldf_sense.std['entryReference']], dictionary,
            metalanguages, number)
        for number, cldf_sense in enumerate(cldf_senses)
        if entry_id_exists(entries, cldf_sense.std['entryReference'])}


def make_meaning_file(meaning, md5, piece_of_media, fileinfo):
    """Create meaning--file association object."""
    jsondata = {}
    jsondata.update(fileinfo.items())
    jsondata.update(piece_of_media.items())
    return models.Meaning_files(
        id=f'{meaning.id}-{md5}',
        name=fileinfo['original'],
        object_pk=meaning.pk,
        mime_type=fileinfo['mimetype'],
        jsondata=jsondata)


def iter_meaning_files(
    cldf_senses, meanings, cldf_media, cdstar, media_order_by,
):
    """Return ORM objects associating media files with meaning descriptions."""
    sense_media_ids = {
        cldf_sense.std['id']: sorted(
            {md5
             for md5 in set(cldf_sense.std.get('mediaReference') or ())
             if md5_in_cdstar(md5, cdstar, 'Sense')},
            key=lambda md5: cldf_media[md5].get(media_order_by) or '')
        for cldf_sense in cldf_senses}
    return (
        make_meaning_file(meanings[sid], md5, cldf_media[md5], cdstar[md5])
        for sid, media_ids in sense_media_ids.items()
        for md5 in media_ids)


def iter_meaning_refs(cldf_senses, meanings, sources):
    """Return ORM objects association meaning descriptions with the bibliography."""
    for cldf_sense in cldf_senses:
        if cldf_sense.std['id'] not in meanings:
            continue
        for ref in cldf_sense.std.get('source') or ():
            source_id, context = Sources.parse(ref)
            if source_id not in sources:
                continue
            yield models.MeaningReference(
                meaning_pk=meanings[cldf_sense.std['id']].pk,
                source_pk=sources[source_id].pk,
                description=context)


def iter_meaning_data_points(
    meaning, free_fields, field_order, blacklist, labels_with_links,
):
    """Return ORM objects for arbitrary data associated with a meaning description."""
    if field_order:
        fields = {
            key: value
            for key in field_order
            if (value := free_fields.get(key))}
    else:
        fields = free_fields
    return (
        models.Meaning_data(
            object_pk=meaning.pk,
            key=key.replace('_', ' '),
            value=value,
            ord=number,
            jsondata={'with_links': key in labels_with_links})
        for number, (key, value) in enumerate(fields.items())
        if value and key not in blacklist)


def iter_meaning_data(
    cldf_senses, meanings, field_order, blacklist, labels_with_links,
):
    """Return ORM objects for arbitrary data associated with meaning descriptions."""
    existing_senses = filter(lambda s: s.std['id'] in meanings, cldf_senses)
    return (
        meaning_data
        for cldf_sense in existing_senses
        for meaning_data in iter_meaning_data_points(
            meanings[cldf_sense.std['id']], cldf_sense.free, field_order,
            blacklist, labels_with_links))


def iter_meaning_nyms(cldf_senses, meanings, entries, sense_crossrefs):
    """Return ORM objects associating meaning descriptions with dictionary entries."""
    return (
        models.Nym(
            source_pk=meanings[cldf_sense.std['id']].pk,
            target_pk=entries[ref].pk,
            description=key.replace('_', ' '))
        for cldf_sense in cldf_senses
        for key, refs in chain(cldf_sense.std.items(), cldf_sense.free.items())
        for ref in (refs if isinstance(refs, list) else [refs])
        if key in sense_crossrefs
        and key != 'entryReference'
        and entry_id_exists(entries, ref))


def example_sense_ids(cldf_example):
    """Find all sense ids in an example record.

    Yes, sometimes the sense ids are lists and sometimes they're
    a semicolon-separated strings.  It is what it is.
    """
    sense_ids = cldf_example.std.get('Sense_IDs') or ''
    if isinstance(sense_ids, str):
        return re.split(r'\s*;\s*', sense_ids)
    elif isinstance(sense_ids, list):
        return filter(None, sense_ids)
    else:
        # If this happens I messed up on the cldf side
        raise TypeError('sense id must be string or list')


def iter_example_assocs(cldf_examples, examples, meanings):
    """Return ORM objects associating examples to meaning descriptions."""
    return (
        models.MeaningSentence(
            meaning_pk=meaning.pk,
            sentence_pk=examples[cldf_example.std['id']].pk)
        for cldf_example in cldf_examples
        for mid in example_sense_ids(cldf_example)
        if (meaning := meanings.get(mid)))


def get_sense_concepticon_ids(cldf_sense):
    """Return Concepticon ids from a sense record."""
    concepts = {
        trimmed_cid
        for cid in cldf_sense.free.get('concepticonReference', '').split(';')
        if (trimmed_cid := cid.strip())}
    concepts.update(
        cid_match.group(1)
        for gloss in cldf_sense.free.get('Comparison_Meaning', '').split(';')
        if (cid_match := re.fullmatch(r'(?:[^[]*)\[(\d+)\]', gloss.strip())))
    return concepts


def get_concepticon_ids(cldf_senses, meanings):
    """Extract Concepticon ids from the sense records."""
    return {
        sense_id: get_sense_concepticon_ids(cldf_sense)
        for cldf_sense in cldf_senses
        if (sense_id := cldf_sense.std['id']) in meanings}


def make_value_sets(concepticon_ids, comparison_meanings, language, dictionary):
    """Return ORM objects associating comparison meanings to languages."""
    concept_ids = {
        concept_id
        for concepts in concepticon_ids.values()
        for concept_id in concepts
        if concept_id in comparison_meanings}
    return {
        concept_id: common.ValueSet(
            id=f'{dictionary.id}-{concept_id}',
            language_pk=language.pk,
            parameter_pk=comparison_meanings[concept_id].pk,
            contribution_pk=dictionary.pk)
        for concept_id in sorted(concept_ids)}


def iter_values(concepticon_ids, valuesets, entries, sense2word):
    """Return ORM objects associating language--concept pairs to individual words."""
    return (
        models.Counterpart(
            id=f'{valueset.id}-{sense_id}-{i}',
            valueset_pk=valueset.pk,
            word_pk=(word := entries[sense2word[sense_id]]).pk,
            name=word.name)
        for sense_id, concepts in concepticon_ids.items()
        for i, concept_id in enumerate(sorted(concepts))
        if (valueset := valuesets.get(concept_id)))


class Submission:
    """Object for loading a submission into the data base."""

    def __init__(self, sid, cldf, md, intro, cdstar):
        """Create submission.

        This constructor is usually called from `from_cldfbench`.
        """
        self.id = sid
        self.md = md
        self.props = self.md['properties']
        self.cdstar = cdstar
        self.description = intro
        self.cldf = cldf
        self.glottocode = md['language']['glottocode']

    @classmethod
    def from_cldfbench(cls, sid, data_dir):
        """Read submission information from disk."""
        cldf_dictionaries = [
            ds
            for ds in iter_datasets(data_dir / 'cldf')
            if ds.module == 'Dictionary']
        assert cldf_dictionaries, 'submission must have a cldf dictionary'
        assert len(cldf_dictionaries) == 1, 'no more than 1 dictionary per submission'
        cldf = cldf_dictionaries[0]

        with open(data_dir / 'etc' / 'md.json', encoding='utf-8') as f:
            md = json.load(f)

        intro_path = data_dir / 'raw' / 'intro.md'
        if intro_path.exists():
            with open(intro_path, encoding='utf-8') as f:
                intro = f.read()
        else:
            # XXX: do i check for None anywhere?
            intro = None

        cdstar_path = data_dir / 'etc' / 'cdstar.json'
        if cdstar_path.exists():
            with open(cdstar_path, encoding='utf-8') as f:
                cdstar = json.load(f)
        else:
            cdstar = {}

        props = md.get('properties', {})
        props['metalanguage_styles'] = {}
        for v, s in zip(
            props.get('metalanguages', {}).values(),
            ['success', 'info', 'warning', 'important'],
        ):
            props['metalanguage_styles'][v] = s
        props['custom_fields'] = [
            f'lang-{field}' if field in props['metalanguage_styles'] else field
            for field in props.get('custom_fields', ())]
        if 'second_tab' in props:
            props['second_tab'] = [
                f'lang-{field}' if field in props['metalanguage_styles'] else field
                for field in props['second_tab']]
        props.setdefault('choices', {})
        md['properties'] = props

        return cls(sid, cldf, md, intro, cdstar)

    def add_to_database(self, dictionary, language, comparison_meanings):
        """Add tables from the dictionary to the data base."""
        # read cldf data

        entry_labels = get_labels(self.props, 'entry_map')
        sense_labels = get_labels(self.props, 'sense_map')

        entry_crossrefs = get_crossref_fields(
            self.cldf, 'EntryTable', entry_labels)
        sense_crossrefs = get_crossref_fields(
            self.cldf, 'SenseTable', sense_labels)

        cldf_entries = read_cldf_entries(
            self.cldf, entry_labels,
            self.props.get('entry_custom_order'))
        cldf_senses = read_cldf_senses(
            self.cldf, sense_labels,
            self.props.get('sense_custom_order'))
        cldf_examples = read_cldf_examples(
            self.cldf, get_labels(self.props, 'example_map'),
            self.props.get('example_custom_order'))
        cldf_media = read_cldf_media(self.cldf)

        # create database objects

        sources = make_sources(self.cldf.sources, dictionary)
        DBSession.add_all(sources.values())

        entries = make_entries(
            cldf_entries, cldf_senses, cldf_examples, language, dictionary,
            self.props.get('custom_fields', ()),
            self.props.get('second_tab', ()),
            self.props.get('metalanguages', {}))
        DBSession.add_all(entries.values())

        examples = make_examples(
            cldf_examples, language, dictionary,
            self.props.get('metalanguages') or {},
            self.props.get('custom_example_fields') or {})
        DBSession.add_all(examples.values())

        DBSession.flush()

        DBSession.add_all(iter_entry_files(
            cldf_entries, cldf_media, entries, self.cdstar,
            self.props.get('media_order') or 'description'))
        DBSession.add_all(iter_entry_refs(
            cldf_entries, entries, sources))

        DBSession.add_all(iter_entry_data(
            cldf_entries, entries, self.props.get('entry_custom_order'),
            entry_crossrefs, self.props.get('process_links_in_labels') or ()))
        DBSession.add_all(iter_entry_alttranslations(
            cldf_senses, entries,
            self.props.get('metalanguages') or {}))
        DBSession.add_all(iter_entry_seealso(
            cldf_entries, entries, entry_crossrefs))

        DBSession.add_all(iter_example_files(
            cldf_examples, examples, self.cdstar))
        DBSession.add_all(iter_example_data(
            cldf_examples, examples, self.props.get('example_custom_order') or ()))
        DBSession.add_all(iter_example_refs(
            cldf_examples, examples, sources))

        meanings = make_meanings(
            cldf_senses, entries, dictionary,
            self.props.get('metalanguages') or {})
        DBSession.add_all(meanings.values())

        DBSession.flush()

        DBSession.add_all(iter_meaning_files(
            cldf_senses, meanings, cldf_media, self.cdstar,
            self.props.get('media_order') or 'description'))
        DBSession.add_all(iter_meaning_refs(
            cldf_senses, meanings, sources))
        DBSession.add_all(iter_meaning_data(
            cldf_senses, meanings, self.props.get('sense_custom_order'),
            sense_crossrefs, self.props.get('process_links_in_labels') or ()))
        DBSession.add_all(iter_meaning_nyms(
            cldf_senses, meanings, entries, sense_crossrefs))

        DBSession.add_all(iter_example_assocs(
            cldf_examples, examples, meanings))

        concepticon_ids = get_concepticon_ids(cldf_senses, meanings)
        valuesets = make_value_sets(
            concepticon_ids, comparison_meanings, language, dictionary)
        DBSession.add_all(valuesets.values())

        DBSession.flush()

        sense2word = {
            cldf_sense.std['id']: cldf_sense.std['entryReference']
            for cldf_sense in cldf_senses}
        DBSession.add_all(iter_values(
            concepticon_ids, valuesets, entries, sense2word))

        DBSession.flush()
