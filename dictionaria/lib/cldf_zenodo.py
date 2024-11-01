# published

import pathlib

from pycldf.ext.discovery import get_dataset


def download_from_doi(doi, outdir=pathlib.Path('.')):
    _ = get_dataset(f'https://doi.org/{doi}', outdir)
    return outdir
