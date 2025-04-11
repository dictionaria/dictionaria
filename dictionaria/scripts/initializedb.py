"""Data base initialisation."""

import datetime
import json
import re
from collections import defaultdict, namedtuple
from itertools import chain
from pathlib import Path

import git
from bs4 import BeautifulSoup
from markdown import markdown
from nameparser import HumanName
from pyconcepticon.api import Concepticon
from sqlalchemy import not_
from sqlalchemy.orm import joinedload

import cldfcatalog
from clld.cliutil import Data
from clld.db import fts
from clld.db.meta import DBSession
from clld.db.models import common
from clld.util import LGR_ABBRS
from clld_glottologfamily_plugin.util import load_families
from clldutils.misc import slug
from pycldf.ext.discovery import get_dataset

import dictionaria
from dictionaria.lib.cldf import Submission
from dictionaria.models import (
    ComparisonMeaning, Dictionary, Example, Meaning, Meaning_files, Variety,
    Word,
)
from dictionaria.util import join, toc

Ed = namedtuple('Ed', 'id name')


DICTIONARIA_EDITORS = [
    Ed(id='haspelmathmartin', name='Martin Haspelmath'),
    Ed(id='stiebelsbarbara', name='Barbara Stiebels'),
]

WEBAPP_REPO = Path(dictionaria.__file__).parent
INTERNAL_REPO = WEBAPP_REPO.joinpath('..', '..', 'dictionaria-intern')


def zenodo_download(sid, contrib_md, cache_dir):
    """Download a contribution from Zenodo."""
    doi = contrib_md['doi']
    path = cache_dir / f'{sid}-{slug(doi)}'
    if not path.exists():
        print(' * downloading dataset from Zenodo; doi:', doi)
        _ = get_dataset(f'https://doi.org/{doi}', path)
        print('   done.')
    if not (path / 'cldf').exists():
        for subpath in path.glob('*'):
            if (subpath / 'cldf').exists():
                path = subpath
                break
    return path


def git_download(sid, contrib_md, cache_dir):
    """Download a contribution using git."""
    origin = contrib_md.get('repo')
    checkout = contrib_md.get('checkout')
    path = (cache_dir / sid).resolve()

    if not path.exists():
        print(' * cloning', origin, 'into', path)
        git.Git().clone(origin, path)
    if not path.exists():
        raise ValueError(f'Could not clone {origin}')

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


def download_data(sid, contrib_md, cache_dir):
    """Download data of a contribution to `cache_dir`."""
    if contrib_md.get('doi'):
        return zenodo_download(sid, contrib_md, cache_dir)
    elif contrib_md.get('repo'):
        return git_download(sid, contrib_md, cache_dir)
    else:
        assert (cache_dir / sid).is_dir(), 'dataset folder must exist'
        return cache_dir / sid


def iter_gloss_abbrevs(leipzig_glossing_rules_abbrevs):
    """Return gloss abbreviations based on the Leipzig Glossing Rules."""
    return (
        common.GlossAbbreviation(id=id_, name=name)
        for id_, name in leipzig_glossing_rules_abbrevs.items())


def make_comparison_meanings(concepticon):
    """Return comparison meaning objects from Concepticon."""
    # make sure there's only one comparison meaning per gloss
    concepts_by_gloss = {}
    for conceptset in concepticon.conceptsets.values():
        if conceptset.gloss not in concepts_by_gloss:
            concepts_by_gloss[conceptset.gloss] = conceptset
    return {
        conceptset.id: ComparisonMeaning(
            id=conceptset.id,
            name=conceptset.gloss.lower(),
            description=conceptset.definition,
            concepticon_url=f'http://concepticon.clld.org/parameters/{conceptset.id}')
        for conceptset in concepts_by_gloss.values()}


def make_languages(submissions):
    """Return languages the dictionaries are abount."""
    language_names = defaultdict(set)
    for submission in submissions.values():
        language_names[submission.glottocode].add(
            submission.md['language']['name'])
    # NOTE: this *might* change, we'll see
    assert all(len(names) == 1 for names in language_names.values())
    return {
        glottocode: Variety(
            id=glottocode,
            name=next(iter(names)),
            glottolog_id=glottocode)
        for glottocode, names in language_names.items()}


def make_dictionary(submission, sinfo, language):
    """Return a contribution object for a single dictionary."""
    date_published = (
        sinfo.get('date_published')
        or datetime.datetime.now().date().isoformat())
    if '-' not in date_published:
        date_published = date_published + '-01-01'

    # strip off ssh stuff off git link
    git_https = re.sub(
        '^git@([^:]*):', r'https://\1/', sinfo.get('repo') or '')

    return Dictionary(
        id=submission.id,
        series=sinfo.get('series'),
        number=sinfo.get('number'),
        name=submission.props.get('title', language.name + ' dictionary'),
        description=submission.description,
        language_pk=language.pk,
        published=datetime.date(*map(int, date_published.split('-'))),
        doi=sinfo.get('doi'),
        git_repo=git_https,
        jsondata=submission.props)


def make_dictionaries(submissions, submission_info, languages):
    """Return dictionary objects for all submissions."""
    return {
        submission.id: make_dictionary(
            submission,
            submission_info[submission.id],
            languages[submission.glottocode])
        for submission in submissions.values()}


def make_contributors(submissions):
    """Return all contributors to Dictionaria (authors and editors)."""
    contributors = {
        ed.id: common.Contributor(id=ed.id, name=ed.name)
        for ed in DICTIONARIA_EDITORS}
    dictionary_authors = defaultdict(list)
    for submission in submissions.values():
        for author in submission.md['authors']:
            if isinstance(author, str):
                name = author
                address = None
                spec = {}
            elif isinstance(author, dict):
                name = author['name']
                address = author.get('affiliation')
                spec = author
            else:
                raise TypeError('author must be string or dict')
            human_name = HumanName(name)
            id_ = slug(f'{human_name.last}{human_name.first}')
            if id_ not in contributors:
                contributors[id_] = common.Contributor(
                    id=id_,
                    name=name,
                    address=address,
                    url=spec.get('url'),
                    email=spec.get('email'))
            dictionary_authors[submission.id].append({
                'id': id_,
                'primary': spec.get('primary') or True})
    return contributors, dictionary_authors


def iter_editors(contributors, dataset):
    """Return specialised editor objects for Dictionaria's editors."""
    return (
        common.Editor(
            dataset_pk=dataset.pk,
            contributor_pk=contributors[ed.id].pk,
            ord=number)
        for number, ed in enumerate(DICTIONARIA_EDITORS, 1))


def iter_dictionary_authors(dictionary_authors, contributors, dictionaries):
    """Return specialised author objects for dictionary authors."""
    return (
        common.ContributionContributor(
            contribution_pk=dictionaries[submission_id].pk,
            contributor_pk=contributors[author['id']].pk,
            ord=number,
            primary=author['primary'])
        for submission_id, authors in dictionary_authors.items()
        for number, author in enumerate(authors, 1))


def collect_link_labels(id_name_pairs):
    """Map object ids to their names to use as labels in markdown links."""
    labels = defaultdict(dict)
    for id_, name in id_name_pairs:
        obj_id, submission_id = id_.split('-', maxsplit=1)
        labels[obj_id][submission_id] = name
    return labels


def add_formatted_description(dictionary, request, entry_labels, source_labels):
    """Render markdown descriptions *destructively* to HTML."""
    if not dictionary.description:
        return
    soup = BeautifulSoup(
        markdown(dictionary.description, extensions=['tables']),
        'html.parser')
    for a in soup.find_all('a', href=True):
        if a['href'] == 'entry':
            if a.string in entry_labels[dictionary.id]:
                a['class'] = 'lemma'
                a['href'] = request.route_path(
                    'unit', id=f'{dictionary.id}-{a.string}')
                a.string = entry_labels[dictionary.id][a.string]
        elif a['href'] == 'source':
            if a.string in source_labels[dictionary.id]:
                a['href'] = request.route_path(
                    'source', id=f'{dictionary.id}-{a.string}')
                a.string = source_labels[dictionary.id][a.string]
    dictionary.description, dictionary.toc = toc(soup)


def main(args):
    """Fill data base."""
    # get input from cli

    published = input('[i]nternal or [e]xternal data (default: e): ').strip().lower() != 'i'
    dict_id = input("dictionary id or 'all' for all dictionaries (default: all): ").strip()

    # load meta-data

    catalog_ini = cldfcatalog.Config.from_file()
    concepticon_path = catalog_ini.get_clone('concepticon')
    glottolog_path = catalog_ini.get_clone('glottolog')

    def is_selected(sid):
        if not dict_id or dict_id == sid or dict_id == 'all':
            return True
        else:
            print(f'{sid}: not selected')
            return False

    with open(INTERNAL_REPO / 'contributions.json', encoding='utf-8') as f:
        submission_info = json.load(f)
    submission_info = {
        sid: sinfo
        for sid, sinfo in submission_info.items()
        if sinfo['published'] == published and is_selected(sid)}

    data_dirs = (
        (sid, download_data(sid, sinfo, INTERNAL_REPO / 'datasets'))
        for sid, sinfo in submission_info.items())
    submissions = {
        sid: Submission.from_cldfbench(sid, data_dir)
        for sid, data_dir in data_dirs}

    # build data base

    fts.index('fts_index', Word.fts, DBSession.bind)
    DBSession.execute("CREATE EXTENSION IF NOT EXISTS unaccent WITH SCHEMA public;")

    dataset = common.Dataset(
        id=dictionaria.__name__,
        name="Dictionaria",
        description="The Dictionary Journal",
        published=datetime.date(2017, 3, 30),
        contact='dictionaria@eva.mpg.de',
        domain='dictionaria.clld.org',
        publisher_name="Max Planck Institute for Evolutionary Anthropology",
        publisher_place="Leipzig",
        publisher_url="https://eva.mpg.de",
        license="http://creativecommons.org/licenses/by/4.0/",
        jsondata={
            'license_icon': 'cc-by.png',
            'license_name': 'Creative Commons Attribution 4.0 International License'})
    DBSession.add(dataset)

    DBSession.add_all(iter_gloss_abbrevs(LGR_ABBRS))

    print('loading concepts ...')
    concepticon = Concepticon(concepticon_path)
    comparison_meanings = make_comparison_meanings(concepticon)
    DBSession.add_all(comparison_meanings.values())
    print('... done')

    print('loading languages...')
    # TODO: add glottolog info?
    # (that's probably done somewhere later but it should be done here)
    languages = make_languages(submissions)
    DBSession.add_all(languages.values())
    print('... done')

    contributors, dictionary_authors = make_contributors(submissions)
    DBSession.add_all(contributors.values())

    DBSession.flush()

    dictionaries = make_dictionaries(submissions, submission_info, languages)
    DBSession.add_all(dictionaries.values())

    DBSession.add_all(iter_editors(contributors, dataset))

    DBSession.flush()

    DBSession.add_all(
        iter_dictionary_authors(dictionary_authors, contributors, dictionaries))

    DBSession.flush()

    for submission in submissions.values():
        print('loading', submission.id, '...')
        submission.add_to_database(
            dictionaries[submission.id],
            languages[submission.glottocode],
            comparison_meanings)
        print('... done')

    load_families(
        Data(),
        [v for v in DBSession.query(Variety) if re.match('[a-z]{4}[0-9]{4}', v.id)],
        glottolog_repos=glottolog_path)

    source_labels = collect_link_labels(
        DBSession.query(common.Source.id, common.Source.name))
    entry_labels = collect_link_labels(
        DBSession.query(common.Unit.id, common.Unit.name))
    for d in DBSession.query(Dictionary):
        add_formatted_description(
            d, args.env['request'], entry_labels, source_labels)

    DBSession.flush()


def count_unit_media_files(contrib, mtype):
    """Return count of media files associated to entries."""
    word_files = (
        DBSession.query(common.Unit_files)
        .join(Word, common.Unit_files.object_pk == Word.pk)
        .filter(Word.dictionary_pk == contrib.pk)
        .filter(common.Unit_files.mime_type.ilike(f'{mtype}/%')))
    meaning_files = (
        DBSession.query(Meaning_files)
        .join(Meaning, Meaning_files.object_pk == Meaning.pk)
        .join(Word, Meaning.word_pk == Word.pk)
        .filter(Word.dictionary_pk == contrib.pk)
        .filter(Meaning_files.mime_type.ilike(f'{mtype}/%')))
    return word_files.count() + meaning_files.count()


def count_unit_example_files(contrib):
    """Return count of audio files associated to examples."""
    example_files = (
        DBSession.query(common.Sentence_files)
        .join(common.Sentence, common.Sentence_files.object_pk == common.Sentence.pk)
        .filter(Example.dictionary_pk == contrib.pk)
        .filter(common.Sentence_files.mime_type.ilike('audio/%')))
    return example_files.count()


def prime_cache(_args):
    """Denormalise data base.

    This procedure should be separate from the db initialization, because
    it will have to be run periodically whenever data has been updated
    (though to be completely honest, nobody ever does that).
    """
    print('counting comparison meanings ...')
    for concept in DBSession.query(ComparisonMeaning).options(
        joinedload(common.Parameter.valuesets).joinedload(common.ValueSet.values),
    ):
        concept.representation = sum(len(vs.values) for vs in concept.valuesets)
        if concept.representation == 0:
            concept.active = False
    print('... done')

    print('counting media files ...')
    for d in DBSession.query(Dictionary):
        q = DBSession.query(Word).filter(Word.dictionary_pk == d.pk)
        d.count_words = q.count()
        sds = set(chain.from_iterable(w.semantic_domain_list for w in q))
        d.semantic_domains = join(sorted(sds))
        d.count_audio = count_unit_media_files(d, 'audio')
        d.count_example_audio = count_unit_example_files(d)
        d.count_image = count_unit_media_files(d, 'image')

        word_pks = [w.pk for w in d.words]
        choices = {}
        custom_cols = chain(
            d.jsondata.get('custom_fields', ()),
            d.jsondata.get('second_tab', ()))
        for col in custom_cols:
            data_values = DBSession.query(common.Unit_data.value)\
                .filter(common.Unit_data.object_pk.in_(word_pks))\
                .filter(common.Unit_data.key == col)\
                .filter(not_(common.Unit_data.key.like('lang-%')))\
                .distinct()
            values = [r[0] for r in data_values]
            if values and len(values) < 40:
                choices[col] = sorted(values)
        if choices:
            d.update_jsondata(choices=choices)
    DBSession.flush()
    print('... done')

    print('counting examples ...')
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
    print('done...')
