from daguerre.checks import *
from daguerre.helpers import *
from daguerre.logger import *

from pathlib import Path
import getpass
import yaml
import xdg.BaseDirectory

class ConfigFile(object):
    def __init__(self, program, filename):
        self.filename = filename
        self.config_path = xdg.BaseDirectory.save_config_path(program)
        self.configuration_file = Path(self.config_path, filename)
        self.all_config = {}
        self.mount_root = Path("/run/media/", getpass.getuser())

    def parse(self):
        if self.configuration_file.exists():
            self.all_config = yaml.load(open(self.configuration_file.as_posix(), 'r'))
            # quick check everything needed is here
            try:
                assert "config"     in self.all_config
                assert "lenses"     in self.all_config
                assert "cameras"    in self.all_config
                assert "directory"  in self.all_config["config"]
            except Exception as err:
                print("Missing config option: ", err)
                raise Exception("Invalid configuration file!")
        else:
            raise Exception("Configuration file %s does not exist!" % self.configuration_file)

    @property
    def directory(self):
        return Path(self.all_config["config"].get("directory", ""))

    @property
    def lenses(self):
        return self.all_config["lenses"]

    @property
    def cameras(self):
        return self.all_config["cameras"]

    def encrypt(self):
        pass

    def decrypt(self):
        pass

