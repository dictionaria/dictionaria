from __future__ import unicode_literals

from collections import OrderedDict

from sqlalchemy import and_, or_, func
from sqlalchemy.orm import joinedload_all, joinedload, aliased

from clld.web import datatables
from clld.web.datatables.base import (
    DataTable, LinkToMapCol, Col, LinkCol, IdCol, filter_number, DetailsRowLinkCol,
)
from clld.web.datatables.contributor import NameCol, ContributionsCol, AddressCol
from clld.web.datatables.language import Languages
from clld.web.datatables.sentence import Sentences, TsvCol
from clld.web.datatables.source import Sources
from clld.web.datatables import unitvalue
from clld.db.meta import DBSession
from clld.db.models import common
from clld.db.util import icontains, get_distinct_values, collkey
from clld.db import fts
from clld.web.util.helpers import link, external_link
from clld.web.util.htmllib import HTML
from clld_glottologfamily_plugin.models import Family
from clld_glottologfamily_plugin.datatables import MacroareaCol, FamilyCol
from clldmpg.cdstar import MediaCol, maintype, bitstream_url

from dictionaria.models import (
    Word, Counterpart, Dictionary, ComparisonMeaning, Variety, Example,
    DictionarySource,
)
from dictionaria.util import concepticon_link, split, add_unit_links


class GlottocodeCol(Col):
    def format(self, item):
        return external_link(
            'http://glottolog.org/resource/languoid/id/' + item.id,
            label=item.id,
            title='Language information at Glottolog')


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
        return icontains(common.Parameter.name, qs)


class WowLanguageCol(LinkCol):
    def get_obj(self, item):
        return item.valueset.language


class DictionaryCol(Col):
    def format(self, item):
        return HTML.div(
            link(self.dt.req, item.dictionary),
            #' by ',
            #linked_contributors(self.dt.req, item.valueset.contribution)
        )


class WordCol(LinkCol):
    def get_attrs(self, item):
        return dict(title=item.name, label=item.label)

    def order(self):
        return collkey(Word.name), Word.number

    def search(self, qs):
        return or_(
            icontains(Word.name, qs),
            func.unaccent(Word.name).contains(func.unaccent(qs)))


class CustomCol(Col):
    def search(self, qs):
        return icontains(self.dt.vars[self.name].value, qs)

    def format(self, item):
        return HTML.p(item.datadict().get(self.name, ''))

    def order(self):
        return self.dt.vars[self.name].value


class SemanticDomainCol(Col):
    __kw__ = dict(bSortable=False, sTitle='semantic domain')

    def __init__(self, dt, name, sds, **kw):
        kw['choices'] = sds
        Col.__init__(self, dt, name, **kw)

    def search(self, qs):
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
            if not self.contribution:
                raise ValueError
            self.eid = 'second_tab'
        self.vars = OrderedDict()
        if self.contribution:
            for name in self.contribution.jsondata.get(
                    'second_tab' if self.second_tab else 'custom_fields', []):
                if name in self.contribution.jsondata.get('metalanguages', {}).values():
                    name = 'lang-{0}'.format(name)
                self.vars[name] = aliased(common.Unit_data, name=name)

    def base_query(self, query):
        if self.second_tab:
            query = query.filter(Word.dictionary_pk == self.contribution.pk) \
                .options(joinedload(common.Unit.data))
            for name, var in self.vars.items():
                query = query.outerjoin(var, and_(var.key == name, var.object_pk == Word.pk))
            return query.distinct()

        query = query.join(Dictionary)\
            .outerjoin(common.Unit_data, and_(
                Word.pk == common.Unit_data.object_pk, common.Unit_data.key == 'ph'))\
            .outerjoin(Counterpart, Word.pk == Counterpart.word_pk)\
            .outerjoin(common.ValueSet)\
            .outerjoin(common.Parameter)\
            .options(
                joinedload(common.Unit.data),
                joinedload(common.Unit._files),
            )
        if self.contribution:
            for name, var in self.vars.items():
                query = query.outerjoin(var, and_(var.key == name, var.object_pk == Word.pk))
            query = query.filter(Word.dictionary_pk == self.contribution.pk)

        return query.distinct()

    def col_defs(self):
        poscol = Col(self, 'part_of_speech', model_col=Word.pos)
        if self.contribution:
            pos = sorted((c for c, in DBSession.query(Word.pos)
                         .filter(Word.dictionary_pk == self.contribution.pk)
                         .distinct() if c))
            res = [
                FtsCol(self, 'fts', sTitle='full entry', model_col=Word.fts),
                WordCol(self, 'word', sTitle='headword', model_col=common.Unit.name),
                Col(self,
                    'part_of_speech',
                    sTitle='part of speech',
                    model_col=Word.pos,
                    choices=pos,
                    format=lambda i: HTML.span(i.pos or '', class_='vocabulary')),
                MeaningDescriptionCol2(self,
                    'description',
                    sTitle='meaning description',
                    model_col=common.Unit.description),
            ]
            if self.second_tab:
                for name in self.vars:
                    res.append(CustomCol(self, name, sTitle=name.replace('lang-', '')))
                return res
            else:
                res.append(Col(self,
                    'examples',
                    input_size='mini',
                    model_col=Word.example_count))
            if self.contribution.semantic_domains:
                res.append(SemanticDomainCol(self, 'semantic_domain', split(self.contribution.semantic_domains)))
            if self.contribution.count_audio:
                res.append(MediaCol(self, 'audio', 'audio', sTitle=''))
            if self.contribution.count_image:
                res.append(ThumbnailCol(self, 'image', sTitle=''))
                #res.append(MediaCol(self, 'image', 'image', sTitle=''))
            for name in self.vars:
                col = CustomCol(self, name, sTitle=name.replace('lang-', ''))
                if name in self.contribution.jsondata['choices']:
                    col.choices = self.contribution.jsondata['choices'][name]
                res.append(col)
            return res
        return [
            WordCol(self, 'word'),
            poscol,
            Col(self, 'description'),
            MeaningsCol(self, 'meaning', bSortable=False, sTitle='Comparison meaning'),
            DictionaryCol(self, 'dictionary'),
        ]

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


#----------------------

#class IdsCodeCol2(IdsCodeCol):
#    def get_attrs(self, item):
#        return dict(label=item.ids_code)
#
#    def get_obj(self, item):
#        return item


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
            #IdsCodeCol2(self, 'code'),
            #LinkCol(self, 'name'),
            MeaningDescriptionCol(self, 'name', sTitle='comparison meaning'),
            #Col(self, 'description', sTitle='description'),
            RepresentationCol(
                self, 'representation', sTitle='representation', sClass='right'),
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


class Dictionaries(datatables.Contributions):
    def get_options(self):
        opts = super(Dictionaries, self).get_options()
        opts['aaSorting'] = [[0, 'asc']]
        return opts

    def col_defs(self):
        from clld.web.datatables.contribution import ContributorsCol, CitationCol
        return [
            Col(self,
                'number',
                sTitle='number',
                model_col=Dictionary.number,
                input_size='mini'),
            LinkCol(
                self,
                'dictionary',
                sTitle='dictionary'),
            ContributorsCol(
                self,
                name='author',
                sTitle='author'),
            Col(self,
                'entries',
                sTitle='entries',
                sClass='right',
                model_col=Dictionary.count_words),
            YearCol(
                self,
                'year',
                bSearchable=False,
                sTitle='year',
                model_col=Dictionary.published),
            CitationCol(self, 'cite', sTitle='cite'),
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
            NameCol(self, 'name', sTitle='name'),
            ContributionsCol(self, 'Contributions', sTitle='contributions'),
            AddressCol(self, 'address', sTitle='affiliation'),
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
            LinkCol(self, 'name', sTitle='primary text', sClass="object-language"),
            TsvCol(self, 'analyzed', sTitle='analyzed text'),
            TsvCol(self, 'gloss', sTitle='gloss', sClass="gloss"),
            Col(self,
                'description',
                sTitle=self.req.translate('translation'),
                sClass="translation"),
            DetailsRowLinkCol(self, 'd', button_text='show', sTitle='IGT'),
        ]
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
