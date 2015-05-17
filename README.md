# Daguerre

## What it is

**Daguerre** is a script to import pictures from removable devices (ie CF cards)
and automatically rename them using exif metadata.
It also generates black & white versions of all jpgs.

At some point it will probably do other things as well.
For example, it can now sync the daguerre directory (or a subdirectory) with a 
[Smugmug](http://www.smugmug.com/) account.

Please note this is not stable yet.
**You may lose data.**
And losing pictures is awful.

## Table of Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Example Commands](#example-commands)
- [Configuration](#configuration)
- [daguerre.yaml example](#daguerreyaml-example)

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
- python-rauth

External binaries required:
- exiftool (.mov metadata)
- jhead (lossless rotation)

For [Smugmug](http://www.smugmug.com/) sync:
- a Smugmug account
- an existing folder for public pictures and one for private pictures
- an [API KEY](https://api.smugmug.com/api/developer/apply)
- a ["New Smugmug"](http://help.smugmug.com/customer/portal/articles/1212681-making-the-move-from-legacy-to-new-smugmug)
 account because `daguerre` uses Smugmug's 2.0 API. 


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
    
    usage: daguerre [-h]
                    [-i CARD_NAME [CARD_NAME ...]]
                    [--clean-raw [DIRECTORY]]
                    [--to TO_DATE] [-s [DIRECTORY]] [--public]
    
    Daguerre. A script to deal with pictures.
    
    optional arguments:
      -h, --help            show this help message and exit
    
    Operations:
      Import.
    
      -i CARD_NAME [CARD_NAME ...], --import CARD_NAME [CARD_NAME ...]
                            import picture from specific cards, or "all".
    
    Operations:
      Maintenance.
    
      --clean-raw [DIRECTORY]
                            Clean up single CR2 files (in a directory).
    
    Operations:
      Export.

      -s [DIRECTORY], --sync-with-smugmug [DIRECTORY]
                            Sync photos with smugmug account.
      --public              Only export pictures tagged as public.


### Example commands

Import pictures from a card:

    daguerre --import cardname

Import pictures from all connected cards:

    daguerre --import all

Remove orphan raw files (cr2), in the `2007-03` subdirectory.

    daguerre --clean-raw 2007-03

This last command assumes the normal mode of operation is to have raw+jpgs files.
Orphan raw files are cr2 files without any corresponding jpg files, presumably
because they were awful shots.

Sync the `2007-03` subdirectory with a Smugmug account: 

    daguerre -s 2007-03
    
Only sync with Smugmug the pictures tagged as public: 

    daguerre -s 2007-03 --public
    
See the following section on what can be expected.

### Configuration

**Daguerre** uses a yaml file to describe
- general configuration,
- known lenses/cameras and their short names (used for renaming pictures).
- Smugmug information

Here is the supported structure of the directory: 

    directory
     |- subdirectory1
        |- xxxx.jpg ...    
     |- subdirectory2

And here is the equivalent when sync'ed with Smugmug: 

    public_folder/
     |- subdirectory1/
        |- xxxx.jpg ...
     |- subdirectory2/
     
    private_folder/
     |- subdirectory1/
     |- subdirectory2/
     
How are files sorted between the public and private folders? 
With a special public exif keyword (in `Iptc.Application2.Keywords`, ie a `tag` in 
[Digikam](https://www.digikam.org)), mentionned in the configuration file.


The public and private folders must be created independantly. 
`daguerre` will create the subdirectories.

When syncing, `daguerre` will analyze local pictures for the public tag and calculate their md5 hash. 
It will then query Smugmug for its own files. 
If there are local changes, obsolete files on Smugmug will be deleted and the new local versions uploaded.

Smumug accounts provide unlimited storage, so private galleries can be used as a backup. 

At first use, Smugmug will provide a link to get access tokens (via web browser). 
To prevent having to do this all over again, the user can copy them in the configuration file for later use.
That probably means that this file needs to be secured, since the tokens grant all rights on your Smugmug account.

Here's the general structure:

    config:
        directory: /home/user/pictures
    lenses:
        exif_lens_name:     short_name
    cameras:
        exif_camera_name:   short_name
    smugmug:
        public_tag: best
        public_folder: Public
        private_folder: Private
        api_key: XXXXX
        api_key_secret: XXXX
        access_token: XXXX
        access_token_secret: XXX



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
    smugmug:
        public_tag: best
        public_folder: Public
        private_folder: Private
        api_key: XXXXX
        api_key_secret: XXXX
        access_token: XXXX
        access_token_secret: XXX
