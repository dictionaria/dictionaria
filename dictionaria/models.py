from zope.interface import implementer
from sqlalchemy import (
    Column,
    String,
    Unicode,
    Integer,
    ForeignKey,
    Date,
)
from sqlalchemy.orm import relationship

from clld import interfaces
from clld.db.meta import Base, CustomModelMixin
from clld.db.models import common

from dictionaria.interfaces import ISemanticDomain


@implementer(ISemanticDomain)
class SemanticDomain(Base, common.IdNameDescriptionMixin):
    pass


@implementer(interfaces.IContribution)
class Dictionary(CustomModelMixin, common.Contribution):
    """Contributions in WOW are dictionaries which are always related to one language.
    """
    pk = Column(Integer, ForeignKey('contribution.pk'), primary_key=True)
    language_pk = Column(Integer, ForeignKey('language.pk'))
    language = relationship('Language', backref='dictionaries')
    published = Column(Date)


@implementer(interfaces.IParameter)
class Meaning(CustomModelMixin, common.Parameter):
    pk = Column(Integer, ForeignKey('parameter.pk'), primary_key=True)

    semantic_domain_pk = Column(Integer, ForeignKey('semanticdomain.pk'))
    semantic_domain = relationship(SemanticDomain, backref='meanings')

    semantic_category = Column(Unicode)

    ids_code = Column(String)
    representation = Column(Integer)


@implementer(interfaces.IUnit)
class Word(CustomModelMixin, common.Unit):
    """Words are units of a particular language, but are still considered part of a
    dictionary, i.e. part of a contribution.
    """
    pk = Column(Integer, ForeignKey('unit.pk'), primary_key=True)
    phonetic = Column(Unicode)
    #script = Column(Unicode)
    #borrowed = Column(Unicode)

    # the concatenated values for the UnitParameter part of speech is stored denormalized.
    pos = Column(Unicode)

    dictionary_pk = Column(Integer, ForeignKey('dictionary.pk'))
    dictionary = relationship(Dictionary, backref='words')
    number = Column(Integer, default=0)  # for disambiguation of words with the same name

    @property
    def linked_from(self):
        return [w.source for w in self.source_assocs]

    @property
    def links_to(self):
        return [w.target for w in self.target_assocs]


class SeeAlso(Base):
    source_pk = Column(Integer, ForeignKey('word.pk'))
    target_pk = Column(Integer, ForeignKey('word.pk'))
    description = Column(Unicode())

    source = relationship(Word, foreign_keys=[source_pk], backref='target_assocs')
    target = relationship(Word, foreign_keys=[target_pk], backref='source_assocs')


class WordSentence(Base):
    word_pk = Column(Integer, ForeignKey('word.pk'))
    sentence_pk = Column(Integer, ForeignKey('sentence.pk'))
    description = Column(Unicode())

    word = relationship(Word, backref='sentence_assocs')
    sentence = relationship(
        common.Sentence, backref='word_assocs', order_by=common.Sentence.id)


@implementer(interfaces.IValue)
class Counterpart(CustomModelMixin, common.Value):
    """Counterparts relate a word to a meaning, i.e. they are the values for meaning
    parameters.
    """
    pk = Column(Integer, ForeignKey('value.pk'), primary_key=True)

    word_pk = Column(Integer, ForeignKey('word.pk'))
    word = relationship(Word, backref='counterparts')
