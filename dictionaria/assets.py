from clld.web.assets import environment
from clldutils.path import Path

import dictionaria


environment.append_path(
    Path(dictionaria.__file__).parent.joinpath('static').as_posix(),
    url='/dictionaria:static/')
environment.load_path = list(reversed(environment.load_path))
