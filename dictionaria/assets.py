from clld.web.assets import environment
from path import path

import dictionaria


environment.append_path(
    path(dictionaria.__file__).dirname().joinpath('static'), url='/dictionaria:static/')
environment.load_path = list(reversed(environment.load_path))
