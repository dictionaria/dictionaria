from pathlib import Path

from clld.web.assets import environment

import dictionaria


environment.append_path(
    Path(dictionaria.__file__).parent.joinpath('static').as_posix(),
    url='/dictionaria:static/')
environment.load_path = list(reversed(environment.load_path))
