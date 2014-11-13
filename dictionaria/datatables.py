from sqlalchemy import and_
from sqlalchemy.sql.expression import cast
from sqlalchemy.types import Integer, Float
from sqlalchemy.orm import joinedload_all, joinedload

from clld.web import datatables
from clld.web.datatables.base import (
    DataTable, LinkToMapCol, Col, LinkCol, IdCol, filter_number,
)
from clld.web.datatables.contributor import Contributors
from clld.web.datatables import unitvalue
from clld.db.meta import DBSession
from clld.db.models import common
from clld.db.util import icontains, get_distinct_values
from clld.web.util.helpers import link, linked_contributors
from clld.web.util.htmllib import HTML

from dictionaria.models import Word, Counterpart, Meaning, Dictionary, SemanticDomain


class MeaningsCol(Col):
    def format(self, item):
        return HTML.ul(
            *[HTML.li(link(self.dt.req, c.valueset.parameter)) for c in item.counterparts],
            class_='unstyled'
        )

    def order(self):
        return common.Parameter.id

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
        return dict(
            label=item.name if not item.number
            else HTML.span(item.name, HTML.sup(str(item.number))))

    def order(self):
        return Word.name, Word.number

    def search(self, qs):
        return icontains(Word.name, qs)


class CustomCol(Col):
    #
    # TODO: pull relevant key from dictionary config!
    #
    def format(self, item):
        return item.datadict().get('ph')

    def order(self, ):
        return common.Unit_data.value

    def search(self, qs):
        return icontains(common.Unit_data.value, qs)


class Words(datatables.Units):
    __constraints__ = [common.Language, common.Contribution, common.Parameter]

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
                joinedload(common.Unit.data))
        if self.contribution:
            query = query.filter(Word.dictionary_pk == self.contribution.pk)
        return query.distinct()

    def col_defs(self):
        poscol = Col(self, 'part_of_speech', model_col=Word.pos)
        poscol.choices = [
            r[0] for r in DBSession.query(common.UnitDomainElement.name)\
            .join(common.UnitParameter)\
            .filter(common.UnitParameter.id == 'pos')]

        if self.contribution:
            return [
                WordCol(self, 'word', model_col=common.Unit.name),
                Col(self, 'description', model_col=common.Unit.description),
                Col(self, 'phonetic', model_col=Word.phonetic),
                MeaningsCol(self, 'meaning'),
                poscol,
                #CustomCol(self, 'custom'),
            ]
        return [
            WordCol(self, 'word'),
            Col(self, 'description'),
            MeaningsCol(self, 'meaning', bSortable=False),
            poscol,
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


class SemanticDomainCol(LinkCol):
    def get_obj(self, item):
        return item.semantic_domain

    def search(self, qs):
        return icontains(SemanticDomain.name, qs)

    def order(self):
        return cast(SemanticDomain.id, Integer)


class RepresentationCol(Col):
    def format(self, item):
        return item.representation

    def order(self):
        return Meaning.representation

    def search(self, qs):
        return filter_number(Meaning.representation)


class Meanings(datatables.Parameters):
    def base_query(self, query):
        return query.join(SemanticDomain).options(joinedload(Meaning.semantic_domain))

    def col_defs(self):
        return [
            #IdsCodeCol2(self, 'code'),
            #LinkCol(self, 'name'),
            MeaningDescriptionCol(self, 'description', sTitle='Comparison meaning'),
            SemanticDomainCol(self, 'semantic_domain', choices=get_distinct_values(SemanticDomain.name)),
            RepresentationCol(self, 'representation', sClass='right')]

# Values --------------------------------------------------------------------------------


class ValueCol(LinkCol):
    def get_obj(self, item):
        return item.word


class Values(datatables.Values):
    def col_defs(self):
        from clld.web.datatables.value import RefsCol

        return [
            LinkCol(self, 'language', model_col=common.Language.name, get_object=lambda v: v.valueset.language),
            LinkCol(self, 'word', model_col=Word.name, get_object=lambda v: v.word),
            Col(self, 'description', model_col=Word.description, get_object=lambda v: v.word),
            LinkToMapCol(self, 'm', get_object=lambda v: v.valueset.language),
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
    config.register_datatable('parameters', Meanings)
    config.register_datatable('contributions', Dictionaries)
    config.register_datatable('contributors', DictionaryContributors)
