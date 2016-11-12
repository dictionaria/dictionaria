from collections import OrderedDict

from sqlalchemy import and_
from sqlalchemy.orm import joinedload_all, joinedload, aliased

from clld.web import datatables
from clld.web.datatables.base import (
    DataTable, LinkToMapCol, Col, LinkCol, IdCol, filter_number,
)
from clld.web.datatables.contributor import Contributors
from clld.web.datatables.language import Languages
from clld.web.datatables import unitvalue
from clld.db.meta import DBSession
from clld.db.models import common
from clld.db.util import icontains, get_distinct_values
from clld.web.util.helpers import link, linked_contributors, icon
from clld.web.util.htmllib import HTML
from clld_glottologfamily_plugin.models import Family
from clld_glottologfamily_plugin.datatables import MacroareaCol, FamilyCol
from clldmpg.cdstar import MediaCol

from dictionaria.models import Word, Counterpart, Dictionary, ComparisonMeaning, Variety
from dictionaria.util import concepticon_link


class LanguageIdCol(LinkCol):
    def get_attrs(self, item):
        return dict(label=item.id)


class Varieties(Languages):
    def base_query(self, query):
        return query.outerjoin(Family)

    def col_defs(self):
        return [
            LanguageIdCol(self, 'id'),
            LinkCol(self, 'name'),
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
        attrs = dict(title=item.name)
        if not item.number:
            attrs['label'] = HTML.span(item.name, class_='lemma')
        else:
            attrs['label'] = HTML.span(
                item.name, HTML.sup(str(item.number)), class_='lemma')
        return attrs

    def order(self):
        return Word.name, Word.number

    def search(self, qs):
        return icontains(Word.name, qs)


class CustomCol(Col):
    def search(self, qs):
        return icontains(self.dt.vars[self.name].value, qs)

    def format(self, item):
        return item.datadict().get(self.name, '')

    def order(self):
        return self.dt.vars[self.name].value


class Words(datatables.Units):
    __constraints__ = [common.Language, common.Contribution, common.Parameter]

    def __init__(self, req, model, **kw):
        datatables.Units.__init__(self, req, model, **kw)
        self.vars = OrderedDict()
        if self.contribution:
            for name in self.contribution.jsondata.get('custom_fields', []):
                self.vars[name] = aliased(common.Unit_data, name=name)

    def base_query(self, query):
        query = query.join(Dictionary)\
            .outerjoin(common.Unit_data, and_(
                Word.pk == common.Unit_data.object_pk, common.Unit_data.key == 'ph'))\
            .outerjoin(Counterpart, Word.pk == Counterpart.word_pk)\
            .outerjoin(common.ValueSet)\
            .outerjoin(common.Parameter)\
            .options(
                joinedload_all(
                    Word.counterparts, common.Value.valueset, common.ValueSet.parameter),
                joinedload(common.Unit.data),
                joinedload(common.Unit._files))
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
                WordCol(self, 'word', model_col=common.Unit.name),
                Col(self, 'part_of_speech', model_col=Word.pos, choices=pos),
                Col(self, 'description', model_col=common.Unit.description),
                MeaningsCol(self, 'meaning', sTitle='Comparison meaning'),
                MediaCol(self, 'audio', 'audio'),
                MediaCol(self, 'image', 'image'),
                #CustomCol(self, 'custom'),
            ]
            for name in self.vars:
                res.append(CustomCol(self, name))
            return res
        return [
            WordCol(self, 'word'),
            poscol,
            Col(self, 'description'),
            MeaningsCol(self, 'meaning', bSortable=False, sTitle='Comparison meaning'),
            DictionaryCol(self, 'dictionary'),
        ]

        #if self.contribution:
        #    return [
        #        WordCol(self, 'word'),
        #        Col(self, 'description')
        #        MeaningsCol(self, 'meaning')]
        #
        #if self.parameter:
        #    return [
        #        WordCol(self, 'word'),
        #        WowLanguageCol(self, 'language'),
        #        DictionaryCol(self, 'dictionary'),
        #    ]
        #
        #return [
        #    WordCol(self, 'word'),
        #    Col(self, 'description'),
        #    MeaningsCol(self, 'meaning')]

    def toolbar(self):
        return ''

    def get_options(self):
        opts = DataTable.get_options(self)

        for attr in ['parameter', 'contribution', 'language']:
            if getattr(self, attr):
                opts['sAjaxSource'] = self.req.route_url(
                    'units', _query={attr: getattr(self, attr).id})

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
        return filter_number(ComparisonMeaning.representation)


class ConcepticonLinkCol(Col):
    __kw__ = {'bSearchable': False, 'bSortable': False}

    def format(self, item):
        return concepticon_link(self.dt.req, item)


class Meanings(datatables.Parameters):
    def col_defs(self):
        return [
            #IdsCodeCol2(self, 'code'),
            #LinkCol(self, 'name'),
            MeaningDescriptionCol(self, 'name', sTitle='Comparison meaning'),
            Col(self, 'description'),
            ConcepticonLinkCol(self, 'concepticon', sTitle=''),
            RepresentationCol(self, 'representation', sClass='right')]

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
        opts['aaSorting'] = [[0, 'desc']]
        return opts

    def col_defs(self):
        from clld.web.datatables.contribution import ContributorsCol, CitationCol
        return [
            LinkCol(self, 'dictionary'),
            ContributorsCol(self, name='author'),
            Col(self, 'entries', sClass='right', model_col=Dictionary.count_words),
            YearCol(self, 'year', bSearchable=False, model_col=Dictionary.published),
            CitationCol(self, 'cite'),
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


class DictionaryContributors(Contributors):
    def base_query(self, query):
        return DBSession.query(common.Contributor) \
            .join(common.ContributionContributor) \
            .join(common.Contribution)


def includeme(config):
    config.register_datatable('units', Words)
    config.register_datatable('values', Values)
    config.register_datatable('unitvalues', Unitvalues)
    config.register_datatable('languages', Varieties)
    config.register_datatable('parameters', Meanings)
    config.register_datatable('contributions', Dictionaries)
    config.register_datatable('contributors', DictionaryContributors)
