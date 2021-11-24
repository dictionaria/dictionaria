Source code of the Dictionaria Webapp
=====================================

see [https://dictionaria.clld.org/](https://dictionaria.clld.org/)

Rebuilding the database(s)
--------------------------

### Prerequisite 1: `pg_collkey`

The database requires the [`pg_collkey`][pg_collkey] extension for PostgreSQL.
On Ubuntu 20.04 (and possibly most other Linux distros) `pg_collkey` is not in
the standard repos and needs to be compiled manually.

[pg_collkey]: https://github.com/ccutrer/pg_collkey

*Note:*
On some systems the `sudo make install` command shows the following error:

    make: icu-config: Command not found
    ...
    make: *** [/usr/lib/postgresql/12/lib/pgxs/src/makefiles/pgxs.mk:233: install] Error 1

To fix this adjust the path variables ICU_CFLAGS, ICU_LDFLAGS,
PG_INCLUDE_DIR, PG_PKG_LIB_DIR in the `Makefile` according to your OS
and settings.  E.g. on Ubuntu change ICU_CFLAGS and ICU_LDFLAGS to the
following:

```make
ICU_CFLAGS = `pkg-config --clfags icu-uc`
ICU_LDFLAGS = `pkg-config --libs icu-uc`
```

### Prerequisite 2: Glottolog and Concepticon

Dictionaria relies on both the [Glottolog][glottolog] and
[Concepticon][concepticon] data.  It will find them using
[cldfcatalog][cldfcatalog].

[glottolog]: https://github.com/glottolog/glottolog
[concepticon]: https://github.com/concepticon/concepticon-data
[cldfcatalog]: https://github.com/cldf/cldfcatalog

### Internal vs external datasets

There are two sets of datasets for Dictionaria:  The internal datasets and the
external datasets.  *External datasets* are the ones that have been released to
the public.  *Internal datasets* are the ones that are still being worked on and
that get served to a separate instance of the webapp, so the editors can give
the authors a preview on what their dictionaries will look like.

The metadata for both internal and external datasets is contained in the private
`dictionaria-intern` repository.  The `clld initdb` script will look for a clone
of this repository in `../dictionaria-intern`.  The `dictionaria-intern` repo
also contains a readme file on how to curate the datasets.

### Database initialisation

Thie `clld initdb` script will ask two questions:

 1. Do you want to load the internal or external datasets into the database?
    (`e` for external, `i` for internal)
 2. Do you want to add *all* or just one specific dataset to the database?
    This is useful for quick testing during development – repopulating the
    entire database can take a minute or two.

We usually load the internal and external datasets into separate databases:

    $ clld initdb development.ini
    ...
    [i]nternal or [e]xternal data (default: e): e
    dictionary id or 'all' for all dictionaries (default: all): all

    $ clld initdb development-intern.ini
    ...
    [i]nternal or [e]xternal data (default: e): i
    dictionary id or 'all' for all dictionaries (default: all): all
