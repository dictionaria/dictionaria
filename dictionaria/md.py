"""Adapters for retrieving meta data for resources in different formats."""

from itertools import chain

from zope.interface import implementer

from clld import interfaces
from clld.lib import bibtex
from clld.web.adapters.md import MetadataFromRec as Base

from dictionaria.util import last_first


class MetadataFromRec(Base):
    """Resource metadata -- base case.  Defaults to bibtex."""

    def rec(self, ctx, req):
        """Create bibtex record of a dictionary.

        @article{dictionaria-daakaka,
            author    = {von Prince, Kilu},
            journal = {Dictionaria},
            number = {1},
            pages = {1-2175},
            doi = {00.0000/clld.2017.00.0.000},
            issn = {0000-0000},
        }
        """
        if not interfaces.IContribution.providedBy(ctx):
            return Base.rec(self, ctx, req)

        return bibtex.Record(
            'article',
            f'{req.dataset.id}-{ctx.id}',
            author=[
                last_first(c) for c in
                chain(ctx.primary_contributors, ctx.secondary_contributors)],
            title=getattr(ctx, 'citation_name', str(ctx)),
            url=req.resource_url(ctx),
            journal=req.dataset.name,
            number=str(ctx.number),
            pages=f'1-{len(ctx.words)}',
            address=req.dataset.publisher_place,
            publisher=req.dataset.publisher_name,
            year=str(ctx.published.year))


@implementer(interfaces.IRepresentation, interfaces.IMetadata)
class BibTex(MetadataFromRec):
    """Resource metadata as BibTex record."""

    name = 'BibTeX'
    __label__ = 'BibTeX'
    unapi = 'bibtex'
    extension = 'md.bib'
    mimetype = 'text/x-bibtex'

    def render(self, ctx, req):
        """Render metadata to bibtex."""
        return str(self.rec(ctx, req))


@implementer(interfaces.IRepresentation, interfaces.IMetadata)
class ReferenceManager(MetadataFromRec):
    """Resource metadata in RIS format."""

    name = 'RIS'
    __label__ = 'RIS'
    unapi = 'ris'
    extension = 'md.ris'
    mimetype = "application/x-research-info-systems"

    def render(self, ctx, req):
        """Render metadata to RIS."""
        return self.rec(ctx, req).format('ris')
