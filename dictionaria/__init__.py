from pyramid.config import Configurator

from clld.interfaces import ILinkAttrs, IUnitValue

# we must make sure custom models are known at database initialization!
from dictionaria import models
from dictionaria.interfaces import ISemanticDomain


_ = lambda s: s
_('Parameter')
_('Parameters')


def link_attrs(req, obj, **kw):
    if IUnitValue.providedBy(obj):
        kw['href'] = req.route_url('unit', id=obj.unit.id, **kw.pop('url_kw', {}))
    return kw


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    config = Configurator(settings=settings)
    config.registry.registerUtility(link_attrs, ILinkAttrs)
    config.include('clldmpg')
    config.register_resource('semanticdomain', models.SemanticDomain, ISemanticDomain)
    return config.make_wsgi_app()
