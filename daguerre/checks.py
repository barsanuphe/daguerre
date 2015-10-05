import sys
import subprocess

# --CHECKS----------------------------
if sys.version_info < (3, 4, 0):
    print("You need python 3.4 or later to run this script.")
    sys.exit(-1)

# -- Python modules

# install: python-yaml, python-xdg, python-notify2,
# python-progressbar, python-pillow, python-rauth
modules = ["yaml", "xdg.BaseDirectory", "notify2", "progressbar", "PIL", "rauth"]
for module in modules:
    try:
        __import__(module)
    except ImportError:
        print("%s must be installed!" % module)
        sys.exit(-1)

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
