"""Daguerre.
A script to deal with pictures.
"""

from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path


setup(
    name='daguerre',
    version='0.1.0',
    description='A script to deal with pictures.',
    url='https://github.com/barsanuphe/daguerre',
    author='barsanuphe',
    author_email='monadressepublique@gmail.com',
    license='GPLv3+',
    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 2 - Pre-Alpha'
        'Intended Audience :: Developers',
        'Operating System :: POSIX :: Linux',
        'Topic :: Multimedia :: Graphics',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Programming Language :: Python :: 3.4',
    ],
    keywords='daguerre pictures exif',
    packages=['daguerre'],

    # note: attic has unresolved dependancies (blosc) for now
    install_requires=['pyyaml', 'notify2', 'progressbar'],# ,'PIL', 'xdg'],


    # If there are data files included in your packages that need to be
    # installed, specify them here.
    #package_data={
        #'sample': ['package_data.dat'],
    #},

    ## To provide executable scripts, use entry points in preference to the
    ## "scripts" keyword. Entry points provide cross-platform support and allow
    ## pip to create the appropriate form of executable for the target platform.
    entry_points={
        'console_scripts': [
            'daguerre=daguerre:main',
        ],
    },

)
