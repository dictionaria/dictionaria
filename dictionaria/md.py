# coding: utf8
from __future__ import unicode_literals, print_function, division
from itertools import chain

from zope.interface import implementer

from clld import interfaces
from clld.web.adapters.md import MetadataFromRec as Base
from clld.lib import bibtex


class MetadataFromRec(Base):
    def rec(self, ctx, req):
        """
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
            '{0}-{1}'.format(req.dataset.id, ctx.id),
            author=[
                c.name for c in
                chain(ctx.primary_contributors, ctx.secondary_contributors)],
            title=getattr(ctx, 'citation_name', ctx.__unicode__()),
            url=req.resource_url(ctx),
            journal=req.dataset.name,
            number='{0}'.format(ctx.number),
            pages='1-{0}'.format(len(ctx.words)),
            address=req.dataset.publisher_place,
            publisher=req.dataset.publisher_name,
            year='{0}'.format(ctx.published.year))


@implementer(interfaces.IRepresentation, interfaces.IMetadata)
class BibTex(MetadataFromRec):

    """Resource metadata as BibTex record."""

    name = 'BibTeX'
    __label__ = 'BibTeX'
    unapi = 'bibtex'
    extension = 'md.bib'
    mimetype = 'text/x-bibtex'

    def render(self, ctx, req):
        return self.rec(ctx, req).__unicode__()


@implementer(interfaces.IRepresentation, interfaces.IMetadata)
class ReferenceManager(MetadataFromRec):

    """Resource metadata in RIS format."""

    name = 'RIS'
    __label__ = 'RIS'
    unapi = 'ris'
    extension = 'md.ris'
    mimetype = "application/x-research-info-systems"

    def render(self, ctx, req):
        return self.rec(ctx, req).format('ris')
