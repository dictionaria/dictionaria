# coding: utf8
from __future__ import unicode_literals
from mimetypes import guess_type

from clldutils.path import Path, md5
from clldutils.jsonlib import load
from clld.db.meta import DBSession
from clld.db.models import common

from dictionaria.lib import sfm
from dictionaria.lib.ingest import Examples, BaseDictionary
from dictionaria import models
import dictionaria


REPOS = Path(dictionaria.__file__).parent.joinpath('..', '..', 'dictionaria-intern')


class Submission(object):
    def __init__(self, path):
        self.dir = path
        self.id = path.name

        self.cdstar = load(REPOS.joinpath('cdstar.json'))
        print(self.dir)
        assert self.dir.exists()
        desc = self.dir.joinpath('md.html')
        if desc.exists():
            with desc.open(encoding='utf8') as fp:
                self.description = fp.read()
        else:
            self.description = None
        md = self.dir.joinpath('md.json')
        self.md = load(md) if md.exists() else None
        self.props = self.md.get('properties', {}) if self.md else {}

    @property
    def dictionary(self):
        d = self.dir.joinpath('processed')
        impl = sfm.Dictionary if d.joinpath('db.sfm').exists() else BaseDictionary
        return impl(d)

    def add_file(self, type_, name, file_cls, obj, index, log='missing'):
        fpath = self.dir.joinpath(type_, name.encode('utf8'))
        if fpath.exists():
            # 1. compute md5
            # 2. lookup in cdstar catalog
            # 3. Assign metadata to file object's jsondata
            checksum = md5(fpath)
            if checksum in self.cdstar:
                jsondata = {k: v for k, v in self.props.get(type_, {}).items()}
                jsondata.update(self.cdstar[checksum])
                f = file_cls(
                    id='%s-%s-%s' % (self.id, obj.id, index),
                    name=name,
                    object_pk=obj.pk,
                    mime_type=self.cdstar[checksum]['mimetype'],
                    jsondata=jsondata)
                DBSession.add(f)
                DBSession.flush()
                DBSession.refresh(f)
                return
            print(fpath)
            return

        if log == 'missing':
            print('{0} file missing: {1}'.format(type_, name))

    def load_examples(self, dictionary, data, lang):
        for ex in Examples.from_file(self.dir.joinpath('processed', 'examples.sfm')):
            obj = data.add(
                models.Example,
                ex.id,
                id='%s-%s' % (self.id, ex.id.replace('.', '_')),
                name=ex.text,
                language=lang,
                dictionary=dictionary,
                analyzed=ex.morphemes,
                gloss=ex.gloss,
                description=ex.translation,
                alt_translation1=ex.alt_translation,
                alt_translation_language1=self.props.get('metalanguages', {}).get('gxx'),
                alt_translation2=ex.alt_translation2,
                alt_translation_language2=self.props.get('metalanguages', {}).get('gxy'))
            DBSession.flush()

            if ex.soundfile:
                maintype = 'audio'
                mtype = guess_type(ex.soundfile)[0]
                if mtype and mtype.startswith('image/'):
                    maintype = 'image'

                self.add_file(
                    maintype,
                    ex.soundfile,
                    common.Sentence_files,
                    obj,
                    maintype)
