from __future__ import unicode_literals
from datetime import date
from itertools import groupby
import re

import transaction
from nameparser import HumanName
from sqlalchemy.orm import joinedload_all, joinedload
from clldutils.misc import slug
from clld.util import LGR_ABBRS
from clld.scripts.util import Data, initializedb
from clld.db.meta import DBSession
from clld.db.models import common
from clldclient.concepticon import Concepticon
from clld_glottologfamily_plugin.util import load_families

import dictionaria
from dictionaria.models import ComparisonMeaning, Dictionary, Word, Variety
from dictionaria.lib.submission import REPOS, Submission


def main(args):
    data = Data()

    dataset = common.Dataset(
        id=dictionaria.__name__,
        name="Dictionaria",
        description="The Dictionary Journal",
        published=date(2015, 10, 1),
        contact='dictionaria@eva.mpg.de',
        domain='dictionaria.clld.org',
        license="http://creativecommons.org/licenses/by/4.0/",
        jsondata={
            'license_icon': 'cc-by.png',
            'license_name': 'Creative Commons Attribution 4.0 International License'})

    ed = data.add(
        common.Contributor, 'hartmanniren', id='hartmanniren', name='Iren Hartmann')
    common.Editor(dataset=dataset, contributor=ed)
    DBSession.add(dataset)

    for id_, name in LGR_ABBRS.items():
        DBSession.add(common.GlossAbbreviation(id=id_, name=name))

    comparison_meanings = {}
    comparison_meanings_alt_labels = {}

    print('loading concepts ...')

    concepticon = Concepticon()
    for i, concept_set in enumerate(concepticon.resources('parameter').members):
        if args.no_concepts:
            break
        concept_set = concepticon.resource(concept_set)
        cm = ComparisonMeaning(
            id=concept_set.id,
            name=concept_set.name.lower(),
            description=concept_set.description,
            concepticon_url='%s' % concept_set.uriref)
        DBSession.add(cm)
        comparison_meanings[cm.name] = cm
        for label in concept_set.alt_labels:
            comparison_meanings_alt_labels.setdefault(label.lower(), cm)

    DBSession.flush()

    print('... done')

    comparison_meanings = {k: v.pk for k, v in comparison_meanings.items()}
    comparison_meanings_alt_labels = {
        k: v.pk for k, v in comparison_meanings_alt_labels.items()}

    submissions = []

    for submission in REPOS.joinpath(
            'submissions-internal' if args.internal else 'submissions').glob('*'):
        if not submission.is_dir():
            continue

        try:
            submission = Submission(submission)
        except ValueError:
            continue

        md = submission.md
        if md is None:
            continue

        id_ = submission.id
        if args.dict and args.dict != id_ and args.dict != 'all':
            continue
        lmd = md['language']

        language = data['Variety'].get(lmd['glottocode'])
        if not language:
            language = data.add(
                Variety, lmd['glottocode'], id=lmd['glottocode'], name=lmd['name'])

        if '-' not in md['published']:
            md['published'] = md['published'] + '-01-01'
        dictionary = data.add(
            Dictionary,
            id_,
            id=id_,
            name=lmd['name'] + ' Dictionary',
            description=submission.description,
            language=language,
            published=date(*map(int, md['published'].split('-'))),
            jsondata=dict(custom_fields=md.get('custom_fields', [])))

        for i, cname in enumerate(md['authors']):
            name = HumanName(cname)
            cid = slug('%s%s' % (name.last, name.first))
            contrib = data['Contributor'].get(cid)
            if not contrib:
                contrib = data.add(common.Contributor, cid, id=cid, name=cname)
            DBSession.add(common.ContributionContributor(
                ord=i + 1,
                primary=True,
                contributor=contrib,
                contribution=dictionary))

        submissions.append((dictionary.id, language.id, submission))
    transaction.commit()

    for did, lid, submission in submissions:
        try:
            mod = __import__(
                'dictionaria.loader.' + submission.id, fromlist=['MARKER_MAP'])
            _marker_map = mod.MARKER_MAP
        except ImportError:
            _marker_map = {}

        marker_map = {}
        for k, v in submission.md.get('labels', {}).items():
            marker_map[k] = v

        for k, v in _marker_map.items():
            if k in marker_map:
                if isinstance(v, tuple):
                    marker_map[k] = (marker_map[k], v[1])
            else:
                marker_map[k] = v

        transaction.begin()
        print('loading %s ...' % submission.id)
        submission.load(
            did,
            lid,
            comparison_meanings,
            comparison_meanings_alt_labels,
            marker_map,
            args)
        transaction.commit()
        print('... done')

        #('hoocak', 'Hooca\u0328k', 43.5, -88.5, [('hartmanniren', 'Iren Hartmann')]),
        #('yakkha', 'Yakkha', 27.37, 87.93, [('schackowdiana', 'Diana Schackow')]),
        #('palula', 'Palula', 35.51, 71.84, [('liljegrenhenrik', 'Henrik Liljegren')], {}),
        #('daakaka', 'Daakaka', -16.27, 168.01, [('vonprincekilu', 'Kilu von Prince')],
        # {'published': date(2015, 9, 30), 'iso': 'bpa', 'glottocode': 'daka1243'}),
        #('teop', 'Teop', -5.67, 154.97, [('moselulrike', 'Ulrike Mosel')],
        # {'published': date(2015, 9, 30), 'iso': 'tio', 'glottocode': 'teop1238', 'encoding': 'latin1'}),

    transaction.begin()
    load_families(
        Data(),
        [v for v in DBSession.query(Variety) if re.match('[a-z]{4}[0-9]{4}', v.id)])


def prime_cache(cfg):
    """If data needs to be denormalized for lookup, do that here.
    This procedure should be separate from the db initialization, because
    it will have to be run periodically whenever data has been updated.
    """
    for meaning in DBSession.query(ComparisonMeaning).options(
        joinedload_all(common.Parameter.valuesets, common.ValueSet.values)
    ):
        meaning.representation = sum([len(vs.values) for vs in meaning.valuesets])
        if meaning.representation == 0:
            meaning.active = False

    q = DBSession.query(Word)\
        .order_by(common.Unit.language_pk, common.Unit.name, common.Unit.pk)\
        .options(joinedload(Word.meanings))
    for _, words in groupby(q, lambda u: u.name):
        words = list(words)
        for i, word in enumerate(words):
            word.description = ' / '.join(m.name for m in word.meanings if m.language == 'en')
            word.number = i + 1 if len(words) > 1 else 0
            DBSession.add(common.Unit_data(
                object_pk=word.pk,
                key='Semantic domain',
                value=' / '.join(m.semantic_domain for m in word.meanings if m.semantic_domain)))

    for d in DBSession.query(Dictionary).options(joinedload(Dictionary.words)):
        d.count_words = len(d.words)


if __name__ == '__main__':
    initializedb(
        (("--internal",), dict(action='store_true')),
        (("--no-concepts",), dict(action='store_true')),
        (("--dict",), dict()),
        create=main, prime_cache=prime_cache)
