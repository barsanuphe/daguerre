# -*- coding: utf-8 -*-

#so that parsing this with python2 does not raise SyntaxError
from __future__ import print_function

import os, subprocess, shutil, sys, datetime
import time
import argparse

from daguerre.checks import *
from daguerre.helpers import *
from daguerre.logger import *
from daguerre.picture import *
from daguerre.movie import *
from daguerre.library import *

# default config file name
CONFIG_FILE = "daguerre.yaml"

def main():
    logger.info( "\n# D A G U E R R E #\n" )

    parser = argparse.ArgumentParser(description='Daguerre.\nA script '
                                     'to deal with pictures.')

    group_config = parser.add_argument_group('Configuration',
                                             'Manage configuration files.')
    group_config.add_argument('--config',
                              dest='config',
                              action='store',
                              metavar="CONFIG_FILE",
                              nargs=1,
                              help='Use an alternative configuration file.')
    group_config.add_argument('--encrypt',
                              dest='encrypt',
                              action='store_true',
                              default=False,
                              help='Toggle encryption on the configuration '
                                   'file.')

    group_projects = parser.add_argument_group('Operations', 'Actions.')
    group_projects.add_argument('-i',
                                '--import',
                                dest='import_cards',
                                action='store',
                                nargs="+",
                                metavar="CARD_NAME",
                                help='import picture from specific cards, or "all".')
    group_projects.add_argument('-r',
                                '--refresh',
                                dest='refresh_files',
                                action='store',
                                nargs="*",
                                metavar="DIRECTORY",
                                help='refresh filenames')
    group_projects.add_argument('-x',
                                '--export',
                                dest='export_files',
                                action='store',
                                nargs=1,
                                metavar="EXPORT_DIRECTORY",
                                help='export pictures to a directory.')
    group_projects.add_argument('-t',
                                '--tags',
                                dest='tags',
                                action='store',
                                nargs="*",
                                metavar="TAG",
                                help='filter tags when exporting.')
    group_projects.add_argument('--from',
                                dest='from',
                                action='store',
                                nargs=1,
                                metavar="FROM_DATE",
                                help='filter by date when exporting.')
    group_projects.add_argument('--to',
                                dest='to',
                                action='store',
                                nargs=1,
                                metavar="TO_DATE",
                                help='filter by date when exporting.')
    group_projects.add_argument('--clean-raw',
                                dest='clean_raw',
                                action='store',
                                nargs="?",
                                const="all",
                                metavar="DIRECTORY",
                                help='Clean up single CR2 files (in a directory).')
    # group_projects.add_argument('-b',
                                # '--backup',
                                # dest='backup',
                                # action='store_true',
                                # default=False,
                                # help='backup selected repositories.')

    args = parser.parse_args()
    logger.debug(args)

    with Library(CONFIG_FILE) as l:
        logger.debug( "Directory: %s" % l.config_file.directory )
        logger.debug( "Lenses: %s" % l.config_file.lenses)
        logger.debug( "Cameras: %s" % l.config_file.cameras)
        logger.debug( "Mount root: %s" % l.config_file.mount_root)

        if args.import_cards is not None:
            l.import_from_cards(args.import_cards)
            os.sync()
            logger.info( "Done, card can be removed.")
            notify_this("Daguerre has finished importing pictures,"
                        "it is safe to remove the CF card.")
        if args.refresh_files is not None:
            print("refresh")
            l.refresh()
        if args.clean_raw is not None:
            try:
                l.remove_single_raw_files(args.clean_raw)
            except AssertionError as err:
                print("Subdirectory %s does not exist." % args.clean_raw)


if __name__=="__main__":
    main()
