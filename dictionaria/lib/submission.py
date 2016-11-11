# coding: utf8
from __future__ import unicode_literals
from mimetypes import guess_type

from clldutils.path import Path, remove, copy, md5
from clldutils.jsonlib import load
from clld.db.meta import DBSession
from clld.db.models import common

from dictionaria.lib import sfm
from dictionaria.lib import xlsx
from dictionaria.lib import filemaker
from dictionaria.lib.ingest import Examples
from dictionaria import models
import dictionaria


REPOS = Path(dictionaria.__file__).parent.joinpath('..', '..', 'dictionaria-intern')


class Submission(object):
    def __init__(self, path_or_id, internal=False):
        if isinstance(path_or_id, Path):
            self.dir = path_or_id
            self.id = path_or_id.name
        else:
            self.id = path_or_id
            self.dir = REPOS.joinpath(
                'submissions-internal' if internal else 'submissions', path_or_id)

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
        self.db_name = None
        self.impl = None
        if self.dir.joinpath('db.sfm').exists():
            self.db_name = 'db.sfm'
            self.impl = sfm.Dictionary
        elif list(self.dir.glob('*.xlsx')):
            self.db_name = list(self.dir.glob('*.xlsx'))[0].name
            self.impl = xlsx.Dictionary
        elif self.dir.joinpath('FIELDS.txt').exists():
            self.db_name = 'FIELDS.txt'
            self.impl = filemaker.Dictionary
        else:
            raise ValueError('no valid db file in %s' % self.dir)

    def db_path(self, processed=True):
        comps = ['processed'] if processed else []
        comps.append(self.db_name)
        return self.dir.joinpath(*comps)

    def dictionary(self, processed=True):
        kw = {}
        if self.impl == sfm.Dictionary:
            kw = dict(
                marker_map=self.md.get('marker_map'),
                encoding=self.md.get('encoding') if not processed else 'utf8')
        return self.impl(self.db_path(processed=processed), **kw)

    def concepticon(self):
        d = self.dictionary()
        d.concepticon(self.db_path())

    def process(self):
        d = self.dictionary(processed=False)
        outfile = self.db_path(processed=True)
        outfile.parent.mkdir(exist_ok=True)
        d.process(outfile, self)

    def stats(self, processed=True):
        d = self.dictionary(processed=processed)
        d.stats()

    def load(self, *args):
        d = self.dictionary(processed=True)
        d.load(self, *args)

    def process_file(self, type_, fp):
        #print(type_, fp)
        outdir = self.db_path(processed=True).parent.joinpath(type_)
        if not outdir.exists():
            outdir.mkdir()

        #if type_ == 'audio' and fp.suffix.lower() == '.wav':
        #    target = outdir.joinpath(fp.stem + '.mp3'.encode('utf8'))
        #    if target.exists():
        #        remove(target)
        #    subprocess.check_call([
        #        'avconv', '-i', fp.as_posix(), '-ab', '192k', target.as_posix()])
        #else:
        target = outdir.joinpath(fp.name)
        copy(fp, target)
        return target

    def add_file(self, args, type_, name, file_cls, obj, index, log='missing'):
        #
        # FIXME: switch to uploading to cdstar for production db!
        # - first step: store md5 in DB to later match files in cdstar!
        #
        fpath = self.dir.joinpath('processed', type_, name.encode('utf8'))
        if fpath.exists():
            #
            # 1. compute md5
            # 2. lookup in cdstar catalog
            # 3. Assign metadata to file object's jsondata
            #
            checksum = md5(fpath)
            if checksum in self.cdstar:
                jsondata = {k: v for k, v in self.md.get(type_, {}).items()}
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
            else:
                print(fpath)
                return
                mimetype = guess_type(fpath.name)[0]
                if mimetype:
                    assert mimetype.startswith(type_)
                    f = file_cls(
                        id='%s-%s-%s' % (self.id, obj.id, index),
                        name=name,
                        object_pk=obj.pk,
                        mime_type=mimetype,
                        jsondata=self.md.get(type_, {}))
                    DBSession.add(f)
                    DBSession.flush()
                    DBSession.refresh(f)
                    #
                    # Don't create files this way for the production DB!
                    #
                    with open(fpath.as_posix(), 'rb') as fp:
                        f.create(args.data_file('files'), fp.read())
                    if log == 'found':
                        print('{0} file added: {1}'.format(type_, name))
                    return

        if log == 'missing':
            print('{0} file missing: {1}'.format(type_, name))

    def load_examples(self, args, data, lang, xrefs=None):
        for ex in Examples.from_file(self.dir.joinpath('processed', 'examples.sfm')):
            if xrefs is None or ex.id in xrefs:
                obj = data.add(
                    models.Example,
                    ex.id,
                    id='%s-%s' % (self.id, ex.id.replace('.', '_')),
                    name=ex.text,
                    language=lang,
                    analyzed=ex.morphemes,
                    gloss=ex.gloss,
                    description=ex.translation,
                    alt_translation=ex.alt_translation,
                    alt_translation_language=self.md.get('metalanguages', {}).get('gxx'),
                    alt_translation2=ex.alt_translation2,
                    alt_translation_language2=self.md.get('metalanguages', {}).get('gxy'))
                DBSession.flush()

                if ex.soundfile:
                    mtype = guess_type(ex.soundfile)[0]
                    maintype = 'audio'
                    if mtype and mtype.startswith('image/'):
                        maintype = 'image'

                    self.add_file(
                        args,
                        maintype,
                        ex.soundfile,  # .replace('.wav', '.mp3'),
                        common.Sentence_files,
                        obj,
                        maintype)
