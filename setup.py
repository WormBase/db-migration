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
    name='wormbase-db-build',
    version='0.1',
    url='http://www.wormbase.org/',
    author='Matt Russell, EMBL-EBI',
    author_email='matthew.russell@wormbase.org',
    description='Build the WormBase datomic database on AWS',
    license='MIT',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    include_package_data=True,
    install_requires=INSTALL_REQUIRES,
    entry_points={
        'console_scripts': [
            'wb-db-build=wormbase.db.taskmanager:cli',
            'wb-db-install=wormbase.db.install:cli',
            'wb-db-run=wormbase.db.runcommand:cli'
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
            'Sphinx',
            # 'sphinx_bootstrap_theme',
            'sphinx_rtd_theme'
        ]
    }
)
