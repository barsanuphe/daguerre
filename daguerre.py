# -*- coding: utf-8 -*-

#TODO: -i import
#TODO: -s sync (smugmug)
#TODO: -e extract best pictures
#TODO: -r refresh
#TODO: tester toutes les combinaisons de caméra/objo + ceux sans exif....

#so that parsing this with python2 does not raise SyntaxError
from __future__ import print_function
import os, subprocess, shutil, sys, datetime, re, logging
import time, concurrent.futures, multiprocessing, argparse

if sys.version_info < (3,0,0):
  print("You need python 3.0 or later to run this script.")
  sys.exit(-1)

# libgexiv2 + python-gobject required
try:
    from gi.repository import GExiv2
except Exception as err:
    print("libgexiv2 must be installed!")
    sys.exit(-1)

# python-pillow required
try:
    from PIL import ImageEnhance, Image
except Exception as err:
    print("pillow for Python3 must be installed!")
    sys.exit(-1)

# python-progressbar required
from progressbar import Bar, Counter, ETA, Percentage, ProgressBar

try:
    # installer: jhead
    assert subprocess.call(["jhead","-V"], stdout=subprocess.DEVNULL) == 0
except AssertionError as err:
    print("jhead must be installed!")
    sys.exit(-1)

EXIFTOOL_PRESENT = True
try:
    # installer: perl-image-exiftool
    assert subprocess.call(["/usr/bin/vendor_perl/exiftool","-ver"],
                           stdout=subprocess.DEVNULL) == 0
except AssertionError as err:
    print("exiftool not detected, impossible to deal with .mov files!")
    #global EXIFTOOL_PRESENT
    EXIFTOOL_PRESENT = False

try:
    import yaml
except Exception as err:
    print("pyyaml (for python3) must be installed!")
    sys.exit(-1)

try:
    # install: python-notify2
    import notify2
except Exception as err:
    print("python-notify2 must be installed!")
    sys.exit(-1)

def notify_this(text):
    notify2.init("daguerre")
    n = notify2.Notification("Daguerre",
                             text,
                             "camera-photo")
    n.set_timeout(2000)
    n.show()


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
IMG_REGEXP = re.compile(r"[\w*]_(\d{4})(-bw)?[.jpg|.cr2|.mov]")


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

logger = None

def set_up_logger():
    global logger
    logger = logging.getLogger('daguerre')
    logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    logger.addHandler(ch)

    fh = logging.FileHandler("log/%s_daguerre.log"%
                             time.strftime("%Y-%m-%d_%Hh%M"))
    fh.setLevel(logging.DEBUG)
    logger.addHandler(fh)
    return logger

class Picture(object):
    def __init__(self, path_on_flash):
        self.path = path_on_flash
        self.filename = os.path.basename(self.path)
        self.type = os.path.splitext(path_on_flash)[1].lower()
        self.date = None
        self.camera = None
        self.lens = None
        self.expr = IMG_REGEXP
        self.new_name_generated = False

    def read_metadata(self):
        try:
            exif = GExiv2.Metadata(self.path)

            datetime_original = exif["Exif.Photo.DateTimeOriginal"]
            self.date = datetime.datetime.strptime(datetime_original,
                                                   "%Y:%m:%d %H:%M:%S")
            self.camera = exif["Exif.Image.Model"]
            if exif.has_tag('Exif.Photo.LensModel'):
                self.lens = exif['Exif.Photo.LensModel']
            elif exif.has_tag('Exif.Canon.LensModel'):
                self.lens = exif['Exif.Canon.LensModel']
            elif exif.has_tag("Exif.CanonCs.Lens"):
                (max_focal, min_focal, div) = [int(el) for el in exif['Exif.CanonCs.Lens'].split()]
                self.lens = "%s-%smm"%(int(min_focal/div), int(max_focal/div))
            assert self.lens is not None # out of ideas if lens is still None

            if self.camera in list(CAMERAS.keys()):
                self.camera = CAMERAS[self.camera]
            else:
                raise Exception("Could not identify camera %s"%self.camera)

            if self.lens in list(LENSES.keys()):
                self.lens = LENSES[self.lens]
            else:
                raise Exception("Could not identify lens %s"%self.lens)

        except Exception as err:
            logger.error( err )
            logger.error( "ERR: file %s does not have valid EXIF data" % self.filename)
            print('tags', exif.get_exif_tags())
            raise Exception("File with unrecognizable metadata.")

    @property
    def number(self):
        try:
            (number, bw) = self.expr.findall(os.path.basename(self.path).lower())[0]
            return number
        except:
            raise Exception("Bad format for file %s" % self.path)

    @property
    def is_bw(self):
        try:
            (number, bw) = self.expr.findall(os.path.basename(self.path).lower())[0]
            return bw == '-bw'
        except:
            raise Exception("Bad format for file %s"%self.path)

    def generate_new_name(self):
        timestamp = self.date.strftime("%Y-%m-%d-%Hh%Mm%Ss")
        if self.is_bw:
            return "%s_%s.%s_%04d-bw%s" % (timestamp,
                                           self.camera,
                                           self.lens,
                                           int(self.number),
                                           self.type)
        else:
            return "%s_%s.%s_%04d%s" % (timestamp,
                                        self.camera,
                                        self.lens,
                                        int(self.number),
                                        self.type)

    @property
    def archive_dir(self):
        if not hasattr(self, "date"):
            self.read_metadata()
        archive_dir = os.path.join(ARCHIVE_ROOT, "%s-%02d" % (self.date.year, self.date.month))
        if not os.path.exists(archive_dir):
            logger.debug( "Creating %s" % archive_dir )
            os.makedirs(archive_dir)
        return archive_dir

    @property
    def active_dir(self):
        if not hasattr(self, "date"):
            self.read_metadata()
        active_dir = os.path.join(ACTIVE_ROOT, "%s-%02d" % (self.date.year, self.date.month))
        if not os.path.exists(active_dir):
            logger.debug( "Creating %s"%active_dir )
            os.makedirs(active_dir)
        return active_dir

    def to_dir(self, active = True, move = True):
        if active:
            dest = os.path.join(self.active_dir, self.generate_new_name())
        else:
            dest = os.path.join(self.archive_dir, self.generate_new_name())
        if move:
            logger.debug( "\tMoving %s to %s" % (os.path.basename(self.path), dest) )
            shutil.move(self.path, dest)
        else:
            logger.debug( "\tCopying %s to %s" % (os.path.basename(self.path), dest) )
            shutil.copyfile(self.path, dest)

    def losslessly_rotate(self):
        #""" rotates losslessly if the photo is in portrait mode so that SmugMug is happy """
        jpg_filename = os.path.join(self.active_dir, self.generate_new_name())
        subprocess.check_call(["jhead","-autorot",jpg_filename],
                              stdout=subprocess.DEVNULL)

    def convert_to_bw(self):
        """ convert to jpg + add to active_images """
        if not self.is_bw:
            jpg_filename = os.path.join(self.active_dir, self.generate_new_name())
            jpg_bw_filename = jpg_filename.replace(".jpg", "-bw.jpg")

            logger.debug( "\tConverting to B&W jpg" )
            im = Image.open(jpg_filename)
            exif = im.info['exif']
            enhancer = ImageEnhance.Color(im)
            bw = enhancer.enhance(0.0)
            enhancer = ImageEnhance.Contrast(bw)
            enhancer.enhance(1.1).save(jpg_bw_filename,
                                       'JPEG',
                                       exif = exif,
                                       quality = 95,
                                       optimize = True,
                                       subsampling = "4:2:2" )

    def __str__(self):
        return self.filename

class Movie(Picture):

    def read_metadata(self):
        try:
            rep = subprocess.check_output(["/usr/bin/vendor_perl/exiftool","-s3","-DateTimeOriginal","-Model","-LensModel", self.path])
            infos = [el.strip() for el in rep.decode("utf-8").split("\n")]
            self.date = datetime.datetime.strptime(infos[0], "%Y:%m:%d %H:%M:%S")
            self.camera = infos[1]
            self.lens = infos[2]

            if self.camera in list(CAMERAS.keys()):
                self.camera = CAMERAS[self.camera]
            else:
                raise Exception("Could not identify camera %s" % self.camera)

            if self.lens in list(LENSES.keys()):
                self.lens = LENSES[self.lens]
            else:
                raise Exception("Could not identify lens %s" % self.lens)

        except Exception as err:
            logger.error( err )
            logger.error( "ERR: file %s does not have valid metadata" % self.filename)
            raise Exception("File with unrecognizable metadata.")

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

def generate_pbar(title, number_of_elements):
    widgets = [title, Counter(), '/%s '%number_of_elements, Percentage(), ' ', Bar(left='[',right=']', fill='-'),' ', ETA()]
    return ProgressBar(widgets = widgets, maxval = number_of_elements).start()

if __name__=="__main__":
    set_up_logger()
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

    if EXIFTOOL_PRESENT and new_movs != []:
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
