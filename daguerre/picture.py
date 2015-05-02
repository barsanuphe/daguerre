import os
import re
from pathlib import Path
import datetime
import shutil

from daguerre.checks import *
from daguerre.logger import *


IMG_REGEXP = re.compile(r"[\w*]_(\d{4})(-bw)?[.jpg|.cr2|.mov]")


class Picture(object):
    def __init__(self, path_on_flash, config):
        self.path = path_on_flash
        self.date = None
        self.camera = None
        self.lens = None
        self.expr = IMG_REGEXP
        self.new_name_generated = False
        self.config = config
        self._is_bw = None
        self._number = None

    def read_metadata(self):
        try:
            exif = GExiv2.Metadata(self.path.as_posix())

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

            if self.camera in self.config.cameras:
                self.camera = self.config.cameras[self.camera]
            else:
                raise Exception("Could not identify camera %s"%self.camera)

            if self.lens in self.config.lenses:
                self.lens = self.config.lenses[self.lens]
            else:
                raise Exception("Could not identify lens %s"%self.lens)

        except Exception as err:
            logger.error( err )
            logger.error( "ERR: file %s does not have valid EXIF data" % self.path.name)
            raise Exception("File with unrecognizable metadata.")

    @property
    def number(self):
        if self._number is None:
            try:
                (self._number, bw) = self.expr.findall(self.path.name.lower())[0]
                return self._number
            except:
                raise Exception("Bad format for file %s" % self.path)
        else:
            return self._number

    @property
    def is_bw(self):
        if self._is_bw is None:
            try:
                (number, bw) = self.expr.findall(self.path.name.lower())[0]
                self._is_bw = (bw == '-bw')
                return self._is_bw
            except:
                raise Exception("Bad format for file %s"%self.path)
        else:
            return self._is_bw

    @property
    def imported_path(self):
        # checking metadata was read
        if not hasattr(self, "camera"):
            self.read_metadata()
        timestamp = self.date.strftime("%Y-%m-%d-%Hh%Mm%Ss")
        if self.is_bw:
            name = "%s_%s.%s_%04d-bw%s" % (timestamp,
                                           self.camera,
                                           self.lens,
                                           int(self.number),
                                           self.path.suffix.lower())
        else:
            name = "%s_%s.%s_%04d%s" % (timestamp,
                                        self.camera,
                                        self.lens,
                                        int(self.number),
                                        self.path.suffix.lower())
        return Path(self.destination_directory, name)

    @property
    def destination_directory(self):
        # checking metadata was read
        if not hasattr(self, "date"):
            self.read_metadata()
        archive_dir = Path(self.config.directory,
                           "%s-%02d" % (self.date.year, self.date.month))
        if not archive_dir.exists():
            logger.debug( "Creating %s" % archive_dir )
            archive_dir.mkdir(parents=True)
        return archive_dir

    def to_dir(self):
        logger.debug("\tMoving %s to %s" % (self.path.name, self.imported_path))
        shutil.move(self.path.as_posix(), self.imported_path.as_posix())

    def losslessly_rotate(self):
        #""" rotates losslessly if the photo is in portrait mode so that SmugMug is happy """
        if self.imported_path.suffix == ".jpg":
            subprocess.check_call(["jhead", "-autorot", self.imported_path.as_posix()],
                              stdout=subprocess.DEVNULL)

    def convert_to_bw(self):
        """ convert to jpg + add to active_images """
        if not self.is_bw:
            jpg_bw_filename = self.imported_path.as_posix().replace(".jpg", "-bw.jpg")
            logger.debug( "\tConverting to B&W jpg" )
            im = Image.open(self.imported_path.as_posix())
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
        return self.path.name
