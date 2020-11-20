from itertools import chain, groupby
from collections import defaultdict

from zope.interface import implementer
from sqlalchemy import (
    Column,
    Unicode,
    Integer,
    ForeignKey,
    Date,
)
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.dialects.postgresql import TSVECTOR

from clld import interfaces
from clld.db.meta import Base, CustomModelMixin
from clld.db.models import common
from clld.web.util.htmllib import HTML
from clld.web.util.helpers import external_link
from clld_glottologfamily_plugin.models import HasFamilyMixin

from dictionaria.util import split


@implementer(interfaces.ILanguage)
class Variety(CustomModelMixin, common.Language, HasFamilyMixin):
    pk = Column(Integer, ForeignKey('language.pk'), primary_key=True)


@implementer(interfaces.IContribution)
class Dictionary(CustomModelMixin, common.Contribution):
    """Contributions in WOW are dictionaries which are always related to one language.
    """
    pk = Column(Integer, ForeignKey('contribution.pk'), primary_key=True)
    language_pk = Column(Integer, ForeignKey('language.pk'))
    language = relationship('Language', backref='dictionaries')
    number = Column(Integer)
    published = Column(Date)
    count_words = Column(Integer)
    count_audio = Column(Integer)
    count_example_audio = Column(Integer)
    count_image = Column(Integer)
    semantic_domains = Column(Unicode)
    toc = Column(Unicode)
    doi = Column(Unicode)

    def metalanguage_label(self, lang):
        style = self.jsondata['metalanguage_styles'].get(lang)
        style = "label label-{0}".format(style) if style else lang
        return HTML.span(lang, class_=style)

    def doi_link(self):
        if self.doi:
            return external_link(
                'https://doi.org/{0.doi}'.format(self), label='DOI: {0.doi}'.format(self))
        return ''


@implementer(interfaces.IParameter)
class ComparisonMeaning(CustomModelMixin, common.Parameter):
    pk = Column(Integer, ForeignKey('parameter.pk'), primary_key=True)
    concepticon_url = Column(Unicode)
    representation = Column(Integer)


class SourcesForDataMixin(object):
    @property
    def sourcedict(self):
        res = defaultdict(list)
        for ref in self.references:
            res[ref.description].append(ref.source)
        return res


@implementer(interfaces.IUnit)
class Word(CustomModelMixin, common.Unit, SourcesForDataMixin):
    """Words are units of a particular language, but are still considered part of a
    dictionary, i.e. part of a contribution.
    """
    pk = Column(Integer, ForeignKey('unit.pk'), primary_key=True)
    semantic_domain = Column(Unicode)
    fts = Column(TSVECTOR)
    serialized = Column(Unicode)

    # original ...?

    # the concatenated values for the UnitParameter part of speech is stored denormalized.
    pos = Column(Unicode)

    dictionary_pk = Column(Integer, ForeignKey('dictionary.pk'))
    dictionary = relationship(Dictionary, backref='words')
    number = Column(Integer, default=0)  # for disambiguation of words with the same name
    example_count = Column(Integer, default=0)

    custom_field1 = Column(Unicode)
    custom_field2 = Column(Unicode)
    second_tab1 = Column(Unicode)
    second_tab2 = Column(Unicode)
    second_tab3 = Column(Unicode)

    def iterfiles(self):
        for file in self._files:
            yield file
        for meaning in self.meanings:
            for file in meaning._files:
                yield file

    @property
    def label(self):
        args = [self.name]
        if self.number:
            args.append(HTML.sup('{0}'.format(self.number)))
        return HTML.span(*args, **{'class': 'lemma'})

    @property
    def linked_from(self):
        for desc, assocs in groupby(
                sorted(self.source_assocs, key=lambda a: a.ord),
                lambda s: s.description):
            yield RELATIONS.get(desc, desc), [a.source for a in assocs]

    @property
    def links_to(self):
        for desc, assocs in groupby(
                sorted(self.target_assocs, key=lambda a: a.ord),
                lambda s: s.description):
            yield desc, [a.target for a in assocs]

    @property
    def iterrelations(self):
        to_assocs = sorted(self.target_assocs, key=lambda a: a.ord)
        links_to = [
            (ta.description, ta.target)
            for ta in to_assocs]
        target_ids = {
            target.id
            for _, target in links_to}

        from_assocs = sorted(self.source_assocs, key=lambda a: a.ord)
        links_from = [
            (RELATIONS.get(sa.description, sa.description), sa.source)
            for sa in from_assocs
            if sa.source.id not in target_ids]

        for desc, pairs in groupby(
            chain(links_to, links_from),
            lambda pair: pair[0]
        ):
            yield desc, [link for _, link in pairs]


    @property
    def description_list(self):
        return split(self.description)

    @property
    def semantic_domain_list(self):
        return split(self.semantic_domain)


class WordReference(Base, common.HasSourceMixin):
    word_pk = Column(Integer, ForeignKey('word.pk'))
    word = relationship(Word, backref="references")


RELATIONS = {
    'Main Entry': 'Subentry',
    'Synonym': '(Part of) Synonym (for)',
    'Antonym': '(Part of) Antonym (for)',
    'Contains': 'Is Part of',
}


class SeeAlso(Base):
    source_pk = Column(Integer, ForeignKey('word.pk'))
    target_pk = Column(Integer, ForeignKey('word.pk'))
    description = Column(Unicode())
    ord = Column(Integer, default=1)

    source = relationship(Word, foreign_keys=[source_pk], backref='target_assocs')
    target = relationship(Word, foreign_keys=[target_pk], backref='source_assocs')


class Meaning_files(Base, common.FilesMixin):
    pass


class Meaning_data(Base, common.DataMixin):
    pass


class Meaning(Base, common.HasFilesMixin, common.HasDataMixin, common.IdNameDescriptionMixin, SourcesForDataMixin):
    word_pk = Column(Integer, ForeignKey('word.pk'))
    ord = Column(Integer, default=1)
    gloss = Column(Unicode)
    language = Column(Unicode, default='en')
    semantic_domain = Column(Unicode)
    alt_translation1 = Column(Unicode)
    alt_translation_language1 = Column(Unicode)
    alt_translation2 = Column(Unicode)
    alt_translation_language2 = Column(Unicode)

    @declared_attr
    def word(cls):
        return relationship(Word, backref=backref('meanings', order_by=[cls.ord]))

    @property
    def semantic_domain_list(self):
        if self.semantic_domain:
            return split(self.semantic_domain)
        return []

    @property
    def related(self):
        for desc, assocs in groupby(
                sorted(self.nyms, key=lambda a: a.description),
                lambda s: s.description):
            yield RELATIONS.get(desc, desc), [a.target for a in assocs]


class MeaningReference(Base, common.HasSourceMixin):
    meaning_pk = Column(Integer, ForeignKey('meaning.pk'))
    meaning = relationship(Meaning, backref="references")


class Nym(Base):
    source_pk = Column(Integer, ForeignKey('meaning.pk'))
    target_pk = Column(Integer, ForeignKey('word.pk'))
    description = Column(Unicode())
    ord = Column(Integer, default=1)

    source = relationship(Meaning, foreign_keys=[source_pk], backref='nyms')
    target = relationship(Word, foreign_keys=[target_pk])


class MeaningSentence(Base):
    meaning_pk = Column(Integer, ForeignKey('meaning.pk'))
    sentence_pk = Column(Integer, ForeignKey('sentence.pk'))
    description = Column(Unicode())

    meaning = relationship(Meaning, backref='sentence_assocs')
    sentence = relationship(
        common.Sentence, backref='meaning_assocs', order_by=common.Sentence.id)


@implementer(interfaces.IValue)
class Counterpart(CustomModelMixin, common.Value):
    """Counterparts relate a word to a meaning, i.e. they are the values for meaning
    parameters.
    """
    pk = Column(Integer, ForeignKey('value.pk'), primary_key=True)

    word_pk = Column(Integer, ForeignKey('word.pk'))
    word = relationship(Word, backref='counterparts')


@implementer(interfaces.ISentence)
class Example(CustomModelMixin, common.Sentence):
    pk = Column(Integer, ForeignKey('sentence.pk'), primary_key=True)
    number = Column(Integer)
    alt_translation1 = Column(Unicode)
    alt_translation_language1 = Column(Unicode)
    alt_translation2 = Column(Unicode)
    alt_translation_language2 = Column(Unicode)
    serialized = Column(Unicode)
    dictionary_pk = Column(Integer, ForeignKey('dictionary.pk'))
    dictionary = relationship(Dictionary, backref='examples')


@implementer(interfaces.ISource)
class DictionarySource(CustomModelMixin, common.Source):
    pk = Column(Integer, ForeignKey('source.pk'), primary_key=True)
    dictionary_pk = Column(Integer, ForeignKey('dictionary.pk'))
    dictionary = relationship(Dictionary, backref='sources')
