from pyramid.config import Configurator

from clld import interfaces

from clld_glottologfamily_plugin.util import LanguageByFamilyMapMarker

# we must make sure custom models are known at database initialization!
from dictionaria import models
from dictionaria import md

_ = lambda s: s
_('Parameter')
_('Parameters')
_('Sentence')
_('Sentences')
_('Contributor')
_('Contributors')
_('Contribution')
_('Contributions')


def link_attrs(req, obj, **kw):
    if interfaces.IUnitValue.providedBy(obj):
        kw['href'] = req.route_url('unit', id=obj.unit.id, **kw.pop('url_kw', {}))
    return kw


class MyMapMarker(LanguageByFamilyMapMarker):
    def get_icon(self, ctx, req):
        if interfaces.IValue.providedBy(ctx):
            ctx = ctx.valueset.language
        if interfaces.IValueSet.providedBy(ctx):
            ctx = ctx.language
        return LanguageByFamilyMapMarker.get_icon(self, ctx, req)


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    config = Configurator(settings=settings)
    config.registry.registerUtility(link_attrs, interfaces.ILinkAttrs)
    config.include('clldmpg')
    config.include('clld_glottologfamily_plugin')
    config.registry.registerUtility(MyMapMarker(), interfaces.IMapMarker)
    config.add_page('submit')
    config.add_settings(home_comp=['submit'] + config.get_settings()['home_comp'])

    for cls in [md.BibTex, md.ReferenceManager]:
        for if_ in [interfaces.IRepresentation, interfaces.IMetadata]:
            config.register_adapter(cls, interfaces.IContribution, if_, name=cls.mimetype)

    return config.make_wsgi_app()
