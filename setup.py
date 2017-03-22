from setuptools import setup, find_packages

requires = [
    'pathlib2>=2.2.1',
    'clld>=3.2.4',
    'clldmpg>=2.3.3',
    'clld-glottologfamily-plugin>=2.0.0',
    'clldutils>=1.9.0',
    'transliterate',
    'pyconcepticon>=1.1.0',
]

tests_require = [
    'WebTest >= 1.3.1',  # py3 compat
    'mock',
]

setup(
    name='dictionaria',
    version='0.0',
    description='dictionaria',
    long_description='',
    classifiers=[
        "Programming Language :: Python",
        "Framework :: Pyramid",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
    ],
    author='Robert Forkel',
    author_email='robert_forkel@eva.mpg.de',
    url='http://clld.org',
    keywords='web pyramid pylons',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=requires,
    tests_require=tests_require,
    test_suite="dictionaria",
    entry_points="""\
        [paste.app_factory]
        main = dictionaria:main
""")
