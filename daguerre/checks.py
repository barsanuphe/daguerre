import sys
import subprocess

# --CHECKS----------------------------
if sys.version_info < (3, 4, 0):
    print("You need python 3.4 or later to run this script.")
    sys.exit(-1)

# -- Python modules

# install: python-yaml, python-xdg, python-notify2, libgexiv2 + python-gobject required,
# python-progressbar, python-pillow
modules = ["yaml", "xdg.BaseDirectory", "notify2", "progressbar", "gi", "PIL"]
for module in modules:
    try:
        __import__(module)
    except ImportError:
        print("%s must be installed!" % module)
        sys.exit(-1)

# better imports
from progressbar import Bar, Counter, ETA, Percentage, ProgressBar
from gi.repository import GExiv2
from PIL import ImageEnhance, Image

# -- External binaries

# installer: perl-image-exiftool; jhead
externals = [["jhead", "-V"], ["/usr/bin/vendor_perl/exiftool", "-ver"]]
for external in externals:
    try:
        assert subprocess.call(external,
                               stdout=subprocess.DEVNULL) == 0
    except FileNotFoundError:
        print("%s must be installed!" % external[0])
        sys.exit(-1)
