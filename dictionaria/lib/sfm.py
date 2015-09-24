"""
Parsing SIL Standard Format (SFM) files
"""
from __future__ import unicode_literals
import re
from collections import Counter
import mimetypes
from collections import defaultdict

from path import path
from clld.util import UnicodeMixin


MARKER_PATTERN = re.compile('\\\\(?P<marker>[a-z1-3][a-z]*)(\s+|$)')
FIELD_SPLITTER_PATTERN = re.compile(';\s+')


def marker_split(block):
    """generate marker, value pairs from a text block (i.e. a list of lines).
    """
    marker = None
    value = []

    for line in block.split('\n'):
        line = line.strip()
        if line.startswith('\\_'):
            continue  # we simply ignore SFM header fields
        match = MARKER_PATTERN.match(line)
        if match:
            if marker:
                yield marker, '\n'.join(value)
            marker = match.group('marker')
            value = [line[match.end():]]
        else:
            value.append(line)
    if marker:
        yield marker, ('\n'.join(value)).strip()


class Entry(list, UnicodeMixin):
    """We store entries in SFM files as lists of (marker, value) pairs.
    """
    @classmethod
    def from_string(cls, block):
        entry = cls()
        for marker, value in marker_split(block.strip()):
            value = value.strip()
            if value:
                entry.append((marker, value))
        return entry

    def markers(self):
        return Counter([k for k, v in self])

    def get(self, key, default=None):
        """Use get to retrieve the first value for a marker or None.
        """
        for k, v in self:
            if k == key:
                return v
        return default

    def getall(self, key):
        """Use getall to retrieve all values for a marker.
        """
        return [v for k, v in self if k == key]

    def __unicode__(self):
        lines = []
        for key, value in self:
            lines.append('%s %s' % (key, value))
        return '\n'.join('\\' + l for l in lines)


def parse(filename, encoding, entry_impl, entry_sep, entry_prefix, marker_map):
    """We assume entries in the file are separated by a blank line.
    """
    # we cannot use codecs.open, because it does not understand mode U.
    with open(filename, 'rU') as fp:
        # thus we have to decode the content ourselves:
        for block in fp.read().decode(encoding).split(entry_sep):
            if block.strip():
                block = entry_prefix + block
            else:
                continue
            rec = entry_impl()
            for marker, value in marker_split(block.strip()):
                value = value.strip()
                if value:
                    rec.append((marker_map.get(marker, marker), value))
            if rec:
                yield rec


class Dictionary(object):
    def __init__(self,
                 filename,
                 encoding='utf8',
                 validate=True,
                 marker_map=None,
                 entry_impl=Entry,
                 entry_sep='\n\n',
                 entry_prefix=None):
        self.marker_map = marker_map or {}
        self.filename = filename
        self.validate = validate
        self.dir = path(filename).dirname()
        self.entries = []
        self._markers = Counter()
        self._mult_markers = defaultdict(int)
        self._implicit_mult_markers = set()

        for entry in parse(
                filename,
                encoding,
                entry_impl,
                entry_sep,
                entry_prefix or entry_sep,
                self.marker_map):
            entry_markers = entry.markers()
            self._markers.update(entry_markers)
            for k, v in entry_markers.items():
                if v > self._mult_markers[k]:
                    self._mult_markers[k] = v
            for k, v in entry:
                if FIELD_SPLITTER_PATTERN.search(v):
                    self._implicit_mult_markers.add(k)
            # now validation and potentially preprocessing takes place
            self.entries.append(self.validated(entry))

    def markers(self):
        return self._markers

    def validated(self, entry):
        def basename(path):
            if '\\' in path:
                return path.split('\\')[-1]
            if '/' in path:
                return path.split('/')[-1]
            return path

        if self.validate:
            for marker, subdir, mimetype in [
                ('pc', 'images', 'image'), ('sf', 'sounds', 'audio')
            ]:
                for i, pair in entry:
                    if pair[0] == marker:
                        p = self.dir.joinpath(subdir, basename(pair[1]))
                        assert p.exists()
                        mtype, _ = mimetypes.guess_type(basename(pair[1]))
                        assert mtype.split('/')[0] == mimetype
                        entry[i] = (pair[0], (p, mtype))
        return entry

    def values(self, marker):
        """
        :return: list of distinct values for marker in any entry.
        """
        res = defaultdict(lambda: 0)
        for e in self.entries:
            for v in e.getall(marker):
                res[v] += 1
        return res

    def __len__(self):
        return len(self.entries)

    def __iter__(self):
        return iter(self.entries)

    def stats(self):
        print('')
        print('marker\tper entry\twith semikolon\ttotal')
        for m in sorted(self._mult_markers):
            print('%s\t%s\t%s\t%s' % (
                m,
                self._mult_markers[m],
                m in self._implicit_mult_markers,
                self._markers[m]))
        print('')
        print('%s entries' % len(self))
        #print('distinct ps values:')
        #for m in sorted(set(self.values('ps'))):
        #    print(m)
        #print()
        #print('distinct sd values:')
        #for m in sorted(set(self.values('sd'))):
        #    print(m)
        #print()
