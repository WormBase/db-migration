import os
from setuptools import find_packages, setup

here = os.path.abspath(os.path.dirname(__file__))


def _read_file(name):
    with open(os.path.join(here, name)) as fp:
        return fp.read()


README = _read_file('README.rst')
CHANGES = _read_file('CHANGES.rst')
INSTALL_REQUIRES = _read_file('requirements.txt').splitlines()

setup(
    name='azanium',
    version='0.4.dev0',
    url='http://www.wormmbase.org/',
    author='Matt Russell, EMBL-EBI',
    author_email='matthew.russell@wormbase.org',
    description='WormBase Database Migration Tools',
    long_description="""\
    Provides command line interfaces to run the database migration steps
    for converting the WormBase ACeDB database to Datomic.
    """,
    license='MIT',
    keywords='WormBase, ACeDB, C. Elegans, Model Organisms',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    include_package_data=True,
    install_requires=INSTALL_REQUIRES,
    entry_points={
        'console_scripts': [
            'azanium=azanium.__main__:cli',
        ],
    },
    zip_safe=False,
    classifiers=[
        'Development Status :: 1 - Pre-Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Topic :: Software Development :: Libraries :: Python Modules :: Tools',
    ],
    extras_require={
        'dev': [
            'Sphinx==1.4.3',
            'sphinx_rtd_theme==0.1.9',
            'travis-sphinx==1.4.2',
            'zest.releaser[recommended]==6.6.4',
        ]
    }
)