import re
from pathlib import Path

from clldutils.jsonlib import load
from clldutils.misc import lazyproperty, nfilter
from clld.db.meta import DBSession
from clld.db.models import common
from clld.lib import bibtex
from clld.cliutil import bibtex2source

from dictionaria.lib import cldf
from dictionaria import models
import dictionaria


REPOS = Path(dictionaria.__file__).parent.joinpath('..', '..', 'dictionaria-intern')


class Submission:
    def __init__(self, sid, path):
        self.id = sid
        self.dir = path

        assert self.dir.exists()

        cdstar_json = self.dir / 'etc' / 'cdstar.json'
        self.cdstar = load(cdstar_json) if cdstar_json.exists() else {}
        desc = self.dir / 'raw' / 'intro.md'
        if desc.exists():
            with desc.open(encoding='utf8') as fp:
                self.description = fp.read()
        else:
            self.description = None
        md = self.dir / 'etc' / 'md.json'
        self.md = load(md) if md.exists() else None
        self.props = self.md.get('properties', {}) if self.md else {}

    @lazyproperty
    def dictionary(self):
        if (self.dir / 'cldf').is_dir():
            return cldf.Dictionary(self.dir / 'cldf')
        else:
            raise ValueError('unknown dictionary format')

    def add_file(self, type_, checksum, file_cls, obj, attrs=None):
        if checksum in self.cdstar:
            jsondata = {k: v for k, v in self.props.get(type_, {}).items()}
            jsondata.update(self.cdstar[checksum])
            if attrs:
                jsondata.update(attrs)
            f = file_cls(
                id=f'{obj.id}-{checksum}',
                name=self.cdstar[checksum]['original'],
                object_pk=obj.pk,
                mime_type=self.cdstar[checksum]['mimetype'],
                jsondata=jsondata)
            DBSession.add(f)
            DBSession.flush()
            DBSession.refresh(f)
            return
        print(type_, 'file missing:', checksum)
        return

    def load_sources(self, dictionary, data):
        if self.dictionary.cldf.sources:
            print('loading sources ...')
            for rec in self.dictionary.cldf.sources:
                rec = bibtex.Record(rec.genre, rec.id, **rec)
                src = bibtex2source(rec, models.DictionarySource)
                src.dictionary = dictionary
                src.id = '{self.id}-{src.id}'
                data.add(models.DictionarySource, rec.id, _obj=src)

    def load_examples(self, dictionary, data, lang):
        abbr_p = re.compile(r'\$(?P<abbr>[a-z1-3][a-z]*(\.[a-z]+)?)')
        if hasattr(self.dictionary, 'cldf') and self.dictionary.cldf.get('ExampleTable'):
            examples = self.dictionary.cldf['ExampleTable']
            example_props = (
                'id',
                'primaryText',
                'analyzedWord',
                'gloss',
                'translatedText',
                'languageReference',
                'metaLanguageReference',
                'comment')
            colmap = {k: self.dictionary.cldf['ExampleTable', k].name
                      for k in example_props
                      if self.dictionary.cldf.get(('ExampleTable', k))}
            exlabels = cldf.get_labels(
                'example', examples, colmap, self,
                exclude=[
                    'Sense_IDs',
                    colmap.get('mediaReference', 'Media_IDs'),
                    colmap.get('languageReference', 'Language_ID')])

            for ord, ex in enumerate(self.dictionary.cldf['ExampleTable'], 1):
                obj = data.add(
                    models.Example,
                    ex[colmap['id']],
                    id='{}-{}'.format(self.id, ex.pop(colmap['id']).replace('.', '_')),
                    name=ex.pop(colmap['primaryText']),
                    number=str(ord),
                    source=ex.pop('Corpus_Reference', None),
                    comment=ex.pop(colmap['comment'], None) if 'comment' in colmap else None,
                    original_script=ex.pop('original_script', None),
                    language=lang,
                    serialized=str(ex),
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
                media_ids = sorted(set(
                    ex.pop(colmap.get('mediaReference', 'Media_IDs'), [])))
                for md5 in media_ids:
                    self.add_file(None, md5, common.Sentence_files, obj)

                for index, (key, label) in enumerate(exlabels.items()):
                    label, with_links = label
                    value = ex.get(key)
                    if value:
                        if isinstance(value, list):
                            value = '\t'.join(e or '' for e in value)
                        DBSession.add(common.Sentence_data(
                            object_pk=obj.pk,
                            key=label.replace('_', ' '),
                            value=value))
