# Daguerre

## What it is

**Daguerre** is a script to import pictures from removable devices (ie CF cards)
and automatically rename them using exif metadata.
It also generates black & white versions of all jpgs.

At some point it will probably do other things as well.

Please note this is not stable yet.
**You may lose data.**
And losing pictures is awful.

## Table of Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Example Commands](#example-commands)
- [Configuration](#configuration)
- [grenier.yaml example](#grenieryaml-example)

### Requirements

**Daguerre** runs on Linux (tested in Archlinux only).

Current requirements:
- python (3.4+)
- python-yaml
- python-notify2
- python-xdg
- python-progressbar
- libgexiv2
- python-gobject
- python-pillow

External binaries required:
- exiftool (.mov metadata)
- jhead (lossless rotation)

### Installation


After cloning this repository, run:

    $ sudo python setup.py install

To uninstall (not sure why one would want to do such a thing), run:

    $ sudo pip uninstall daguerre

The configuration file *daguerre.yaml* is expected to be in
`$XDG_CONFIG_HOME/daguerre/`. You might want to `ln -s` your actual configuration
file there, because let's face it, `$XDG_CONFIG_HOME` is a sad and lonely place
you never visit.

Logs are in `$XDG_DATA_HOME/daguerre`.

### Usage

    $ daguerre -h
    # D A G U E R R E #

    usage: daguerre [-h] [--config CONFIG_FILE]
                    [-i CARD_NAME [CARD_NAME ...]]
                    [--clean-raw [DIRECTORY]]

    Daguerre. A script to deal with pictures.

    optional arguments:
    -h, --help            show this help message and exit

    Configuration:
    Manage configuration files.

    --config CONFIG_FILE  Use an alternative configuration file.

    Operations:
    Actions.

    -i CARD_NAME [CARD_NAME ...], --import CARD_NAME [CARD_NAME ...]
                            import picture from specific cards, or "all".
    --clean-raw [DIRECTORY]
                            Clean up single CR2 files (in a directory).


### Example commands

Import pictures from a card:

    daguerre --import cardname

Import pictures from all connected cards:

    daguerre --import all


### Configuration

**Daguerre** uses a yaml file to describe
- general configuration,
- known lenses/cameras and their short names (used for renaming pictures).


Here's the general structure:

    config:
        directory: /home/user/pictures
    lenses:
        exif_lens_name:     short_name
    cameras:
        exif_camera_name:   short_name


### daguerre.yaml example

This file will import `IMG_0501.jpg` to something like
`2007-03/2007-03-10-14h27m00s_350D.135mm2L_0501.jpg` after parsing its exif
metadata.

    config:
        directory: /home/user/pictures
    lenses:
        EF70-200mm f/4L IS USM:         70-200mm4L-IS
        EF135mm f/2L USM:               135mm2L
        35mm:                           35mm1.4
        EF16-35mm f/4L IS USM:          16-35mm4L-IS
    cameras:
        Canon EOS 5D Mark III:  5D3
        Canon EOS 7D:           7D
        Canon EOS 40D:          40D
        Canon EOS 350D DIGITAL: 350D
