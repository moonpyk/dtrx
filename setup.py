#!/usr/bin/env python

from distutils.core import setup

setup(name="dtrx",
      version = "6.5",
      description = "Script to intelligently extract multiple archive types",
      author = "Brett Smith",
      author_email = "brettcsmith@brettcsmith.org",
      url = "http://www.brettcsmith.org/2007/dtrx/",
      download_url = "http://www.brettcsmith.org/2007/dtrx/",
      scripts = ['scripts/dtrx'],
      license = "GNU General Public License, version 3 or later",
      classifiers = ['Development Status :: 5 - Production/Stable',
                     'Environment :: Console',
                     'Intended Audience :: End Users/Desktop',
                     'Intended Audience :: System Administrators',
                     'License :: OSI Approved :: GNU General Public License (GPL)',
                     'Natural Language :: English',
                     'Operating System :: POSIX',
                     'Programming Language :: Python',
                     'Topic :: Utilities'],
      long_description = """dtrx extracts archives in a number of different
      formats; it currently supports tar, zip (including self-extracting
      .exe files), cpio, rpm, deb, gem, 7z, cab, rar, and InstallShield
      files.  It can also decompress files compressed with gzip, bzip2,
      lzma, or compress.

      In addition to providing one command to handle many different archive
      types, dtrx also aids the user by extracting contents consistently.
      By default, everything will be written to a dedicated directory
      that's named after the archive.  dtrx will also change the
      permissions to ensure that the owner can read and write all those
      files."""
      )
