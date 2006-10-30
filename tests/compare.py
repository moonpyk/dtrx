#!/usr/bin/env python
#
# compare.py -- High-level tests for x.
# Copyright (c) 2006 Brett Smith <brettcsmith@brettcsmith.org>.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, 5th Floor, Boston, MA, 02111.

import os
import subprocess
import sys

from sets import Set as set

TESTSCRIPT_NAME = 'testscript.sh'
SCRIPT_PROLOGUE = """#!/bin/sh
set -e
"""

tests = {'test-1.23.tar': ['tar -xf test-1.23.tar'],
         'test-1.23.tar.gz': ['tar -xzf test-1.23.tar.gz'],
         'test-1.23.tar.bz2': ['mkdir test-1.23',
                               'cd test-1.23',
                               'tar -jxf ../test-1.23.tar.bz2'],
         'test-1.23.zip': ['mkdir test-1.23',
                           'cd test-1.23',
                           'unzip -q ../test-1.23.zip'],
         'test-1.23.cpio': ['cpio -i --make-directories \
                             <test-1.23.cpio 2>/dev/null'],
         'test-1.23_all.deb': ['TD=$PWD',
                               'mkdir test-1.23',
                               'cd /tmp',
                               'ar x $TD/test-1.23_all.deb data.tar.gz',
                               'cd $TD/test-1.23',
                               'tar -zxf /tmp/data.tar.gz',
                               'rm /tmp/data.tar.gz']}

if os.path.exists('scripts/x') and os.path.exists('tests'):
    os.chdir('tests')
elif os.path.exists('../scripts/x') and os.path.exists('../tests'):
    pass
else:
    print "ERROR: Can't run tests in this directory!"
    sys.exit(2)

class ExtractorTestError(Exception):
    pass


class ExtractorTest(object):
    def __init__(self, archive_filename, commands):
        self.archive_filename = archive_filename
        self.shell_commands = commands
        
    def get_results(self, commands):
        status = subprocess.call(commands)
        if status != 0:
            return None
        process = subprocess.Popen(['find'], stdout=subprocess.PIPE)
        process.wait()
        output = process.stdout.read(-1)
        process.stdout.close()
        return set(output.split('\n'))
        
    def get_shell_results(self):
        script = open(TESTSCRIPT_NAME, 'w')
        script.write("%s%s\n" % (SCRIPT_PROLOGUE,
                                 '\n'.join(self.shell_commands)))
        script.close()
        subprocess.call(['chmod', 'u+w', TESTSCRIPT_NAME])
        return self.get_results(['sh', TESTSCRIPT_NAME])

    def get_extractor_results(self):
        return self.get_results(['../scripts/x', self.archive_filename])
        
    def clean(self):
        status = subprocess.call(['find', '-mindepth', '1', '-maxdepth', '1',
                                  '-type', 'd',
                                  '!', '-name', 'CVS', '!', '-name', '.svn',
                                  '-exec', 'rm', '-rf', '{}', ';'])
        if status != 0:
            raise ExtractorTestError("cleanup exited with status code %s" %
                                     (status,))

    def run(self):
        self.clean()
        expected = self.get_shell_results()
        self.clean()
        actual = self.get_extractor_results()
        self.clean()
        if expected is None:
            raise ExtractorTestError("could not get baseline results")
        elif actual is None:
            raise ExtractorTestError("could not get extractor results")
        elif expected != actual:
            print "FAILED:", self.archive_filename
            print "Only in baseline results:"
            print '\n'.join(expected.difference(actual))
            print "Only in actual results:"
            print '\n'.join(actual.difference(expected))
            return False
        else:
            print "Passed:", self.archive_filename
            return True


successes = 0
failures = 0
testnames = tests.keys()
testnames.sort()
for testname in testnames:
    test = ExtractorTest(testname, tests[testname])
    if test.run():
        successes += 1
    else:
        failures += 1
print "Totals: %s successes, %s failures" % (successes, failures)

