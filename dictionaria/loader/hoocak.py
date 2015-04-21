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
    'adv.': 'adverb',
    'n.': 'noun',
    'affix': 'affix',
    'v.tr.': 'transitive verb',
    'pron.': 'pronoun',
    'v.act.': 'active verb',
    'num.': 'numeral',
    'v.inact.': 'inactive verb',
}


def load(id_, data, files_dir):
    #d = Dictionary(path(__file__).dirname().joinpath('Hocaklex_utf8_oA_ld100.lex'))
    d = Dictionary(path(__file__).dirname().joinpath('Hoocak_lex_ld100.lex'))
    d.entries = filter(lambda r: r.get('lx'), d.entries)

    lang = data['Language'][id_]
    vocab = data['Dictionary'][id_]

    sd = common.UnitParameter(id='sd', name='semantic domain')
    DBSession.add(sd)
    DBSession.flush()

    for name in d.values('sd'):
        if name.startswith('??'):
            continue
        p = data.add(common.UnitDomainElement, name, id='sd-'+slug(name), name=name)
        p.unitparameter_pk = sd.pk

    DBSession.flush()

    for i, row in enumerate(d.entries):
        w = data.add(
            models.Word, row.get('lx'),
            id='%s-%s' % (id_, i),
            name=row.get('lx'),
            description='; '.join(row.getall('me')),
            dictionary=vocab)
        w.language = lang

        if row.get('hm'):
            try:
                w.number = int(row.get('hm'))
            except:
                print '---->', row.get('hm')

        DBSession.flush()

        for marker, label in [
            ('al', 'alternative form'),
            ('cf', 'conjugated form'),
            ('cc', 'conjugation class'),
            ('mp', 'metaphony'),
            ('is', 'internal structure')
        ]:
            for k, name in enumerate(row.getall(marker)):
                DBSession.add(
                    common.Unit_data(key=label, value=name, ord=k, object_pk=w.pk))

        for marker in ['pc', 'sf']:
            for l, spec in enumerate(row.getall(marker)):
                try:
                    p, mimetype = spec
                except:
                    p = spec
                    mimetype = 'image/jpeg' if marker == 'pc' else 'audio/mpeg'
                p = path(__file__).dirname().joinpath(*p.split('\\'))
                with open(p, 'rb') as fp:
                    f = common.Unit_files(
                        name=p.basename(),
                        id=mimetype.split('/')[0],
                        mime_type=mimetype,
                        ord=l + 1,
                        object_pk=w.pk)
                    DBSession.add(f)
                    DBSession.flush()
                    DBSession.refresh(f)
                    f.create(files_dir, fp.read())

        for j, name in enumerate(row.getall('sd')):
            if name.startswith('??'):
                continue
            DBSession.add(common.UnitValue(
                id='sd-%s-%s' % (i, j),
                unit=w,
                unitparameter=sd,
                unitdomainelement=data['UnitDomainElement'][name],
                contribution=vocab,
            ))

        meaning_prefix = ''
        for j, name in enumerate(row.getall('ps')):
            if name.startswith('??'):
                continue
            if name == "v.inact":
                name += '.'
            if name.startswith('v.'):
                meaning_prefix = 'to '
            elif name.startswith('n.'):
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

        for j, name in enumerate(row.getall('me')):
            key = '%s%s' % (meaning_prefix, name.lower())
            if key in data['Meaning']:
                meaning = data['Meaning'][key]
                vsid = '%s-%s' % (key, id_),
                if vsid in data['ValueSet']:
                    vs = data['ValueSet'][vsid]
                else:
                    vs = data.add(
                        common.ValueSet, vsid,
                        id='%s-%s' % (id_, meaning.id),
                        language=lang,
                        contribution=vocab,
                        parameter=meaning)

                DBSession.add(models.Counterpart(
                    id='%s-%s-%s' % (id_, i, j),
                    name=row.get('lx'),
                    valueset=vs,
                    word=w))

    DBSession.flush()

