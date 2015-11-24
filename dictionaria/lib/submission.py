# coding: utf8
from __future__ import unicode_literals

from clldutils.path import Path
from clldutils.jsonlib import load

from dictionaria.lib.sfm import Dictionary
import dictionaria


REPOS = Path(dictionaria.__file__).parent.joinpath('..', '..', 'dictionaria-intern')


class Submission(object):
    def __init__(self, path_or_id):
        if isinstance(path_or_id, Path):
            self.dir = path_or_id
            self.id = path_or_id.name
        else:
            self.id = path_or_id
            self.dir = REPOS.joinpath('submissions', path_or_id)

        assert self.dir.exists()
        md = self.dir.joinpath('md.json')
        self.md = load(md) if md.exists() else None
        self.db_name = None
        self.type = None
        if self.dir.joinpath('db.sfm').exists():
            self.db_name = 'db.sfm'
            self.type = 'sfm'
        else:
            raise ValueError('no valid db file in %s' % self.dir)

    def db_path(self, processed=True):
        comps = ['processed'] if processed else []
        comps.append(self.db_name)
        return self.dir.joinpath(*comps)

    def dictionary(self, processed=True):
        db_path = self.db_path(processed=processed)
        if self.type == 'sfm':
            return Dictionary(
                db_path,
                marker_map=self.md.get('marker_map'),
                encoding=self.md.get('encoding') if not processed else 'utf8')

    def process(self):
        d = self.dictionary(processed=False)
        outfile = self.db_path(processed=True)
        outfile.parent.mkdir(exist_ok=True)
        d.process(outfile)

    def stats(self, processed=True):
        pass
