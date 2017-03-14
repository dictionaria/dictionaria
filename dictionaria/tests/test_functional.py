from clldutils.path import Path
from clld.tests.util import TestWithApp

import dictionaria


class Tests(TestWithApp):
    __cfg__ = Path(dictionaria.__file__).parent.joinpath('..', 'development.ini').resolve()
    __setup_db__ = False

    def test_home(self):
        res = self.app.get('/', status=200)

    def test_misc(self):
        self.app.get_dt('/sentences')
        self.app.get_dt('/contributors')
        self.app.get_dt('/contributions')
        self.app.get_dt('/units')
        self.app.get_html('/contributions/daakaka')
