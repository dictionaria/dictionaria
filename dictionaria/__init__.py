"""Basic setup for the Dictionaria webapp."""

from functools import partial

from pyramid.config import Configurator

from clld import interfaces
from clld.web.app import menu_item
from clld_glottologfamily_plugin.util import LanguageByFamilyMapMarker

# we must make sure custom models are known at database initialization!
from dictionaria import md

_ = lambda s: s  # noqa
_('Parameter')
_('Parameters')
_('Sentence')
_('Sentences')
_('Contributor')
_('Contributors')
_('Contribution')
_('Contributions')


def link_attrs(req, obj, **kw):
    # XXX(johannes): what does that actually do...?
    if interfaces.IUnitValue.providedBy(obj):
        kw['href'] = req.route_url('unit', id=obj.unit.id, **kw.pop('url_kw', {}))
    return kw


class MyMapMarker(LanguageByFamilyMapMarker):
    """Custom map marker based on language fmaily."""

    def get_icon(self, ctx, req):
        """Return map icon for a language.

        Needs to actually *find* the language when `ctx` is a value (i.e.
        comparison meaning).
        """
        if interfaces.IValue.providedBy(ctx):
            ctx = ctx.valueset.language
        if interfaces.IValueSet.providedBy(ctx):
            ctx = ctx.language
        return LanguageByFamilyMapMarker.get_icon(self, ctx, req)


def main(_global_config, **settings):
    """Return a Pyramid WSGI application."""
    config = Configurator(settings=settings)
    config.registry.registerUtility(link_attrs, interfaces.ILinkAttrs)
    config.include('clldmpg')
    config.include('clld_glottologfamily_plugin')
    config.registry.registerUtility(MyMapMarker(), interfaces.IMapMarker)

    config.add_page('submit')
    config.add_page('help')
    config.register_menu(
        ('dataset', partial(menu_item, 'dataset', label='Home')),
        ('contributions', partial(menu_item, 'contributions')),
        ('contributors', partial(menu_item, 'contributors')),
        ('sentences', partial(menu_item, 'sentences')),
        ('help', lambda _ctx, rq: (rq.route_url('help'), 'Help')),
    )

    config.add_settings(home_comp=['submit', 'languages'] + config.get_settings()['home_comp'])

    for cls in [md.BibTex, md.ReferenceManager]:
        for if_ in [interfaces.IRepresentation, interfaces.IMetadata]:
            config.register_adapter(cls, interfaces.IContribution, if_, name=cls.mimetype)

    return config.make_wsgi_app()
