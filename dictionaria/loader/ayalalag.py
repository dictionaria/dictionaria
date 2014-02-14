# coding: utf8
from __future__ import unicode_literals
import re
from datetime import date

from sqlalchemy import create_engine
from path import path
from clld.db.meta import DBSession
from clld.db.models import common
from clld.util import slug

import dictionaria
from dictionaria import models
from dictionaria.lib.sfm import Dictionary


DB = 'postgresql://robert@/wold'
POS_MAP = {
    'n adj': 'noun',
    'vi': 'inactive verb',
    'num': 'numeral',
    'vt': 'transitive verb',
    'conj': 'other',
    'vt vi': 'verb',
    'adv': 'adverb',
    'pron': 'pronoun',
    'neg': 'other',
    'pron (resp)': 'pronoun',
    'deic': 'other',
    'quant': 'other',
    'adj': 'adjective',
    'prep': 'other',
    'qmrk': 'other',
    'wh': 'other',
    'Q': 'other',
    'part': 'other',
    'vdt': 'other',
    'det': 'other',
    'n': 'noun',
    'q': 'other',
    'pron (conf)': 'pronoun',
    'v': 'verb',
}


def load(id_, data):
    d = Dictionary(path(__file__).dirname().joinpath('yalalag.bak'), encoding='latin1')
    d.entries = filter(lambda r: r.get('lx') and r.get('ge'), d.entries)

    lang = data.add(common.Language, id_, id=id_, name='Yalálag Zapotec',
                    latitude=17.18574, longitude=-96.17891)
    #
    # TODO:
    #
    # iso code zpu
    contrib = data.add(
        common.Contributor, 'heriberto', id='avelinoheriberto', name='Heriberto Avelino')
    DBSession.flush()

    number = max([int(dd.id) for dd in data['Dictionary'].values()] + [0])
    vocab = data.add(
        models.Dictionary, id_, id=str(number + 1),
        name='Yalálag Zapotec Dictionary',
        language=lang,
        published=date(2013, 5, 5))
    DBSession.flush()

    DBSession.add(common.Contribution_files(
        object_pk=vocab.pk,
        name='description',
        file=common.File(
            name='yalalag.pdf',
            mime_type='application/pdf',
            content=open(path(__file__).dirname().joinpath('yalalag.pdf')).read())))

    old_db = create_engine(DB)
    for row in old_db.execute("select * from meaning"):
        data.add(
            common.ValueSet, '%s-%s' % (row['label'].lower(), id_),
            id='%s-%s' % (id_, row['id'].replace('.', '-')),
            language=lang,
            contribution=vocab,
            parameter=data['Meaning'][row['id']])

    DBSession.flush()

    ue = common.UnitParameter(id='ue', name='usage')
    DBSession.add(ue)
    DBSession.flush()

    for name in d.values('ue'):
        p = data.add(common.UnitDomainElement, name, id='ue-'+slug(name), name=name)
        p.unitparameter_pk = ue.pk

    for i, row in enumerate(d.entries):
        w = data.add(
            models.Word, row.get('lx'),
            id='%s-%s' % (id_, i),
            name=row.get('lx'),
            description='; '.join(row.getall('ge')),
            dictionary=vocab)
        w.language = lang

        DBSession.flush()

        for marker in [
            'bw', 'ce', 'cf', 'de', 'dn', 'et', 'gv', 'lc', 'mr', 'nt',
            'ph', 're', 'rn', 'sc', 'se', 'un', 'va',
        ]:
            for k, name in enumerate(row.getall(marker)):
                DBSession.add(
                    common.Unit_data(key=marker, value=name, ord=k, object_pk=w.pk))

        for j, name in enumerate(row.getall('ue')):
            DBSession.add(common.UnitValue(
                id='ue-%s-%s' % (i, j),
                unit=w,
                unitparameter=ue,
                unitdomainelement=data['UnitDomainElement'][name],
                contribution=vocab,
            ))

        meaning_prefix = ''
        for j, name in enumerate(row.getall('ps')):
            if POS_MAP[name] == 'verb' or ' verb' in POS_MAP[name]:
                meaning_prefix = 'to '
            elif POS_MAP[name] == 'noun':
                meaning_prefix = 'the '
            if j > 0:
                # only one part-of-speech value per entry!
                raise ValueError
            DBSession.add(common.UnitValue(
                id='pos-%s-%s' % (id_, i),
                unit=w,
                unitparameter=data['UnitParameter']['pos'],
                unitdomainelement=data['UnitDomainElement'][POS_MAP[name]],
                contribution=vocab,
            ))

        for j, name in enumerate(row.getall('ge')):
            if name.startswith(meaning_prefix):
                meaning_prefix = ''
            key = '%s%s-%s' % (meaning_prefix, name.lower(), id_)
            if key in data['ValueSet']:
                value = data.add(
                    models.Counterpart, '%s-%s' % (i, j),
                    id='%s-%s-%s' % (id_, i, j),
                    name=row.get('lx'),
                    valueset=data['ValueSet'][key],
                    word=w)

        if row.get('xv'):
            ex = data.add(
                common.Sentence, i,
                id='%s-%s' % (id_, i),
                name=row.get('xv'),
                description=row.get('xe', default=''))
            DBSession.add(models.WordSentence(word=w, sentence=ex))

    DBSession.flush()

    DBSession.add(common.ContributionContributor(
        ord=1,
        primary=True,
        contributor_pk=contrib.pk,
        contribution_pk=vocab.pk))

    DBSession.flush()
