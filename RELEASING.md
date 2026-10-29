# Releasing the Dictionaria clld app

```shell
git clone https://github.com/clld/dictionaria
git clone --depth 1 https://github.com/dictionaria/dictionaria-intern
cd dictionaria
pip install -e .[test]
```

```shell
clld initdb development.ini
```

```shell
pytest
```

Store the tested requirements:
```shell
pip freeze > requirements.txt
```

Store a db dump:
```shell
pg_dump -xO dictionaria > dictionaria.sql
zip dictionaria.sql.zip dictionaria.sql
rm dictionaria.sql
```

