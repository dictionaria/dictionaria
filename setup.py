from setuptools import setup, find_packages

requires = [
    'clld>=2.1.1',
    'clldmpg>=2.0.0',
    'clld-glottologfamily-plugin',
    'clldutils>=0.5',
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
        [console_scripts]
        dictionaria = dictionaria.scripts.cli:main
""")
