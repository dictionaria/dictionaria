from hashlib import md5
from pathlib import Path

from clldutils.sfm import SFM, Entry
from clldutils.misc import lazyproperty, slug, UnicodeMixin
from clldutils.jsonlib import load
from clldutils.text import split_text

import dictionaria
from dictionaria import models


def split(s, sep=';'):
    return split_text(s, separators=sep, brackets={}, strip=True)


_concepticon = None


def get_concept(s):
    global _concepticon
    if _concepticon is None:
        _concepticon = load(Path(dictionaria.__file__).parent.joinpath(
            'static', 'concepticon-1.0-labels.json'))
    s = s.lower()
    if s in _concepticon['conceptset_labels']:
        return _concepticon['conceptset_labels'][s]
    return _concepticon['alternative_labels'].get(s)


class ComparisonMeaning(UnicodeMixin):
    def __init__(self, s):
        self.id = None
        self.label = None
        cid = get_concept(s)
        if cid:
            self.id, self.label = cid

    def __unicode__(self):
        if self.id:
            return f'[{self.label}](http://concepticon.clld.org/parameters/{self.id})'
        else:
            return ''


class MeaningDescription(object):
    # split s at ;
    # lookup concepticon match
    def __init__(self, s):
        self._meanings = []
        self._comparison_meanings = []
        for m in split(s):
            self._meanings.append(m)
            cm = ComparisonMeaning(m)
            self._comparison_meanings.append(cm if cm.id else '')

    @property
    def has_comparison_meaning(self):
        return any(self._comparison_meanings)

    @property
    def meanings(self):
        return '; '.join(self._meanings)

    @property
    def comparison_meanings(self):
        return '; '.join(str(cm) for cm in self._comparison_meanings)


class Example(Entry):
    markers = {
        'ref': 'id',
        'lemma': None,
        'rf': 'corpus_ref',
        'tx': 'text',
        'mb': 'morphemes',
        'gl': 'gloss',
        'ft': 'translation',
        'ot': 'alt_translation',
        'ota': 'alt_translation2',
        'sf': 'soundfile',
    }
    name_to_marker = {v: k for k, v in markers.items()}

    @staticmethod
    def normalize(morphemes_or_gloss):
        """
        Normalize aligned words by replacing whitespace with single tab, and removing
        ELAN comments.
        """
        if morphemes_or_gloss:
            return '\t'.join(
                p for p in morphemes_or_gloss.split() if not p.startswith('#'))

    @property
    def id(self):
        res = self.get('ref')
        if not res:
            res = md5(slug(self.text or '' + self.translation or '').encode('utf')).hexdigest()
            self.insert(0, ('ref', res))
        return res

    def set(self, key, value):
        assert (key in self.markers) or (key in self.name_to_marker)
        key = self.name_to_marker.get(key, key)
        for i, (k, v) in enumerate(self):
            if k == key:
                if key == 'lemma':
                    value = ' ; '.join([v, value])
                self[i] = (key, value)
                break
        else:
            self.append((key, value))

    @property
    def lemmas(self):
        return split(self.get('lemma', ''))

    @property
    def corpus_ref(self):
        return self.get('rf')

    @property
    def text(self):
        return self.get('tx')

    @property
    def translation(self):
        return self.get('ft')

    @property
    def alt_translation(self):
        return self.get('ot')

    @property
    def alt_translation2(self):
        return self.get('ota')

    @property
    def soundfile(self):
        return self.get('sf')

    @property
    def morphemes(self):
        return self.normalize(self.get('mb'))

    @property
    def gloss(self):
        return self.normalize(self.get('gl'))

    def __unicode__(self):
        lines = []
        for key in self.markers:
            value = self.get(key) or ''
            if key in ['mb', 'gl']:
                value = self.normalize(value) or ''
            else:
                value = ' '.join(value.split())
            lines.append(f'{key} {value}')
        return '\n'.join('\\' + l for l in lines)


class Examples(SFM):
    def read(self, filename, **kw):
        return SFM.read(self, filename, entry_impl=Example, **kw)

    @lazyproperty
    def _map(self):
        return {entry.get('ref'): entry for entry in self}

    def get(self, item):
        return self._map.get(item)


class BaseDictionary(object):
    """
    A dictionary that knows how to load data from a `processed` directory.
    """
    def __init__(self, d):
        self.dir = d

    def load(
            self,
            submission,
            data,
            vocab,
            lang,
            comparison_meanings,
            labels):
        raise NotImplementedError
