# coding: utf8
from __future__ import unicode_literals
import re

from clldutils.path import Path
from clldutils.jsonlib import load
from clldutils.misc import nfilter
from clld.db.meta import DBSession
from clld.db.models import common
from clld.lib import bibtex
from clld.scripts.util import bibtex2source

from dictionaria.lib import cldf
from dictionaria.lib.ingest import Examples
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
        desc = self.dir.joinpath('intro.md')
        if desc.exists():
            with desc.open(encoding='utf8') as fp:
                self.description = fp.read()
        else:
            self.description = None
        md = self.dir.joinpath('md.json')
        self.md = load(md) if md.exists() else None
        self.props = self.md.get('properties', {}) if self.md else {}
        bib = self.dir.joinpath('sources.bib')
        self.bib = bibtex.Database.from_file(bib) if bib.exists() else None

    @property
    def dictionary(self):
        d = self.dir.joinpath('processed')
        if d.joinpath('cldf-md.json').exists():
            impl = cldf.Dictionary
        else:
            raise ValueError('unknown dictionary format')
        return impl(d)

    def add_file(self, type_, checksum, file_cls, obj, attrs=None):
        if checksum in self.cdstar:
            jsondata = {k: v for k, v in self.props.get(type_, {}).items()}
            jsondata.update(self.cdstar[checksum])
            if attrs:
                jsondata.update(attrs)
            f = file_cls(
                id='%s-%s' % (obj.id, checksum),
                name=self.cdstar[checksum]['original'],
                object_pk=obj.pk,
                mime_type=self.cdstar[checksum]['mimetype'],
                jsondata=jsondata)
            DBSession.add(f)
            DBSession.flush()
            DBSession.refresh(f)
            return
        print('{0} file missing: {1}'.format(type_, checksum))
        return

    def load_sources(self, dictionary, data):
        if self.bib:
            for rec in self.bib.records:
                src = bibtex2source(rec, models.DictionarySource)
                src.dictionary = dictionary
                src.id = '%s-%s' % (self.id, src.id)
                data.add(models.DictionarySource, rec.id, _obj=bibtex2source(rec))

    def load_examples(self, dictionary, data, lang):
        abbr_p = re.compile('\$(?P<abbr>[a-z1-3][a-z]*(\.[a-z]+)?)')
        if hasattr(self.dictionary, 'cldf'):
            #ID,Language_ID,Primary_Text,Analyzed_Word,Gloss,Translated_Text,Meta_Language_ID,Comment,Sense_IDs,Analyzed,Media_IDs
            #XV000001,tzh,lek a lok',,,salió bien,,,SN000001,,
            colmap = {}
            for k in [
                'id',
                'primaryText',
                'analyzedWord',
                'gloss',
                'translatedText',
                'languageReference',
                'metaLanguageReference',
                'comment',
            ]:
                try:
                    colmap[k] = self.dictionary.cldf['ExampleTable', k].name
                except KeyError:
                    pass

            for i, ex in enumerate(self.dictionary.cldf['ExampleTable']):
                obj = data.add(
                    models.Example,
                    ex[colmap['id']],
                    id='%s-%s' % (self.id, ex.pop(colmap['id']).replace('.', '_')),
                    name=ex.pop(colmap['primaryText']),
                    number='{0}'.format(i + 1),
                    source=ex.pop('Corpus_Reference', None),
                    comment=ex.pop(colmap['comment'], None) if 'comment' in colmap else None,
                    original_script=ex.pop('original_script', None),
                    language=lang,
                    serialized='{0}'.format(ex),
                    dictionary=dictionary,
                    analyzed='\t'.join(
                        nfilter(ex.pop(colmap['analyzedWord'], []) or []))
                    if 'analyzedWord' in colmap else None,
                    gloss='\t'.join(
                        [abbr_p.sub(lambda m: m.group('abbr').upper(), g or '') for g in ex[colmap['gloss']]])
                    if 'gloss' in colmap and ex[colmap['gloss']] \
                    else ((ex[colmap['gloss']] or None) if 'gloss' in colmap else None),
                    description=ex.pop(colmap['translatedText'], None),
                    alt_translation1=ex.pop('alt_translation1', None),
                    alt_translation_language1=self.props.get('metalanguages', {}).get('gxx'),
                    alt_translation2=ex.pop('alt_translation2', None),
                    alt_translation_language2=self.props.get('metalanguages', {}).get('gxy'),
                )
                for col in ['languageReference', 'metaLanguageReference', 'gloss']:
                    if col in colmap:
                        del ex[colmap[col]]
                DBSession.flush()
                for md5 in sorted(set(ex.pop('Media_IDs', []))):
                    self.add_file(None, md5, common.Sentence_files, obj)

                for k, v in ex.items():
                    if v and (k not in ['Sense_IDs']):
                        DBSession.add(common.Sentence_data(
                            object_pk=obj.pk,
                            key=k,
                            value=ex[k],
                        ))
        elif self.dir.joinpath('processed', 'examples.sfm').exists():
            for i, ex in enumerate(
                    Examples.from_file(self.dir.joinpath('processed', 'examples.sfm'))):
                obj = data.add(
                    models.Example,
                    ex.id,
                    id='%s-%s' % (self.id, ex.id.replace('.', '_')),
                    name=ex.text,
                    number='{0}'.format(i + 1),
                    source=ex.corpus_ref,
                    language=lang,
                    serialized='{0}'.format(ex),
                    dictionary=dictionary,
                    analyzed=ex.morphemes,
                    gloss=abbr_p.sub(lambda m: m.group('abbr').upper(), ex.gloss) if ex.gloss else ex.gloss,
                    description=ex.translation,
                    alt_translation1=ex.alt_translation,
                    alt_translation_language1=self.props.get('metalanguages', {}).get('gxx'),
                    alt_translation2=ex.alt_translation2,
                    alt_translation_language2=self.props.get('metalanguages', {}).get('gxy'))
                DBSession.flush()

                if ex.soundfile:
                    self.add_file('audio', ex.soundfile, common.Sentence_files, obj)

