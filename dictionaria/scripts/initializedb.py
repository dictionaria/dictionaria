from datetime import date
from itertools import groupby, chain
import json
from collections import OrderedDict, defaultdict
import re

import transaction
from nameparser import HumanName
from sqlalchemy.orm import joinedload
from sqlalchemy import Index
import cldfcatalog
from clldutils.misc import slug, nfilter, lazyproperty
from clld.util import LGR_ABBRS
from clld.cliutil import Data
from clld.db.meta import DBSession
from clld.db.models import common
from clld.db import fts
from clld_glottologfamily_plugin.util import load_families
from pyconcepticon.api import Concepticon
from bs4 import BeautifulSoup
import git
from markdown import markdown

import dictionaria
from dictionaria.models import ComparisonMeaning, Dictionary, Word, Variety, Meaning_files, Meaning, Example
from dictionaria.lib.submission import REPOS, Submission
from dictionaria.lib.cldf_zenodo import download_from_doi
from dictionaria.util import join, toc


def download_data(sid, contrib_md, cache_dir):
    if contrib_md.get('doi'):
        doi = contrib_md['doi']
        path = cache_dir / '{}-{}'.format(sid, slug(doi))
        if not path.exists():
            print(' * downloading dataset from Zenodo; doi:', doi)
            download_from_doi(doi, path)
            print('   done.')
        if not (path / 'cldf').exists():
            for subpath in path.glob('*'):
                if (subpath / 'cldf').exists():
                    path = subpath
                    break
        return path

    elif contrib_md.get('repo'):
        origin = contrib_md.get('repo')
        checkout = contrib_md.get('checkout')
        path = (cache_dir / sid).resolve()

        if not path.exists():
            print(' * cloning', origin, 'into', path)
            git.Git().clone(origin, path)
        if not path.exists():
            raise ValueError('Could not clone {}'.format(origin))

        try:
            repo = git.Repo(path)
        except git.exc.InvalidGitRepositoryError as e:
            print('WARNING: not a git repo:', str(e))
            return path

        for remote in repo.remotes:
            remote.fetch()

        if checkout:
            for branch in repo.branches:
                if branch.name == checkout:
                    print(' *', path, 'checking out branch', checkout)
                    branch.checkout()
                    repo.git.merge()
                    break
            else:
                print(' *', path, 'checking out', checkout)
                repo.git.checkout(checkout)
        else:
            # checkout main/master
            try:
                branch = repo.branches.main
                branch.checkout()
            except AttributeError:
                try:
                    branch = repo.branches.master
                    branch.checkout()
                except AttributeError:
                    print('WARNING: default branch is neither main nor master')
            print(' *', path, 'merging latest changes')
            repo.git.merge()

        return path

    else:
        return cache_dir / sid


def main(args):
    published = input('[i]nternal or [e]xternal data (default: e): ').strip().lower() != 'i'
    dict_id = input("dictionary id or 'all' for all dictionaries (default: all): ").strip()

    catalog_ini = cldfcatalog.Config.from_file()
    concepticon_path = catalog_ini.get_clone('concepticon')
    glottolog_path = catalog_ini.get_clone('glottolog')

    fts.index('fts_index', Word.fts, DBSession.bind)
    DBSession.execute("CREATE EXTENSION IF NOT EXISTS unaccent WITH SCHEMA public;")

    data = Data()

    dataset = common.Dataset(
        id=dictionaria.__name__,
        name="Dictionaria",
        description="The Dictionary Journal",
        published=date(2017, 3, 30),
        contact='dictionary.journal@uni-leipzig.de',
        domain='dictionaria.clld.org',
        publisher_name="Max Planck Institute for Evolutionary Anthropology",
        publisher_place="Leipzig",
        publisher_url="https://eva.mpg.de",
        license="http://creativecommons.org/licenses/by/4.0/",
        jsondata={
            'license_icon': 'cc-by.png',
            'license_name': 'Creative Commons Attribution 4.0 International License'})

    for i, (id_, name) in enumerate([
        ('haspelmathmartin', 'Martin Haspelmath'),
        ('stiebelsbarbara', 'Barbara Stiebels')
    ]):
        ed = data.add(common.Contributor, id_, id=id_, name=name)
        common.Editor(dataset=dataset, contributor=ed, ord=i + 1)
    DBSession.add(dataset)

    for id_, name in LGR_ABBRS.items():
        DBSession.add(common.GlossAbbreviation(id=id_, name=name))

    comparison_meanings = {}

    print('loading concepts ...')

    glosses = set()
    concepticon = Concepticon(concepticon_path)
    for conceptset in concepticon.conceptsets.values():
        if conceptset.gloss in glosses:
            continue
        glosses.add(conceptset.gloss)
        cm = data.add(
            ComparisonMeaning,
            conceptset.id,
            id=conceptset.id,
            name=conceptset.gloss.lower(),
            description=conceptset.definition,
            concepticon_url='http://concepticon.clld.org/parameters/%s' % conceptset.id)
        comparison_meanings[cm.id] = cm

    DBSession.flush()

    print('... done')

    comparison_meanings = {k: v.pk for k, v in comparison_meanings.items()}

    with open(REPOS / 'contributions.json', encoding='utf-8') as f:
        contrib_json = json.load(f)

    submissions = []
    for sid, sinfo in contrib_json.items():
        if sinfo['published'] != published:
            continue
        if dict_id and dict_id != sid and dict_id != 'all':
            print('not selected', sid)
            continue

        if not sinfo['date_published']:
            print('no date', sid)
            continue

        data_dir = download_data(sid, sinfo, REPOS / 'datasets')

        try:
            submission = Submission(sid, data_dir)
        except ValueError:
            continue

        md = submission.md
        if md is None:
            print('etc/md.json not found', submission.id)
            continue

        lmd = md['language']
        props = md.get('properties', {})
        props.setdefault('custom_fields', [])
        props['metalanguage_styles'] = {}
        for v, s in zip(props.get('metalanguages', {}).values(),
                        ['success', 'info', 'warning', 'important']):
            props['metalanguage_styles'][v] = s
        props['custom_fields'] = ['lang-' + f if f in props['metalanguage_styles'] else f
                                  for f in props['custom_fields']]
        props.setdefault('choices', {})

        language = data['Variety'].get(lmd['glottocode'])
        if not language:
            language = data.add(
                Variety, lmd['glottocode'], id=lmd['glottocode'], name=lmd['name'])

        date_published = sinfo.get('date_published') or date.today().isoformat()
        if '-' not in date_published:
            date_published = date_published + '-01-01'

        # strip off ssh stuff off git link
        git_https = re.sub(
            '^git@([^:]*):', r'https://\1/', sinfo.get('repo') or '')

        dictionary = data.add(
            Dictionary,
            sid,
            id=sid,
            number=sinfo.get('number'),
            name=props.get('title', lmd['name'] + ' dictionary'),
            description=submission.description,
            language=language,
            published=date(*map(int, date_published.split('-'))),
            doi=sinfo.get('doi'),
            git_repo=git_https,
            jsondata=props)

        for i, spec in enumerate(md['authors']):
            if not isinstance(spec, dict):
                cname, address = spec, None
                spec = {}
            else:
                cname, address = spec['name'], spec.get('affiliation')
            name = HumanName(cname)
            cid = slug('%s%s' % (name.last, name.first))
            contrib = data['Contributor'].get(cid)
            if not contrib:
                contrib = data.add(
                    common.Contributor,
                    cid,
                    id=cid,
                    name=cname,
                    address=address,
                    url=spec.get('url'),
                    email=spec.get('email'))
            DBSession.add(common.ContributionContributor(
                ord=i + 1,
                primary=spec.get('primary', True),
                contributor=contrib,
                contribution=dictionary))

        submissions.append((dictionary.id, language.id, submission))
    transaction.commit()

    for did, lid, submission in submissions:
        transaction.begin()
        print('loading %s ...' % submission.id)
        dictdata = Data()
        lang = Variety.get(lid)
        submission.load_sources(Dictionary.get(did), dictdata)
        submission.load_examples(Dictionary.get(did), dictdata, lang)
        submission.dictionary.load(
            submission,
            dictdata,
            Dictionary.get(did),
            lang,
            comparison_meanings,
            OrderedDict(submission.md.get('properties', {}).get('labels', [])))
        transaction.commit()
        print('... done')

    transaction.begin()
    load_families(
        Data(),
        [v for v in DBSession.query(Variety) if re.match('[a-z]{4}[0-9]{4}', v.id)],
        glottolog_repos=glottolog_path)


def joined(iterable):
    return ' ; '.join(sorted(nfilter(set(iterable))))


class CustomFieldDenormalizer:
    """Denormalize custom fields for the first and second tab of a word."""

    custom_attribs = ('custom_field1', 'custom_field2')
    second_tab_attribs = ('second_tab1', 'second_tab2', 'second_tab3')

    def __init__(self, word):
        self.word = word

    @lazyproperty
    def word_datadict(self):
        return self.word.datadict()

    @lazyproperty
    def meaning_datadicts(self):
        return [m.datadict() for m in self.word.meanings]

    @lazyproperty
    def meaning_keys(self):
        return {k for d in self.meaning_datadicts for k in d}

    def set_custom_fields(self, custom_fields):
        self._denormalise_custom_fields(self.custom_attribs, custom_fields)

    def set_second_tab(self, second_tab):
        self._denormalise_custom_fields(self.second_tab_attribs, second_tab)

    def _denormalise_custom_fields(self, attribs, colnames):
        for attrib, name in zip(attribs, colnames):
            if name in self.word_datadict:
                setattr(self.word, attrib, self.word_datadict[name])
            elif name in self.meaning_keys:
                val = ' / '.join(
                    d.get(name) for d in self.meaning_datadicts if d.get(name))
                if val:
                    setattr(self.word, attrib, val)


def denormalize_dictionary(contrib):
    query = DBSession.query(Word)\
        .filter_by(dictionary=contrib)\
        .order_by(Word.dictionary_pk, common.Unit.name, common.Unit.pk)\
        .options(joinedload(Word.meanings), joinedload(Word.dictionary))

    jsondata = contrib.jsondata
    custom_fields = jsondata.get('custom_fields') or ()
    second_tab = jsondata.get('second_tab') or ()

    for _, words in groupby(query, lambda u: u.name):
        words = list(words)
        for i, word in enumerate(words):
            word.description = ' / '.join(m.name for m in word.meanings)
            word.semantic_domain = joined(m.semantic_domain for m in word.meanings)
            word.number = i + 1 if len(words) > 1 else 0

            custom_field_adder = CustomFieldDenormalizer(word)
            custom_field_adder.set_custom_fields(custom_fields)
            custom_field_adder.set_second_tab(second_tab)

            for suffix in ['1', '2']:
                alt_t, alt_l = [], []
                for m in word.meanings:
                    if getattr(m, 'alt_translation' + suffix):
                        alt_l.append(getattr(m, 'alt_translation_language' + suffix))
                        alt_t.append(getattr(m, 'alt_translation' + suffix))
                if alt_t and len(set(alt_l)) == 1:
                    DBSession.add(common.Unit_data(
                        object_pk=word.pk, key='lang-' + alt_l.pop(), value=join(alt_t)))
    DBSession.flush()


def prime_cache(args):
    """If data needs to be denormalized for lookup, do that here.
    This procedure should be separate from the db initialization, because
    it will have to be run periodically whenever data has been updated.
    """
    labels = {}
    for type_, cls in [('source', common.Source), ('unit', common.Unit)]:
        labels[type_] = defaultdict(dict)
        for r in DBSession.query(cls.id, cls.name):
            sid, _, lid = r[0].partition('-')
            labels[type_][sid][lid] = r[1]

    link_map = {'entry': 'unit', 'source': 'source'}

    for d in DBSession.query(Dictionary):
        if d.description:
            soup = BeautifulSoup(
                markdown(d.description, extensions=['tables']),
                'html.parser')
            for a in soup.find_all('a', href=True):
                if a['href'] in link_map:
                    type_ = link_map[a['href']]
                    if a.string in labels[type_][d.id]:
                        a['href'] = args.env['request'].route_path(
                            type_, id='{0}-{1}'.format(d.id, a.string))
                        a.string = labels[type_][d.id][a.string]
                        if type_ == 'unit':
                            a['class'] = 'lemma'
            d.description, d.toc = toc(soup)

    for meaning in DBSession.query(ComparisonMeaning).options(
        joinedload(common.Parameter.valuesets).joinedload(common.ValueSet.values)
    ):
        meaning.representation = sum([len(vs.values) for vs in meaning.valuesets])
        if meaning.representation == 0:
            meaning.active = False

    DBSession.flush()
    for d in DBSession.query(Dictionary):
        print('Denormalizing dictionary {} ...'.format(d.id))
        denormalize_dictionary(d)
        print('... done')

    def count_unit_media_files(contrib, mtype, cls=common.Unit_files):
        if cls == common.Unit_files:
            return DBSession.query(common.Unit_files)\
                .join(Word, common.Unit_files.object_pk == Word.pk)\
                .filter(Word.dictionary_pk == contrib.pk)\
                .filter(common.Unit_files.mime_type.ilike(mtype + '/%'))\
                .count() + \
                DBSession.query(Meaning_files)\
                .join(Meaning, Meaning_files.object_pk == Meaning.pk)\
                .join(Word, Meaning.word_pk == Word.pk)\
                .filter(Word.dictionary_pk == contrib.pk)\
                .filter(Meaning_files.mime_type.ilike(mtype + '/%'))\
                .count()
        return DBSession.query(common.Sentence_files)\
            .join(common.Sentence, common.Sentence_files.object_pk == common.Sentence.pk)\
            .filter(Example.dictionary_pk == contrib.pk)\
            .filter(common.Sentence_files.mime_type.ilike(mtype + '/%'))\
            .count()

    print('counting media files ...')
    for d in DBSession.query(Dictionary):
        q = DBSession.query(Word).filter(Word.dictionary_pk == d.pk)
        d.count_words = q.count()
        sds = set(chain(*[w.semantic_domain_list for w in q]))
        d.semantic_domains = join(sorted(sds))
        d.count_audio = count_unit_media_files(d, 'audio')
        d.count_example_audio = count_unit_media_files(d, 'audio', cls=common.Sentence_files)
        d.count_image = count_unit_media_files(d, 'image')

        word_pks = [w.pk for w in d.words]
        choices = {}
        for col in d.jsondata.get('custom_fields', []):
            values = [
                r[0] for r in DBSession.query(common.Unit_data.value)
                .filter(common.Unit_data.object_pk.in_(word_pks))
                .filter(common.Unit_data.key == col)
                .distinct()]
            if len(values) < 40:
                choices[col] = sorted(values)
        d.update_jsondata(choices=choices)
        DBSession.flush()
    print('... done')

    DBSession.execute("""
    UPDATE word
      SET example_count = s.c
      FROM (
        SELECT m.word_pk AS wpk, count(ms.sentence_pk) AS c
        FROM meaning AS m, meaningsentence AS ms
        WHERE m.pk = ms.meaning_pk
        GROUP BY m.word_pk
      ) AS s
      WHERE word.pk = s.wpk
    """)
