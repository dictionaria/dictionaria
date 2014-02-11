from clld.tests.util import TestWithSelenium

import dictionaria


class Tests(TestWithSelenium):
    app = dictionaria.main({}, **{'sqlalchemy.url': 'postgres://robert@/dictionaria'})
