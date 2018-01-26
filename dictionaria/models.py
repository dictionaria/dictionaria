from __future__ import unicode_literals
from itertools import groupby

from zope.interface import implementer
from sqlalchemy import (
    Column,
    Unicode,
    Integer,
    ForeignKey,
    Date,
    Boolean,
    func,
)
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.dialects.postgresql import TSVECTOR

from clld import interfaces
from clld.db.meta import Base, CustomModelMixin
from clld.db.models import common
from clld.web.util.htmllib import HTML
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
    count_image = Column(Integer)
    semantic_domains = Column(Unicode)

    def metalanguage_label(self, lang):
        style = self.jsondata['metalanguage_styles'].get(lang)
        style = "label label-{0}".format(style) if style else lang
        return HTML.span(lang, class_=style)


@implementer(interfaces.IParameter)
class ComparisonMeaning(CustomModelMixin, common.Parameter):
    pk = Column(Integer, ForeignKey('parameter.pk'), primary_key=True)
    concepticon_url = Column(Unicode)
    representation = Column(Integer)


@implementer(interfaces.IUnit)
class Word(CustomModelMixin, common.Unit):
    """Words are units of a particular language, but are still considered part of a
    dictionary, i.e. part of a contribution.
    """
    pk = Column(Integer, ForeignKey('unit.pk'), primary_key=True)
    semantic_domain = Column(Unicode)
    comparison_meanings = Column(Unicode)
    phonetic = Column(Unicode)
    #script = Column(Unicode)
    #borrowed = Column(Unicode)
    fts = Column(TSVECTOR)
    serialized = Column(Unicode)

    # original ...?

    # the concatenated values for the UnitParameter part of speech is stored denormalized.
    pos = Column(Unicode)

    dictionary_pk = Column(Integer, ForeignKey('dictionary.pk'))
    dictionary = relationship(Dictionary, backref='words')
    number = Column(Integer, default=0)  # for disambiguation of words with the same name
    example_count = Column(Integer, default=0)

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
    def description_list(self):
        return split(self.description)

    @property
    def comparison_meanings_list(self):
        return split(self.comparison_meanings)

    @property
    def semantic_domain_list(self):
        return split(self.semantic_domain)


class WordReference(Base, common.HasSourceMixin):
    word_pk = Column(Integer, ForeignKey('word.pk'))
    word = relationship(Word, backref="references")


RELATIONS = {
    'main entry': 'subentry',
    'synonym': '(part of) synonym (for)',
    'antonym': '(part of) antonym (for)',
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


class Meaning(Base, common.HasFilesMixin, common.IdNameDescriptionMixin):
    word_pk = Column(Integer, ForeignKey('word.pk'))
    ord = Column(Integer, default=1)
    gloss = Column(Unicode)
    language = Column(Unicode, default='en')
    semantic_domain = Column(Unicode)
    reverse = Column(Unicode)
    alt_translation1 = Column(Unicode)
    alt_translation_language1 = Column(Unicode)
    alt_translation2 = Column(Unicode)
    alt_translation_language2 = Column(Unicode)

    @declared_attr
    def word(cls):
        return relationship(Word, backref=backref('meanings', order_by=[cls.ord]))

    @property
    def reverse_list(self):
        return split(self.reverse or '')

    @property
    def semantic_domain_list(self):
        if self.semantic_domain:
            return split(self.semantic_domain)
        return []


#
# FIXME: need relations between senses as well!
#


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
