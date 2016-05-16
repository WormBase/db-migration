import os
from setuptools import find_packages, setup

here = os.path.abspath(os.path.dirname(__file__))
version = __import__('harp').__version__


def _read_file(name):
    with open(os.path.join(here, name)) as fp:
        return fp.read()


README = _read_file('README.rst')
CHANGES = _read_file('CHANGES.rst')

setup(
    name='wormbase_db_build',
    version=version,
    url='http://www.wormbase.org/',
    author='Matt Russell, EMBL-EBI',
    author_email='matthew.russell@wormbase.org',
    description='Build the WormBase datomic database on AWS',
    license='MIT',
    packages=find_packages('src'),
    include_package_data=True,
    entry_points={'console_scripts': [
        'wb-fetch-release = wormbase.pseudoace:download_release_binary',
        'wb-aws-build = wormbase.build:main'
    ]},
    install_requires=[
        'boto3',
        'click'
    ],
    zip_safe=False,
    classifiers=[
        'Development Status :: 1 - Pre-Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)
