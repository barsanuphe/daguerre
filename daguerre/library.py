import os
from pathlib import Path
import concurrent.futures
import multiprocessing

from daguerre.checks import *
from daguerre.helpers import generate_progress_bar, run_in_parallel
from daguerre.logger import *
from daguerre.smugmugsync import SmugMugManager
from daguerre.config import ConfigFile
from daguerre.picture import Picture
from daguerre.movie import Movie


class Library(object):
    def __init__(self, config_file):
        self.config_file = ConfigFile("daguerre", config_file)

    def __enter__(self):
        self.config_file.parse()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is not None:
            print("\nGot interrupted. Trying to clean up.")
            # TODO

    def import_from_cards(self, cards=["all"]):
        all_mounted_cards = [Path(self.config_file.mount_root, el)
                             for el in self.config_file.mount_root.iterdir()
                             if el.is_dir()]
        if cards == ["all"]:
            cards_to_import = all_mounted_cards
        else:
            # intersection cards/all_mounted_cards
            cards_to_import = [Path(self.config_file.mount_root, el)
                               for el in cards
                               if Path(self.config_file.mount_root, el) in all_mounted_cards]
        if not cards_to_import:
            logger.warning("Card %s not found." % ', '.join(cards))
        # actual import
        for card in cards_to_import:
            self.import_from_card(card)

    def import_from_card(self, card_path):
        jpgs_to_process = []
        logger.info("# Searching for pictures or movies on card %s..." % card_path)
        new_pics = [x for x in card_path.rglob("*")
                    if x.suffix.lower() in ['.jpg', '.cr2', '.arw'] and "DCIM" in x.parts]
        new_movs = [x for x in card_path.rglob("*") if x.suffix.lower() in ['.mov', '.mp4']]

        if new_pics:
            start = time.perf_counter()
            logger.debug("Dealing with JPG/RAW files...")
            progress_bar = generate_progress_bar("Archiving JPG/RAW files: ", len(new_pics)).start()
            for (i, pic_filename) in enumerate(new_pics):
                pic = Picture(pic_filename, self.config_file)
                pic.read_metadata()
                pic.to_dir()
                if pic_filename.suffix.lower() == ".jpg":
                    jpgs_to_process.append(pic)
                progress_bar.update(i)
            progress_bar.finish()
            logger.debug("Pictures dealt with in %.3fs." % (time.perf_counter() - start))

        if new_movs:
            start = time.perf_counter()
            logger.debug("Dealing with MOVs...")
            progress_bar = generate_progress_bar("Archiving MOV files: ", len(new_movs)).start()
            for (i, mov_filename) in enumerate(new_movs):
                mov = Movie(mov_filename, self.config_file)
                mov.read_metadata()
                mov.to_dir()
                progress_bar.update(i)
            progress_bar.finish()
            logger.debug("MOVs dealt with in %.3fs." % (time.perf_counter() - start))

        # process jpgs
        start = time.perf_counter()
        run_in_parallel(self._post_processing_jpg, jpgs_to_process, "Processing JPG files: ")
        logger.debug("JPGs dealt with in %.3fs." % (time.perf_counter() - start))

    @staticmethod
    def _post_processing_jpg(picture):
        picture.losslessly_rotate()
        picture.convert_to_bw()

    def refresh_filenames(self, directory):
        pass

    def filter_files(self, conditions):
        pass

    def export(self, to_directory, conditions):
        pass

    def list_single_raw_files(self, directory=None):
        if directory is None:
            directory = self.config_file.directory
        else:
            directory = Path(self.config_file.directory, directory)
            assert directory.exists()

        # list of Pictures in directory
        pics = [Picture(x, self.config_file)
                for x in directory.rglob("*")
                if x.suffix.lower() in ['.jpg', '.cr2', '.arw']]
        pics.sort(key=lambda p: p.path.name)

        all_file_groups = {}
        # group by number and date
        for p in pics:
            if (p.file_prefix, p.number) in all_file_groups:
                all_file_groups[(p.file_prefix, p.number)].append(p)
            else:
                all_file_groups[(p.file_prefix, p.number)] = [p]

        orphans = []
        for (t, i) in all_file_groups:
            group = all_file_groups[(t, i)]
            cr2s = [p for p in group if p.path.suffix in ['.cr2', '.arw']]
            jpgs = [p for p in group if p.path.suffix == '.jpg']

            if not cr2s:
                pass
                # print("No raw file for %s" % jpgs[0])
            if jpgs == [] and cr2s != []:
                orphans.extend(cr2s)

        if orphans:
            print("Orphans:")
            orphans.sort(key=lambda p: p.path.name)
            for o in orphans:
                print("\t%s" % o.path.name)
        else:
            print("No orphan raw file found.")
        return orphans, len(pics)

    def remove_single_raw_files(self, directory=None):
        start = time.time()
        orphans, number_of_pics = self.list_single_raw_files(directory)
        print("\n%s pictures analyzed in %.2fs" % (number_of_pics,
                                                   time.time() - start))
        if orphans:
            rep = input("\n!! Remove files? (y/N) ")
            if rep.lower() == "y":
                for o in orphans:
                    print(" + Removing %s..." % o.path.name)
                    os.remove(o.path.as_posix())
            else:
                print("Nothing was done.")

    def sync(self, directory, public_only=False):
        print("Syncing with smugmug")
        if directory == "all":
            sync_directories = [p for p in self.config_file.directory.iterdir() if p.is_dir()]
            sync_directories.sort()
        else:
            directory = Path(self.config_file.directory, directory)
            assert directory.exists() and directory.is_dir()
            sync_directories = [Path(self.config_file.directory, directory)]

        start = time.perf_counter()
        s = SmugMugManager(self.config_file)
        s.login()
        for directory_to_sync in sync_directories:
            s.sync(directory_to_sync, directory_to_sync.name, public_only)
        print("Synced with Smugmug in %.3fs." % (time.perf_counter() - start))
