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
from daguerre.smugmugsync import *

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

    group_projects = parser.add_argument_group('Operations', 'Import.')
    group_projects.add_argument('-i',
                                '--import',
                                dest='import_cards',
                                action='store',
                                nargs="+",
                                metavar="CARD_NAME",
                                help='import picture from specific cards, or "all".')

    group_maintenance = parser.add_argument_group('Operations', 'Maintenance.')
    group_maintenance.add_argument('-r',
                                   '--refresh',
                                   dest='refresh_files',
                                   action='store',
                                   nargs="*",
                                   metavar="DIRECTORY",
                                   help='refresh filenames')
    group_maintenance.add_argument('--clean-raw',
                                   dest='clean_raw',
                                   action='store',
                                   nargs="?",
                                   const="all",
                                   metavar="DIRECTORY",
                                   help='Clean up single CR2 files (in a directory).')
    group_export = parser.add_argument_group('Operations', 'Export.')
    group_export.add_argument('-x',
                              '--export',
                              dest='export_files',
                              action='store',
                              nargs=1,
                              metavar="EXPORT_DIRECTORY",
                              help='export pictures to a directory.')
    group_export.add_argument('-t',
                              '--tags',
                              dest='tags',
                              action='store',
                              nargs="*",
                              metavar="TAG",
                              help='filter tags when exporting.')
    group_export.add_argument('--from',
                              dest='from',
                              action='store',
                              nargs=1,
                              metavar="FROM_DATE",
                              help='filter by date when exporting.')
    group_export.add_argument('--to',
                              dest='to',
                              action='store',
                              nargs=1,
                              metavar="TO_DATE",
                              help='filter by date when exporting.')
    group_export.add_argument('-s',
                              '--sync-with-smugmug',
                              dest='sync',
                              action='store',
                              nargs="?",
                              const="all",
                              metavar="DIRECTORY",
                              help='Sync photos with smugmug account.')
    group_export.add_argument('--public',
                              dest='public_only',
                              action='store_true',
                              default=False,
                              help='Only export pictures tagged as public.')

    args = parser.parse_args()
    logger.debug(args)

    #TODO if args.config is not None...

    with Library(CONFIG_FILE) as l:
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
        if args.sync is not None:
            try:
                l.sync(args.sync, args.public_only)
            except AssertionError as err:
                print("Subdirectory %s does not exist." % args.sync)


if __name__=="__main__":
    main()

