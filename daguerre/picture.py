import os
import re

from daguerre.checks import *
from daguerre.logger import *


IMG_REGEXP = re.compile(r"[\w*]_(\d{4})(-bw)?[.jpg|.cr2|.mov]")


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
