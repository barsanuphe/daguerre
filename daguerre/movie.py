from daguerre.checks import *
from daguerre.picture import *

class Movie(Picture):

    def read_metadata(self):
        try:
            rep = subprocess.check_output(["/usr/bin/vendor_perl/exiftool","-s3","-DateTimeOriginal","-Model","-LensModel", self.path.as_posix()])
            infos = [el.strip() for el in rep.decode("utf-8").split("\n")]
            self.date = datetime.datetime.strptime(infos[0], "%Y:%m:%d %H:%M:%S")
            self.camera = infos[1]
            self.lens = infos[2]

            if self.camera in list(self.config.cameras.keys()):
                self.camera = self.config.cameras[self.camera]
            else:
                raise Exception("Could not identify camera %s" % self.camera)

            if self.lens in list(self.config.lenses.keys()):
                self.lens = self.config.lenses[self.lens]
            else:
                raise Exception("Could not identify lens %s" % self.lens)

        except Exception as err:
            logger.error( err )
            logger.error( "ERR: file %s does not have valid metadata" % self.filename)
            raise Exception("File with unrecognizable metadata.")

