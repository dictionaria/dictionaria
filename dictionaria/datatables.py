from sqlalchemy import and_, or_, func
from sqlalchemy.orm import joinedload

from clld.web import datatables
from clld.web.datatables.base import (
    DataTable, LinkToMapCol, Col, LinkCol, filter_number, DetailsRowLinkCol,
)
from clld.web.datatables.contributor import NameCol, ContributionsCol, AddressCol
from clld.web.datatables.language import Languages
from clld.web.datatables.sentence import Sentences, TsvCol
from clld.web.datatables.source import Sources
from clld.web.datatables import unitvalue
from clld.db.meta import DBSession
from clld.db.models import common
from clld.db.util import icontains, get_distinct_values
from clld.db import fts
from clld.web.util.helpers import link, external_link
from clld.web.util.htmllib import HTML
from clld_glottologfamily_plugin.models import Family
from clld_glottologfamily_plugin.datatables import MacroareaCol, FamilyCol
from clldmpg.cdstar import MediaCol, maintype, bitstream_url
from clldutils.misc import slug

from dictionaria.models import (
    Word, Counterpart, Dictionary, ComparisonMeaning, Variety, Example,
    DictionarySource,
)
from dictionaria.util import concepticon_link, split, add_unit_links


class GlottocodeCol(Col):
    def format(self, item):
        item = self.get_obj(item)
        return external_link(
            'http://glottolog.org/resource/languoid/id/' + item.id,
            label=item.id,
            title='Language information at Glottolog')


# GlottocodeCol doesn't work in the contributions table
class GlottologIdCol(Col):
    def format(self, item):
        item = self.get_obj(item)
        return external_link(
            'http://glottolog.org/resource/languoid/id/' + item.glottolog_id,
            label=item.id,
            title='Language information at Glottolog')


class SeriesCol(Col):
    def format(self, item):
        item = self.get_obj(item)
        if item.series:
            return '<span class="series-{}"><nobr>{}</nobr></span>'.format(
                slug(item.series),
                item.series)
        else:
            return ''


class Varieties(Languages):
    def base_query(self, query):
        return query.outerjoin(Family)

    def col_defs(self):
        return [
            LinkCol(self, 'name'),
            GlottocodeCol(self, 'id', sTitle='Glottocode'),
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


class MeaningsCol(Col):
    def format(self, item):
        return HTML.ul(
            *[HTML.li(HTML.span(
                link(self.dt.req, c.valueset.parameter),
                ' ',
                concepticon_link(self.dt.req, c.valueset.parameter)
            )) for c in item.counterparts],
            class_='unstyled'
        )

    def order(self):
        return common.Parameter.name

    def search(self, qs):
        if getattr(self, 'choices', None):
            return common.Parameter.name == qs
        else:
            return icontains(common.Parameter.name, qs)


class WowLanguageCol(LinkCol):
    def get_obj(self, item):
        return item.valueset.language


class DictionaryCol(Col):
    def format(self, item):
        return HTML.div(
            link(self.dt.req, item.dictionary),
            # ' by ',
            # linked_contributors(self.dt.req, item.valueset.contribution)
        )


class WordCol(LinkCol):
    def get_attrs(self, item):
        return dict(title=item.name, label=item.label)

    def order(self):
        return Word.name, Word.number

    def search(self, qs):
        return or_(
            icontains(Word.name, qs),
            func.unaccent(Word.name).contains(func.unaccent(qs)))


# Welcome to Unicode Hell o/
PALOCHKA = 'Ӏ'
SMALL_PALOCHKA = 'ӏ'
LATIN_I = 'I'
CYRILLIC_I = 'І'


def collapse_accents(sql_column):
    """Collapse accented and unaccented characters."""
    sql_column = func.unaccent(sql_column)
    # allow searching for palochka using the number 1
    for palochka in (PALOCHKA, SMALL_PALOCHKA, LATIN_I, CYRILLIC_I):
        sql_column = func.replace(sql_column, palochka, '1')
    return sql_column


class AltTransCol(Col):
    def __init__(self, dt, name, attrib, *args, **kwargs):
        self._attrib = attrib
        super().__init__(dt, name, *args, **kwargs)

    def search(self, qs):
        column = getattr(Word, self._attrib)
        column_norm = collapse_accents(column)
        query_norm = collapse_accents(qs)
        return or_(
            icontains(column, qs),
            column_norm.contains(query_norm))

    def format(self, item):
        value = getattr(item, self._attrib, '') or ''
        value = add_unit_links(self.dt.req, item.dictionary, value)
        return HTML.p(value)

    def order(self):
        column = getattr(Word, self._attrib)
        return func.unaccent(column)


class CustomCol(Col):

    def search(self, qs):
        db_column = getattr(Word, self.name)
        # collapse accented and unaccented characters
        column_norm = collapse_accents(db_column)
        query_norm = collapse_accents(qs)
        return or_(
            icontains(db_column, qs),
            column_norm.contains(query_norm))

    def order(self):
        return func.unaccent(getattr(Word, self.name))


class ScientificNameCol(CustomCol):

    def format(self, item):
        return HTML.em(super().format(item))


class SemanticDomainCol(Col):
    __kw__ = dict(bSortable=False, sTitle='Semantic Domain')

    def __init__(self, dt, name, sds, **kw):
        kw['choices'] = sds
        Col.__init__(self, dt, name, **kw)

    def search(self, qs):
        if getattr(self, 'choices', None):
            return Word.semantic_domain == qs
        else:
            return icontains(Word.semantic_domain, qs)

    def format(self, item):
        return HTML.ul(
            *[HTML.li(HTML.span(sd, class_='vocabulary'))
              for sd in item.semantic_domain_list], **{'class': 'unstyled'})


class ThumbnailCol(Col):
    __kw__ = dict(bSearchable=False, bSortable=False)

    def format(self, item):
        item = self.get_obj(item)
        for f in item.iterfiles():
            if maintype(f) == 'image':
                return HTML.img(src=bitstream_url(f, type_='thumbnail'))
        return ''


class FtsCol(DetailsRowLinkCol):
    __kw__ = dict(bSortable=False, sType='html', button_text='more')

    def search(self, qs):
        return fts.search(self.model_col, qs)


class MeaningDescriptionCol2(Col):
    def format(self, item):
        return add_unit_links(self.dt.req, item.dictionary, Col.format(self, item))


class Words(datatables.Units):
    __constraints__ = [common.Language, common.Contribution, common.Parameter]

    def __init__(self, req, model, **kw):
        datatables.Units.__init__(self, req, model, **kw)
        self.second_tab = kw.pop('second_tab', req.params.get('second_tab', False))
        if self.second_tab:
            self.eid = 'second_tab'
        self.vars = []
        if self.contribution:
            for name in self.contribution.jsondata.get(
                    'second_tab' if self.second_tab else 'custom_fields', []):
                if name in self.contribution.jsondata.get('metalanguages', {}).values():
                    name = 'lang-{0}'.format(name)
                self.vars.append(name)

    def toolbar(self):
        return HTML.a(
            'Help', class_="btn btn-warning", href=self.req.route_url('help'), target="_blank")

    def base_query(self, query):
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
            return MeaningsCol(
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
        if not self.contribution:
            return [
                WordCol(self, 'word'),
                Col(self, 'part_of_speech', model_col=Word.pos, sTitle='Part of Speech'),
                Col(self, 'description'),
                MeaningsCol(self, 'meaning', bSortable=False, sTitle='Comparison Meaning'),
                DictionaryCol(self, 'dictionary')]

        pos_choices = sorted(
            choice
            for choice, in DBSession.query(Word.pos)
                .filter(Word.dictionary_pk == self.contribution.pk)
                .distinct()
            if choice)
        columns = [
            FtsCol(self, 'fts', sTitle='Full Entry', model_col=Word.fts),
            WordCol(self, 'word', sTitle='Headword', model_col=common.Unit.name),
            Col(self,
                'part_of_speech',
                sTitle='Part of Speech',
                model_col=Word.pos,
                choices=pos_choices,
                format=lambda i: HTML.span(i.pos or '', class_='vocabulary')),
            MeaningDescriptionCol2(
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
                columns.append(SemanticDomainCol(self, 'semantic_domain', split(self.contribution.semantic_domains)))
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
        opts = DataTable.get_options(self)
        opts['aaSorting'] = [[1, 'asc']]

        for attr in ['parameter', 'contribution', 'language']:
            if getattr(self, attr):
                q = {attr: getattr(self, attr).id}
                if attr == 'contribution' and self.second_tab:
                    q['second_tab'] = '1'
                opts['sAjaxSource'] = self.req.route_url('units', _query=q)

        return opts


# ----------------------

# class IdsCodeCol2(IdsCodeCol):
#     def get_attrs(self, item):
#         return dict(label=item.ids_code)
#
#     def get_obj(self, item):
#         return item


class MeaningDescriptionCol(LinkCol):
    def get_attrs(self, item):
        return dict(label=item.name)


class RepresentationCol(Col):
    def format(self, item):
        return item.representation

    def order(self):
        return ComparisonMeaning.representation

    def search(self, qs):
        return filter_number(ComparisonMeaning.representation, qs)


class ConcepticonLinkCol(Col):
    __kw__ = {'bSearchable': False, 'bSortable': False}

    def format(self, item):
        return concepticon_link(self.dt.req, item)


class Meanings(datatables.Parameters):
    def col_defs(self):
        return [
            # IdsCodeCol2(self, 'code'),
            # LinkCol(self, 'name'),
            MeaningDescriptionCol(self, 'name', sTitle='Comparison Meaning'),
            # Col(self, 'description'),
            RepresentationCol(
                self, 'representation', sClass='right'),
            ConcepticonLinkCol(self, 'concepticon', sTitle=''),
        ]

# Values --------------------------------------------------------------------------------


class ValueCol(LinkCol):
    def get_obj(self, item):
        return item.word

    def search(self, qs):
        return icontains(Word.name, qs)


class Values(datatables.Values):
    def base_query(self, query):
        query = datatables.Values.base_query(self, query)
        return query.join(Counterpart.word)

    def col_defs(self):
        if self.parameter:
            return [
                LinkCol(self, 'language', model_col=common.Language.name, get_object=lambda v: v.valueset.language),
                ValueCol(self, 'word', model_col=Word.name, get_object=lambda v: v.word),
                Col(self, 'description', model_col=Word.description, get_object=lambda v: v.word),
                LinkToMapCol(self, 'm', get_object=lambda v: v.valueset.language),
            ]
        return [
            ValueCol(self, 'word', model_col=Word.name, get_object=lambda v: v.word),
            Col(self, 'description', model_col=Word.description, get_object=lambda v: v.word),
        ]

# Dictionaries


class YearCol(Col):
    def format(self, item):
        return item.published.year


class NoWrapLinkCol(LinkCol):
    def get_attrs(self, item):
        return {'style': 'white-space: nowrap; font-weight: bold;'}


class Dictionaries(datatables.Contributions):
    def base_query(self, query):
        return query.join(Variety)

    def get_options(self):
        opts = super(Dictionaries, self).get_options()
        opts['aaSorting'] = [[0, 'asc']]
        return opts

    def col_defs(self):
        from clld.web.datatables.contribution import ContributorsCol, CitationCol
        series = sorted(
            s for s, in DBSession.query(Dictionary.series).distinct())
        return [
            Col(self,
                'number',
                model_col=Dictionary.number,
                input_size='mini'),
            SeriesCol(
                self, 'series', model_col=Dictionary.series, choices=series),
            NoWrapLinkCol(
                self,
                'dictionary',
                model_col=Dictionary.name),
            ContributorsCol(
                self,
                name='author'),
            GlottologIdCol(
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


class Unitvalues(unitvalue.Unitvalues):
    def base_query(self, query):
        return super(Unitvalues, self).base_query(query).join(
            Dictionary, Dictionary.pk == Word.dictionary_pk)

    def col_defs(self):
        name_col = unitvalue.UnitValueNameCol(self, 'value')
        if self.unitparameter and self.unitparameter.domain:
            name_col.choices = sorted([de.name for de in self.unitparameter.domain])
        return [
            name_col,
            LinkCol(self, 'word', get_object=lambda i: i.unit, model_col=common.Unit.name),
            LinkCol(self, 'dictionary', get_object=lambda i: i.unit.dictionary, model_col=Dictionary.name),
        ]


class DictionaryContributors(DataTable):
    def base_query(self, query):
        return DBSession.query(common.Contributor) \
            .join(common.ContributionContributor) \
            .join(common.Contribution)

    def col_defs(self):
        return [
            NameCol(self, 'name'),
            ContributionsCol(self, 'Contributions'),
            AddressCol(self, 'address', sTitle='Affiliation'),
        ]


class DictionarySources(Sources):
    __constraints__ = [Dictionary]

    def base_query(self, query):
        if self.dictionary:
            query = query.filter(DictionarySource.dictionary_pk == self.dictionary.pk)
        else:
            query = query.join(Dictionary).options(joinedload(DictionarySource.dictionary))

        return query


class Examples(Sentences):
    __constraints__ = [Dictionary]

    def toolbar(self):
        return HTML.a(
            'Help', class_="btn btn-warning", href=self.req.route_url('help'), target="_blank")

    def base_query(self, query):
        from clld.db.models.sentence import Sentence_files
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
        return {'aaSorting': []}


def includeme(config):
    config.register_datatable('sentences', Examples)
    config.register_datatable('units', Words)
    config.register_datatable('values', Values)
    config.register_datatable('unitvalues', Unitvalues)
    config.register_datatable('languages', Varieties)
    config.register_datatable('parameters', Meanings)
    config.register_datatable('contributions', Dictionaries)
    config.register_datatable('sources', DictionarySources)
    config.register_datatable('contributors', DictionaryContributors)
