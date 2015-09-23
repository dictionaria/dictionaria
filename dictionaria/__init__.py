from pyramid.config import Configurator

from clld.interfaces import ILinkAttrs, IUnitValue, IValue, IValueSet, IMapMarker
from clld_glottologfamily_plugin.util import LanguageByFamilyMapMarker

# we must make sure custom models are known at database initialization!
from dictionaria import models


_ = lambda s: s
_('Parameter')
_('Parameters')


def link_attrs(req, obj, **kw):
    if IUnitValue.providedBy(obj):
        kw['href'] = req.route_url('unit', id=obj.unit.id, **kw.pop('url_kw', {}))
    return kw


class MyMapMarker(LanguageByFamilyMapMarker):
    def get_icon(self, ctx, req):
        if IValue.providedBy(ctx):
            ctx = ctx.valueset.language
        if IValueSet.providedBy(ctx):
            ctx = ctx.language
        return LanguageByFamilyMapMarker.get_icon(self, ctx, req)


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    config = Configurator(settings=settings)
    config.registry.registerUtility(link_attrs, ILinkAttrs)
    config.include('clldmpg')
    config.include('clld_glottologfamily_plugin')
    config.registry.registerUtility(MyMapMarker(), IMapMarker)
    return config.make_wsgi_app()
