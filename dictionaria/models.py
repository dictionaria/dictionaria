"""Definitions for data base objects."""

import re
from collections import defaultdict
from itertools import chain, groupby

from sqlalchemy import Column, Date, ForeignKey, Integer, Unicode
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import backref, relationship
from zope.interface import implementer

from clld import interfaces
from clld.db.meta import Base, CustomModelMixin
from clld.db.models import common
from clld.web.util.doi import url as doi_url
from clld.web.util.helpers import external_link
from clld.web.util.htmllib import HTML
from clld_glottologfamily_plugin.models import HasFamilyMixin

from dictionaria.util import split


@implementer(interfaces.ILanguage)
class Variety(CustomModelMixin, common.Language, HasFamilyMixin):
    """Dictionaria-specific Language."""

    pk = Column(Integer, ForeignKey('language.pk'), primary_key=True)
    glottolog_id = Column(Unicode)


@implementer(interfaces.IContribution)
class Dictionary(CustomModelMixin, common.Contribution):
    """A contribution to dictionaria."""

    pk = Column(Integer, ForeignKey('contribution.pk'), primary_key=True)
    language_pk = Column(Integer, ForeignKey('language.pk'))
    language = relationship('Language', backref='dictionaries')
    series = Column(Unicode)
    number = Column(Integer)
    published = Column(Date)
    count_words = Column(Integer)
    count_audio = Column(Integer)
    count_example_audio = Column(Integer)
    count_image = Column(Integer)
    semantic_domains = Column(Unicode)
    toc = Column(Unicode)
    git_repo = Column(Unicode)
    doi = Column(Unicode)

    def doi_link(self):
        """Return HTML render of a DOI link."""
        if self.doi:
            return external_link(doi_url(self), label=f'DOI: {self.doi}')
        else:
            return ''

    def git_link(self):
        """Return HTML render of link to a git repo."""
        if self.git_repo:
            github_match = re.fullmatch(
                r'.*github\.com/([^/]*)/([^/]*)/?', self.git_repo)
            if github_match:
                label = 'Github: {}/{}'.format(*github_match.groups())
            else:
                label = self.git_repo
            return external_link(self.git_repo, label=label)
        else:
            return ''


@implementer(interfaces.IParameter)
class ComparisonMeaning(CustomModelMixin, common.Parameter):
    """Comparison meaning as defined in Concepticon."""

    pk = Column(Integer, ForeignKey('parameter.pk'), primary_key=True)
    concepticon_url = Column(Unicode)
    representation = Column(Integer)


class SourcesForDataMixin:
    """Helper class for accessing associated sources."""

    @property
    def sourcedict(self):
        """Return citations mapped to source objects."""
        res = defaultdict(list)
        for ref in self.references:
            res[ref.description].append(ref.source)
        return res


@implementer(interfaces.IUnit)
class Word(CustomModelMixin, common.Unit, SourcesForDataMixin):
    """Words are units of a particular language.

    At the same time  are they're still considered part of a specific
    contribution.
    """

    pk = Column(Integer, ForeignKey('unit.pk'), primary_key=True)
    semantic_domain = Column(Unicode)
    fts = Column(TSVECTOR)

    pos = Column(Unicode)

    dictionary_pk = Column(Integer, ForeignKey('dictionary.pk'))
    dictionary = relationship(Dictionary, backref='words')
    # for disambiguating of homonyms
    number = Column(Integer, default=0)
    example_count = Column(Integer, default=0)

    custom_field1 = Column(Unicode)
    custom_field2 = Column(Unicode)
    second_tab1 = Column(Unicode)
    second_tab2 = Column(Unicode)
    second_tab3 = Column(Unicode)

    def iterfiles(self):
        """Return all files associated with this word."""
        yield from self._files
        for meaning in self.meanings:
            yield from meaning._files

    @property
    def label(self):
        """Return HTML representation of the headword."""
        args = [self.name]
        if self.number:
            args.append(HTML.sup(str(self.number)))
        return HTML.span(*args, **{'class': 'lemma'})

    @property
    def iterrelations(self):
        """Return related entries.

        I.e. cross-referenced entries and entries cross-referencing `self`.
        """
        # note: add 0/1 to tuples to sort references before back-references
        links_to = [
            (ta.description, 0, ta.ord, ta.target)
            for ta in self.target_assocs]
        target_ids = {t[3].id for t in links_to}

        links_from = [
            (
                RELATIONS.get(sa.description, sa.description),
                1,
                sa.ord,
                sa.source,
            )
            for sa in self.source_assocs
            if sa.source.id not in target_ids]

        links = sorted(
            chain(links_to, links_from),
            key=lambda t: t[:3])
        for desc, tuples in groupby(links, lambda t: t[0]):
            yield desc, [t[3] for t in tuples]

    @property
    def description_list(self):
        """Return description as a list.

        This just splits the property, so we don't have do the roundtrip to
        the data base.
        """
        return split(self.description)

    @property
    def semantic_domain_list(self):
        """Return semantic domains as a list.

        This just splits the property, so we don't have do the roundtrip to
        the data base.
        """
        return split(self.semantic_domain)


class WordReference(Base, common.HasSourceMixin):
    """Association of a word with a bibliographical source."""

    word_pk = Column(Integer, ForeignKey('word.pk'))
    word = relationship(Word, backref="references")


RELATIONS = {
    'Main Entry': 'Subentry',
    'Synonym': '(Part of) Synonym (for)',
    'Antonym': '(Part of) Antonym (for)',
    'Contains': 'Is Part of',
}


class SeeAlso(Base):
    """Association of entries with other entries (i.e. cross-references)."""

    source_pk = Column(Integer, ForeignKey('word.pk'))
    target_pk = Column(Integer, ForeignKey('word.pk'))
    description = Column(Unicode())
    ord = Column(Integer, default=1)

    source = relationship(Word, foreign_keys=[source_pk], backref='target_assocs')
    target = relationship(Word, foreign_keys=[target_pk], backref='source_assocs')


class Meaning_files(Base, common.FilesMixin):
    """Association media files with meaning descriptions."""


class Meaning_data(Base, common.DataMixin):
    """Association media files with arbitrary data."""


class Meaning(Base, common.HasFilesMixin, common.HasDataMixin, common.IdNameDescriptionMixin, SourcesForDataMixin):
    """Meaning description of a word."""

    word_pk = Column(Integer, ForeignKey('word.pk'))
    ord = Column(Integer, default=1)
    gloss = Column(Unicode)
    semantic_domain = Column(Unicode)
    alt_translation1 = Column(Unicode)
    alt_translation_language1 = Column(Unicode)
    alt_translation2 = Column(Unicode)
    alt_translation_language2 = Column(Unicode)

    @declared_attr
    def word(cls):
        """Return associated entry."""
        return relationship(Word, backref=backref('meanings', order_by=[cls.ord]))

    @property
    def semantic_domain_list(self):
        """Return list of semantic domains."""
        if self.semantic_domain:
            return split(self.semantic_domain)
        else:
            return []

    @property
    def related(self):
        """Iterate over related entries."""
        for desc, assocs in groupby(
                sorted(self.nyms, key=lambda a: a.description),
                lambda s: s.description):
            yield RELATIONS.get(desc, desc), [a.target for a in assocs]


class MeaningReference(Base, common.HasSourceMixin):
    """Association of a meaning description to a source."""

    meaning_pk = Column(Integer, ForeignKey('meaning.pk'))
    meaning = relationship(Meaning, backref="references")


class Nym(Base):
    """Reference of a meaning descriptions to an entries."""

    source_pk = Column(Integer, ForeignKey('meaning.pk'))
    target_pk = Column(Integer, ForeignKey('word.pk'))
    description = Column(Unicode())
    ord = Column(Integer, default=1)

    source = relationship(Meaning, foreign_keys=[source_pk], backref='nyms')
    target = relationship(Word, foreign_keys=[target_pk])


class MeaningSentence(Base):
    """Association of examples to meaning descriptions."""

    meaning_pk = Column(Integer, ForeignKey('meaning.pk'))
    sentence_pk = Column(Integer, ForeignKey('sentence.pk'))
    description = Column(Unicode())

    meaning = relationship(Meaning, backref='sentence_assocs')
    sentence = relationship(
        common.Sentence, backref='meaning_assocs', order_by=common.Sentence.id)


@implementer(interfaces.IValue)
class Counterpart(CustomModelMixin, common.Value):
    """Associations of a comparison meaning to an entry.

    I.e. they are the 'values' for comparison meaning 'parameters'.
    """

    pk = Column(Integer, ForeignKey('value.pk'), primary_key=True)
    word_pk = Column(Integer, ForeignKey('word.pk'))
    word = relationship(Word, backref='counterparts')


@implementer(interfaces.ISentence)
class Example(CustomModelMixin, common.Sentence):
    """Example sentence for Dictionaria."""

    pk = Column(Integer, ForeignKey('sentence.pk'), primary_key=True)
    number = Column(Integer)
    alt_translation1 = Column(Unicode)
    alt_translation_language1 = Column(Unicode)
    alt_translation2 = Column(Unicode)
    alt_translation_language2 = Column(Unicode)
    dictionary_pk = Column(Integer, ForeignKey('dictionary.pk'))
    dictionary = relationship(Dictionary, backref='examples')


@implementer(interfaces.ISource)
class DictionarySource(CustomModelMixin, common.Source):
    """Association of a bibliographical source to a dictionary."""

    pk = Column(Integer, ForeignKey('source.pk'), primary_key=True)
    dictionary_pk = Column(Integer, ForeignKey('dictionary.pk'))
    dictionary = relationship(Dictionary, backref='sources')
