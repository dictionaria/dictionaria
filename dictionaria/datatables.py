"""Datatables shown on Dictionaria."""

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import joinedload

from clld.db import fts
from clld.db.meta import DBSession
from clld.db.models import common
from clld.db.models.sentence import Sentence_files
from clld.db.util import get_distinct_values, icontains
from clld.web import datatables
from clld.web.datatables.base import (
    Col, DataTable, DetailsRowLinkCol, LinkCol, LinkToMapCol, filter_number,
)
from clld.web.datatables.contribution import CitationCol, ContributorsCol
from clld.web.datatables.contributor import AddressCol, ContributionsCol, NameCol
from clld.web.datatables.language import Languages
from clld.web.datatables.sentence import Sentences, TsvCol
from clld.web.datatables.source import Sources
from clld.web.util.helpers import external_link, link
from clld.web.util.htmllib import HTML
from clld_glottologfamily_plugin.datatables import FamilyCol, MacroareaCol
from clld_glottologfamily_plugin.models import Family
from clldmpg.cdstar import MediaCol, bitstream_url, maintype

from dictionaria.models import (
    ComparisonMeaning, Counterpart, Dictionary, DictionarySource, Example,
    Variety, Word,
)
from dictionaria.util import add_word_links, concepticon_link, split


# DICTIONARIES ----------------------------------------------------------------

class NoWrapLinkCol(LinkCol):
    """Link column with line wrapping disabled."""

    def get_attrs(self, _):
        """Disable line wrapping in column."""
        return {'style': 'white-space: nowrap; font-weight: bold;'}


class DictionaryGlottocodeCol(Col):
    """Column showing a dictionary's glottocode."""

    def format(self, item):
        """Add glottolog link to glottocode."""
        item = self.get_obj(item)
        return external_link(
            f'http://glottolog.org/resource/languoid/id/{item.glottolog_id}',
            label=item.id,
            title='Language information at Glottolog')


class YearCol(Col):
    """Column for the publication year of a dictionary."""

    def format(self, item):
        """Return publication year."""
        return item.published.year


class Dictionaries(datatables.Contributions):
    """Data table for the dictionaries."""

    def base_query(self, query):
        """Build query for the data table."""
        return query.join(Variety)

    def get_options(self):
        """Set default sort order."""
        opts = super().get_options()
        opts['aaSorting'] = [[0, 'asc']]
        return opts

    def col_defs(self):
        """Define columns for the dictionaries table."""
        series = sorted(
            s
            for s, in DBSession.query(Dictionary.series).distinct()
            if s)
        series.append('--none--')
        return [
            Col(self,
                'number',
                model_col=Dictionary.number,
                input_size='mini'),
            NoWrapLinkCol(
                self,
                'dictionary',
                model_col=Dictionary.name),
            ContributorsCol(
                self,
                name='author'),
            DictionaryGlottocodeCol(
                self,
                'glottolog_id',
                sTitle='Glottocode',
                get_object=lambda i: i.language,
                model_col=Variety.glottolog_id),
            Col(self,
                'entries',
                sClass='right',
                bSearchable=False,
                input_size='mini',
                model_col=Dictionary.count_words),
            YearCol(
                self,
                'year',
                bSearchable=False,
                model_col=Dictionary.published),
            Col(self,
                'doi',
                bSearchable=False,
                bSortable=False,
                sTitle='DOI',
                format=lambda i: i.doi_link()),
            CitationCol(self, 'cite', sTitle='Cite'),
        ]


# WORDS -----------------------------------------------------------------------

class WordCol(LinkCol):
    """Column for the headword."""

    def get_attrs(self, item):
        """Add a tooltip to the word (I think (<_<)" )."""
        return {'title': item.name, 'label': item.label}

    def order(self):
        """Take homonym number into account when searching."""
        return Word.name, Word.number

    def search(self, qs):
        """Allow search with or without accents."""
        # NOTE(johannes): For a short second I thought about adding palochka
        # support here, HOWEVER:  Dictionaria requires the use of the Latin
        # alphabet for the headword column, so we ain't gonna need that.
        return or_(
            icontains(Word.name, qs),
            func.unaccent(Word.name).contains(func.unaccent(qs)))


class ConceptsCol(Col):
    """Column for linked comparison meanings from Concepticon."""

    def format(self, item):
        """Add a link to Concepticon to the cell."""
        return HTML.ul(
            *[HTML.li(HTML.span(
                link(self.dt.req, c.valueset.parameter),
                ' ',
                concepticon_link(self.dt.req, c.valueset.parameter),
            )) for c in item.counterparts],
            class_='unstyled',
        )

    def order(self):
        """Order by the concept gloss."""
        return common.Parameter.name

    def search(self, qs):
        """Handle dropdown boxes differently from manually typed search terms."""
        if getattr(self, 'choices', None):
            return common.Parameter.name == qs
        else:
            return icontains(common.Parameter.name, qs)


class DictionaryCol(Col):
    """Column for links to the dictionary page."""

    def format(self, item):
        """Add authors to the link."""
        # XXX(johannes): we don't actually do this anymore, so this class can
        # probably be removed.
        return HTML.div(
            link(self.dt.req, item.dictionary),
            # ' by ',
            # linked_contributors(self.dt.req, item.valueset.contribution)
        )


class FtsCol(DetailsRowLinkCol):
    """Details column with added full-text search."""

    __kw__ = {'bSortable': False, 'sType': 'html', 'button_text': 'more'}

    def search(self, qs):
        """Enable search using tsvectors."""
        return fts.search(self.model_col, qs)


class MeaningDescriptionCol(Col):
    """Column for the meaning description of a word."""

    def format(self, item):
        """Add links to words from inline markdown links."""
        return add_word_links(self.dt.req, item.dictionary, Col.format(self, item))


# Welcome to Unicode Hell o/
PALOCHKA = 'Ӏ'
SMALL_PALOCHKA = 'ӏ'
LATIN_I = 'I'
CYRILLIC_I = 'І'
EXCLAMATION_MARK = '!'

PALOCHKI = [PALOCHKA, SMALL_PALOCHKA, LATIN_I, CYRILLIC_I, EXCLAMATION_MARK]


def collapse_accents(sql_column):
    """Collapse accented and unaccented characters.

    This includes some palochka folding.
    """
    sql_column = func.unaccent(sql_column)
    # search for palochka using commonly-used homoglyphs or ascii replacements
    for palochka in PALOCHKI:
        sql_column = func.replace(sql_column, palochka, '1')
    return sql_column


class CustomCol(Col):
    """Default column for custom fields in the table."""

    def search(self, qs):
        """Ignore accents and palochka when searching."""
        db_column = getattr(Word, self.name)
        # collapse accented and unaccented characters
        column_norm = collapse_accents(db_column)
        query_norm = collapse_accents(qs)
        return or_(
            icontains(db_column, qs),
            column_norm.contains(query_norm))

    def order(self):
        """Ignore accents when sorting."""
        return func.unaccent(getattr(Word, self.name))


class ScientificNameCol(CustomCol):
    """Specific custom column for scientific names."""

    def format(self, item):
        """Format scientific names in italics, as it is custom."""
        return HTML.em(super().format(item))


class AltTransCol(Col):
    """Column for non-English translations of a word."""

    def __init__(self, dt, name, attrib, *args, **kwargs):
        """Construct the alternative tranlsation column.

        Note down the attribute where the translation will be found.
        """
        self._attrib = attrib
        super().__init__(dt, name, *args, **kwargs)

    def search(self, qs):
        """Ignore accents and palochka when searching."""
        column = getattr(Word, self._attrib)
        column_norm = collapse_accents(column)
        query_norm = collapse_accents(qs)
        return or_(
            icontains(column, qs),
            column_norm.contains(query_norm))

    def format(self, item):
        """Add links to words from inline markdown links."""
        value = getattr(item, self._attrib, '') or ''
        value = add_word_links(self.dt.req, item.dictionary, value)
        return HTML.p(value)

    def order(self):
        """Ignore accents when sorting."""
        column = getattr(Word, self._attrib)
        return func.unaccent(column)


class SemanticDomainCol(Col):
    """Column for semantic domains."""

    __kw__ = {'bSortable': False, 'sTitle': 'Semantic Domain'}

    def __init__(self, dt, name, semantic_domains, **kw):
        """Note down possible set of semantic domains when making the column."""
        kw['choices'] = semantic_domains
        super().__init__(dt, name, **kw)

    def search(self, qs):
        """Handle dropdown boxes differently from manually typed search terms."""
        if getattr(self, 'choices', None):
            return Word.semantic_domain == qs
        else:
            return icontains(Word.semantic_domain, qs)

    def format(self, item):
        """Put semantic domains into small caps, as is custom."""
        return HTML.ul(
            *[HTML.li(HTML.span(sd, class_='vocabulary'))
              for sd in item.semantic_domain_list], **{'class': 'unstyled'})


class ThumbnailCol(Col):
    """Column for thumbnails of media files."""

    __kw__ = {'bSearchable': False, 'bSortable': False}

    def format(self, item):
        """Show thumbnail images for media files."""
        item = self.get_obj(item)
        for f in item.iterfiles():
            if maintype(f) == 'image':
                return HTML.img(src=bitstream_url(f, type_='thumbnail'))
        return ''


class Words(datatables.Units):
    """Data table for word forms."""

    __constraints__ = [common.Language, common.Contribution, common.Parameter]

    def __init__(self, req, model, **kw):
        """Override the constructor to add some info needed for the tabs."""
        super().__init__(req, model, **kw)
        self.second_tab = kw.pop('second_tab', req.params.get('second_tab', False))
        if self.second_tab:
            self.eid = 'second_tab'
        self.vars = []
        if self.contribution:
            varnames = self.contribution.jsondata.get(
                'second_tab' if self.second_tab else 'custom_fields', [])
            for name in varnames:
                if name in self.contribution.jsondata.get('metalanguages', {}).values():
                    name = f'lang-{name}'
                self.vars.append(name)

    def toolbar(self):
        """Add a help button to the tool bar about the advanced search."""
        return HTML.a(
            'Help', class_="btn btn-warning", href=self.req.route_url('help'), target="_blank")

    def base_query(self, query):
        """Build database query for the words.

        The first tab needs load additional information to show the
        comparison meanings and file thumbnails.
        """
        if self.second_tab and self.contribution:
            query = query.filter(Word.dictionary_pk == self.contribution.pk)
            return query.distinct()
        else:
            query = query\
                .join(Dictionary)\
                .outerjoin(common.Unit_data, and_(
                    Word.pk == common.Unit_data.object_pk, common.Unit_data.key == 'ph'))\
                .outerjoin(Counterpart, Word.pk == Counterpart.word_pk)\
                .outerjoin(common.ValueSet)\
                .outerjoin(common.Parameter)\
                .options(joinedload(common.Unit._files))
            if self.contribution:
                query = query.filter(Word.dictionary_pk == self.contribution.pk)
            return query.distinct()

    def _choose_custom_column(self, name, attrib):
        if name == 'Comparison Meanings':
            return ConceptsCol(
                self, 'meaning', bSortable=False, sTitle='Comparison Meaning')
        elif name == 'Scientific Name':
            return ScientificNameCol(self, attrib, sTitle=name)
        elif name.startswith('lang-'):
            col = AltTransCol(
                self, name, attrib, sTitle=name.replace('lang-', ''))
            if self.contribution.jsondata['choices'].get(name):
                col.choices = self.contribution.jsondata['choices'][name]
            return col
        else:
            col = CustomCol(self, attrib, sTitle=name)
            if self.contribution.jsondata['choices'].get(name):
                col.choices = self.contribution.jsondata['choices'][name]
            return col

    def col_defs(self):
        """Return column definitions for the various Words tables."""
        if not self.contribution:
            return [
                WordCol(self, 'word'),
                Col(self, 'part_of_speech', model_col=Word.pos, sTitle='Part of Speech'),
                Col(self, 'description'),
                ConceptsCol(self, 'meaning', bSortable=False, sTitle='Comparison Meaning'),
                DictionaryCol(self, 'dictionary')]

        pos_tags = DBSession.query(Word.pos)\
            .filter(Word.dictionary_pk == self.contribution.pk)\
            .distinct()
        pos_choices = sorted(choice for choice, in pos_tags if choice)
        columns = [
            FtsCol(self, 'fts', sTitle='Full Entry', model_col=Word.fts),
            WordCol(self, 'word', sTitle='Headword', model_col=common.Unit.name),
            Col(self,
                'part_of_speech',
                sTitle='Part of Speech',
                model_col=Word.pos,
                choices=pos_choices,
                format=lambda i: HTML.span(i.pos or '', class_='vocabulary')),
            MeaningDescriptionCol(
                self,
                'description',
                sTitle='Meaning Description',
                model_col=common.Unit.description)]

        if self.second_tab:
            attribs = ('second_tab1', 'second_tab2', 'second_tab3')
            for name, attrib in zip(self.vars, attribs):
                columns.append(self._choose_custom_column(name, attrib))
            return columns
        else:
            attribs = ('custom_field1', 'custom_field2')
            for name, attrib in zip(self.vars, attribs):
                columns.append(self._choose_custom_column(name, attrib))
            if self.contribution.semantic_domains:
                columns.append(SemanticDomainCol(
                    self,
                    'semantic_domain',
                    split(self.contribution.semantic_domains)))
            columns.append(Col(
                self,
                'examples',
                input_size='mini',
                model_col=Word.example_count))
            if self.contribution.count_audio:
                columns.append(MediaCol(self, 'audio', 'audio', sTitle=''))
            if self.contribution.count_image:
                columns.append(ThumbnailCol(self, 'image', sTitle=''))
                # columns.append(MediaCol(self, 'image', 'image', sTitle=''))
            return columns

    def get_options(self):
        """Set up default sorting and make separate tabs work.

        (At least I think that's what the ajax magic is doing… (<_<)" )
        """
        opts = super().get_options()
        opts['aaSorting'] = [[1, 'asc']]

        for attr in ['parameter', 'contribution', 'language']:
            if getattr(self, attr):
                q = {attr: getattr(self, attr).id}
                if attr == 'contribution' and self.second_tab:
                    q['second_tab'] = '1'
                opts['sAjaxSource'] = self.req.route_url('units', _query=q)

        return opts


# EXAMPLES --------------------------------------------------------------------

class Examples(Sentences):
    """Data table for examples."""

    __constraints__ = [Dictionary]

    def toolbar(self):
        """Add a help button to the tool bar about the advanced search."""
        return HTML.a(
            'Help', class_="btn btn-warning", href=self.req.route_url('help'), target="_blank")

    def base_query(self, query):
        """Build query for example table."""
        query = query \
            .outerjoin(
                Sentence_files,
                and_(
                    Sentence_files.object_pk == common.Sentence.pk,
                    Sentence_files.mime_type.contains('audio/'))) \
            .options(joinedload(common.Sentence._files))

        if self.dictionary:
            query = query.filter(Example.dictionary_pk == self.dictionary.pk)
        else:
            query = query.join(Dictionary).options(joinedload(Example.dictionary))

        return query

    def col_defs(self):
        """Define columns for the example table."""
        res = [
            LinkCol(self, 'name', sTitle='Primary Text', sClass="object-language"),
            TsvCol(self, 'analyzed', sTitle='Analyzed Text'),
            TsvCol(self, 'gloss', sClass="gloss"),
            Col(self,
                'description',
                sTitle=self.req.translate('Translation'),
                sClass="translation"),
        ]
        if self.dictionary and self.dictionary.count_example_audio:
            res.append(MediaCol(self, 'exaudio', 'audio', sTitle=''))
        res.append(DetailsRowLinkCol(self, 'd', button_text='show', sTitle='IGT'))
        if not self.dictionary:
            res.insert(-1, LinkCol(
                self,
                'dictionary',
                model_col=Dictionary.name,
                get_obj=lambda i: i.dictionary,
                choices=get_distinct_values(Dictionary.name)))
        return res

    def get_options(self):
        """Reset default order in example table."""
        return {'aaSorting': []}


# SOURCES ---------------------------------------------------------------------

class DictionarySources(Sources):
    """Data table for the bibliography of a dictionary ."""

    __constraints__ = [Dictionary]

    def base_query(self, query):
        """Build data base query for the bibliography."""
        if self.dictionary:
            query = query.filter(DictionarySource.dictionary_pk == self.dictionary.pk)
        else:
            query = query.join(Dictionary).options(joinedload(DictionarySource.dictionary))
        return query


# DICTIONARY AUTHORS ----------------------------------------------------------

class DictionaryContributors(DataTable):
    """Data table for dictionary authors."""

    def base_query(self, _):
        """Build data base query for dictionary authors."""
        return DBSession.query(common.Contributor) \
            .join(common.ContributionContributor) \
            .join(common.Contribution)

    def col_defs(self):
        """Define columns for the author table."""
        return [
            NameCol(self, 'name'),
            ContributionsCol(self, 'Contributions'),
            AddressCol(self, 'address', sTitle='Affiliation'),
        ]


# LANGUAGES -------------------------------------------------------------------

class LanguageGlottocodeCol(Col):
    """Column for showing the glottocode of a language."""

    def format(self, item):
        """Add link to glottolog to the cell."""
        item = self.get_obj(item)
        return external_link(
            f'http://glottolog.org/resource/languoid/id/{item.id}',
            label=item.id,
            title='Language information at Glottolog')


class Varieties(Languages):
    """Data table for languages.

    TBH barely anyone ever looks at this.  Since the mapping of dictionaries
    to languages is almost 1:1 the `Dictionaries` table tends to be just
    as informative for most purposes.
    """

    def base_query(self, query):
        """Return data base query for filling the language table."""
        return query.outerjoin(Family)

    def col_defs(self):
        """Return column definitions for the language table."""
        return [
            LinkCol(self, 'name'),
            LanguageGlottocodeCol(self, 'id', sTitle='Glottocode'),
            LinkToMapCol(self, 'm'),
            Col(self,
                'latitude',
                sDescription='<small>The geographic latitude</small>'),
            Col(self,
                'longitude',
                sDescription='<small>The geographic longitude</small>'),
            MacroareaCol(self, 'macroarea', Variety),
            FamilyCol(self, 'family', Variety),
        ]


# COMPARISON MEANINGS ---------------------------------------------------------

class SingleConceptCol(LinkCol):
    """Column for a single comparison meaning."""

    def get_attrs(self, item):
        """Add a tooltip to the cell."""
        return {'label': item.name}


class ValueCountCol(Col):
    """Column for the number of words for a comparison meaning."""

    def format(self, item):
        """Show number of words for a comparison meaning."""
        return item.representation

    def order(self):
        """Sort comparison meanings by the number of associated words."""
        return ComparisonMeaning.representation

    def search(self, qs):
        """Enable advanced number search."""
        # XXX(johannes): Is the advanced number search documented anywhere?
        return filter_number(ComparisonMeaning.representation, qs)


class ConcepticonLinkCol(Col):
    """Column linking to the Concepticon."""

    __kw__ = {'bSearchable': False, 'bSortable': False}

    def format(self, item):
        """Show link to concepticon."""
        return concepticon_link(self.dt.req, item)


class ComparisonMeanings(datatables.Parameters):
    """Data table for Concepticon concepts."""

    def col_defs(self):
        """Define columns for the comparison meanings table."""
        return [
            # IdsCodeCol2(self, 'code'),
            # LinkCol(self, 'name'),
            # Col(self, 'description'),
            SingleConceptCol(self, 'name', sTitle='Comparison Meaning'),
            ValueCountCol(
                self, 'representation', sClass='right'),
            ConcepticonLinkCol(self, 'concepticon', sTitle=''),
        ]


# VALUES ----------------------------------------------------------------------

class ValueWordCol(LinkCol):
    """Column linking to a word associated to a comparison meaning."""

    def get_obj(self, item):
        """Return the word."""
        return item.word

    def search(self, qs):
        """Search by the word."""
        return icontains(Word.name, qs)


class Values(datatables.Values):
    """Data table of comparison meanings associated with specific words."""

    def base_query(self, query):
        """Build query for the value table."""
        query = super().base_query(query)
        return query.join(Counterpart.word)

    def col_defs(self):
        """Define columns for the value table."""
        if self.parameter:
            return [
                LinkCol(self, 'language', model_col=common.Language.name, get_object=lambda v: v.valueset.language),
                ValueWordCol(self, 'word', model_col=Word.name, get_object=lambda v: v.word),
                Col(self, 'description', model_col=Word.description, get_object=lambda v: v.word),
                LinkToMapCol(self, 'm', get_object=lambda v: v.valueset.language),
            ]
        else:
            return [
                ValueWordCol(self, 'word', model_col=Word.name, get_object=lambda v: v.word),
                Col(self, 'description', model_col=Word.description, get_object=lambda v: v.word),
            ]


def includeme(config):
    """Do pyramid's mighty metaprogramming magic."""
    config.register_datatable('sentences', Examples)
    config.register_datatable('units', Words)
    config.register_datatable('values', Values)
    config.register_datatable('languages', Varieties)
    config.register_datatable('parameters', ComparisonMeanings)
    config.register_datatable('contributions', Dictionaries)
    config.register_datatable('sources', DictionarySources)
    config.register_datatable('contributors', DictionaryContributors)
