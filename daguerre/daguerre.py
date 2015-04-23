# -*- coding: utf-8 -*-

#TODO: -i import
#TODO: -s sync (smugmug)
#TODO: -e extract best pictures
#TODO: -r refresh
#TODO: tester toutes les combinaisons de caméra/objo + ceux sans exif....

#so that parsing this with python2 does not raise SyntaxError
from __future__ import print_function

import os, subprocess, shutil, sys, datetime
import time, concurrent.futures, multiprocessing, argparse

from daguerre.checks import *
from daguerre.helpers import *
from daguerre.logger import *
from daguerre.picture import *
from daguerre.movie import *

# library & config are located next to this script
daguerre_dir = os.path.dirname(os.path.realpath(__file__))
CONFIG_FILE = os.path.join(daguerre_dir, "daguerre.yaml")
if not os.path.exists( os.path.join(daguerre_dir, "log") ):
    os.makedirs(os.path.join(daguerre_dir, "log"))

COLLECTION_DIR = ""
ARCHIVE_ROOT = ""
ACTIVE_ROOT = ""
MNT_ROOT = ""
LENSES = {}
CAMERAS = {}


def open_config(config_file):
    if os.path.exists(config_file):
        config = yaml.load(open(config_file, 'r'))
        global ARCHIVE_ROOT, ACTIVE_ROOT, MNT_ROOT, LENSES, CAMERAS
        try:
            ARCHIVE_ROOT = config["archive_root"]
            ACTIVE_ROOT = config["active_root"]
            MNT_ROOT = config["mnt_root"]

            if "lenses" in list(config.keys()):
                LENSES = config["lenses"]

            if "cameras" in list(config.keys()):
                CAMERAS = config["cameras"]

        except Exception as err:
            print("Missing config option: ", err)
            raise Exception("Invalid configuration file!")


def deal_with_cr2(cr2_filename):
    new = Picture(cr2_filename)
    new.read_metadata()
    new.to_dir(active = False, move = True)
    return new

def deal_with_jpg(jpg_filename):
    jpg = Picture(jpg_filename)
    jpg.read_metadata()
    jpg.to_dir(active = True, move = True)
    return jpg

def post_processing_jpg(picture):
    picture.losslessly_rotate()
    picture.convert_to_bw()

def deal_with_mov(mov_filename):
    mov = Movie(mov_filename)
    mov.read_metadata()
    # a copy + a move does not work, because reasons.
    # it looks like the copy does not block, and the move makes the source
    # disappear.
    # however, 2 copies + 1 delete works.
    mov.to_dir(active = False, move = False)
    mov.to_dir(active = True, move = False)
    os.remove(mov.path)
    return mov


def main():
    open_config(CONFIG_FILE)

    logger.info( "# D A G U E R R E #\n" )
    logger.info( "Archive:   %s"%ARCHIVE_ROOT )
    logger.info( "Workspace: %s\n"%ACTIVE_ROOT )

    logger.debug( "Lenses: %s"%LENSES)
    logger.debug( "Cameras: %s"%CAMERAS)
    logger.debug( "Mount root: %s"%MNT_ROOT)

    cards = [os.path.join(MNT_ROOT, el) for el in os.listdir(MNT_ROOT)]
    new_cr2s = []
    new_jpgs = []
    new_movs = []
    logger.info("# Searching for pictures or movies...")
    for card in cards:
        for root, dirs, files in os.walk(card):
            new_cr2s.extend( [os.path.join(root, el) for el in files if os.path.splitext(el)[1].lower() == '.cr2'] )
            new_jpgs.extend( [os.path.join(root, el) for el in files if os.path.splitext(el)[1].lower() == '.jpg'] )
            new_movs.extend( [os.path.join(root, el) for el in files if os.path.splitext(el)[1].lower() == '.mov'] )

    pictures = []

    if new_cr2s != []:
        start = time.perf_counter()
        logger.debug("Dealing with CR2s...")
        pbar = generate_pbar("Archiving CR2 files: ", len(new_cr2s)).start()
        for (i,cr2) in enumerate(new_cr2s):
            deal_with_cr2(cr2)
            pbar.update(i)
        pbar.finish()
        logger.debug("CR2s dealt with in %.3fs."%( (time.perf_counter() - start)))

    if new_jpgs != []:
        start = time.perf_counter()
        logger.debug("Dealing with JPGs...")

        pbar = generate_pbar("Archiving JPG files: ", len(new_jpgs)).start()
        for (i,jpg) in enumerate(new_jpgs):
            pictures.append(deal_with_jpg(jpg))
            pbar.update(i)
        pbar.finish()
        logger.debug("JPGs dealt with in %.3fs."%( (time.perf_counter() - start)))

    if new_movs != []:
        start = time.perf_counter()
        logger.debug("Dealing with MOVs...")
        pbar = generate_pbar("Archiving MOV files: ", len(new_movs)).start()
        for (i,mov) in enumerate(new_movs):
            deal_with_mov(mov)
            pbar.update(i)
        pbar.finish()
        logger.debug("MOVs dealt with in %.3fs."%( (time.perf_counter() - start)))

    os.sync()

    if pictures != []:
        cpt = 0
        pbar = generate_pbar("Processing JPG files: ", len(pictures)).start()
        with concurrent.futures.ThreadPoolExecutor(max_workers = multiprocessing.cpu_count()) as executor:
            future_jpg = { executor.submit(post_processing_jpg, pic): pic for pic in pictures}
            for future in concurrent.futures.as_completed(future_jpg):
                cpt +=1
                pbar.update(cpt)
        pbar.finish()
        logger.debug("JPGs dealt with in %.3fs."%( (time.perf_counter() - start)))

    logger.info( "Done, card can be removed.")
    notify_this("Daguerre has finished importing pictures,"
                "it is safe to remove the CF card.")

if __name__=="__main__":
    main()
