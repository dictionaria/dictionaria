from clld import interfaces
from clld.web.adapters.md import BibTex


class DictionaryBibTex(BibTex):
    def rec(self, ctx, req):
        res = BibTex.rec(self, ctx, req)
        if ctx.doi:
            res['doi'] = ctx.doi
        return res


def includeme(config):
    for if_ in [interfaces.IRepresentation, interfaces.IMetadata]:
        config.register_adapter(DictionaryBibTex, interfaces.IContribution, if_)
