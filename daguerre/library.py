import os
from pathlib import Path
import concurrent.futures
import mulitprocessing

from daguerre.checks import *
from daguerre.helpers import *
from daguerre.logger import *
from daguerre.config import *

class Library(object):
    def __init__(self, config_file):
        self.config_file = ConfigFile("daguerre", config_file)
        self.config_file.parse()

    def import_from_cards(self, cards=["all"]):
        all_mounted_cards = [Path(self.config_file.mount_root, el) for el in os.listdir(self.config_file.mount_root)]
        if cards == ["all"]:
            cards = all_mounted_cards
        else: 
            # intersection cards/all_mounted_cards
            cards = [Path(self.config_file.mount_root, el) for el in cards if Path(self.config_file.mount_root, el) in all_mounted_cards]
        # actual import
        for card in cards:
            self.import_from_card(card_name)
            
    def import_from_card(self, card_name):
        new_pics = []
        new_movs = []
        jpgs_to_process = []
        logger.info("# Searching for pictures or movies on card %s..." % card_name)
        for root, dirs, files in os.walk(card):
            new_pics.extend([Path(root, el) for el in files if Path(el).suffix.lower() in ['.jpg', '.cr2']])
            new_movs.extend([Path(root, el) for el in files if Path(el).suffix.lower() == '.mov'])

        if new_pics != []:
            start = time.perf_counter()
            logger.debug("Dealing with JPG/CR2 files...")
            pbar = generate_pbar("Archiving JPG/CR2 files: ", len(new_pics)).start()
            for (i, pic_filename) in enumerate(new_pics):
                pic = Picture(pic_filename, self.config_file)
                pic.read_metadata()
                pic.to_dir()
                if pic_filename.suffix.lower() == ".jpg":
                    jpgs_to_process.append(pic)
                pbar.update(i)
            pbar.finish()
            logger.debug("Pictures dealt with in %.3fs."%( (time.perf_counter() - start)))
            
        if new_movs != []:
            start = time.perf_counter()
            logger.debug("Dealing with MOVs...")
            pbar = generate_pbar("Archiving MOV files: ", len(new_movs)).start()
            for (i, mov_filename) in enumerate(new_movs):
                mov = Movie(mov_filename, self.config_file)
                mov.read_metadata()
                mov.to_dir()
                pbar.update(i)
            pbar.finish()
            logger.debug("MOVs dealt with in %.3fs."%( (time.perf_counter() - start)))
            
        if jpgs_to_process != []:
            cpt = 0
            start = time.perf_counter()
            pbar = generate_pbar("Processing JPG files: ", len(jpgs_to_process)).start()
            with concurrent.futures.ThreadPoolExecutor(max_workers = multiprocessing.cpu_count()) as executor:
                future_jpg = {executor.submit(self._post_processing_jpg, pic): pic for pic in jpgs_to_process}
                for future in concurrent.futures.as_completed(future_jpg):
                    cpt +=1
                    pbar.update(cpt)
            pbar.finish()
            logger.debug("JPGs dealt with in %.3fs."%( (time.perf_counter() - start)))
        
        
    def _post_processing_jpg(self, picture):
        picture.losslessly_rotate()
        picture.convert_to_bw()
    
    def refresh_filenames(self, directory):
        pass
        
    def filter_files(self, conditions):
        pass
        
    def export(self, to_directory, conditions):
        pass
        
    def list_single_raw_file(self, directory=None):
        if directory is None:
            directory = self.config_file.directory
        else:
            directory = Path(self.config_file.directory, directory)
            assert directory.exists()
            
        all_file_groups = {}
        for root, dirs, files in os.walk(directory):
            for file in [Path(f) for f in files if Path(f).suffix in [".jpg", ".cr2"]:
                #TODO récup timestamp et id
                all_file_groups[(timestamp, id)] = file
            
        orphans = []
        for (t,i) in list(all_file_groups.keys()):
            group = all_file_groups[(t,i)]
            cr2s = [p for p in group if p.suffix == '.cr2']
            jpgs = [p for p in group if p.suffix == '.jpg']
            
            if cr2s == []:
                pass
                # print("No raw file for %s"%jpgs[0])
            if jpgs == []:
                orphans.extend(cr2s)
        
        print("\n".join(orphans))
        return orphans
        
    def remove_single_raw_files(self, directory=None):
        pass