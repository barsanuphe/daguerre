"""Daguerre.
A script to deal with pictures.
"""

from setuptools import setup

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

    install_requires=['pyyaml', 'notify2', 'progressbar', 'rauth'],  # ,'PIL', 'xdg'],

    entry_points={
        'console_scripts': [
            'daguerre=daguerre:main',
        ],
    },

)
