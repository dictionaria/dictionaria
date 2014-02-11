from clld.web.app import get_configurator

# we must make sure custom models are known at database initialization!
from dictionaria import models


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    config = get_configurator('dictionaria', settings=settings)
    config.include('clldmpg')
    config.include('dictionaria.datatables')
    config.include('dictionaria.adapters')
    return config.make_wsgi_app()
