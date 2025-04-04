"""Adapters for overriding clld functionality."""

from clld import interfaces
from clld.web.adapters.md import BibTex


class DictionaryBibTex(BibTex):
    """Bibtex Entry that uses the DOI from the data base."""

    def rec(self, ctx, req):
        """Add the doi from the data base object to the bibtex entry."""
        # res = BibTex.rec(self, ctx, req)
        res = super().rec(ctx, req)
        if ctx.doi:
            res['doi'] = ctx.doi
        return res


def includeme(config):
    """Do pyramid's mighty metaprogramming magic."""
    config.register_adapter(
        DictionaryBibTex, interfaces.IContribution, interfaces.IRepresentation)
    config.register_adapter(
        DictionaryBibTex, interfaces.IContribution, interfaces.IMetadata)
