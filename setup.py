# Encoding: UTF-8

from setuptools import setup, find_packages
from os import listdir

setup(
    name='luna',
    version='0.0.1',

    packages=find_packages(),

    install_requires=[
        'pymongo==2.5.2',
        'tornado==2.2.1',
        'python-hostlist==1.14'
    ],

    dependency_links=[],

    package_data={

    },
    data_files=[
        ('usr/share/luna/templates', [ 'templates/' + e for e in listdir('templates') ] )
    ],
    include_package_data=True
)
