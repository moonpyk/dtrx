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

tests = {'test-1.23.tar': ([], ['tar -xf $1'], []),
         'test-1.23.tar.gz': ([], ['tar -xzf $1'], []),
         'test-1.23.tar.bz2': ([], ['mkdir test-1.23',
                                    'cd test-1.23',
                                    'tar -jxf ../$1'], []),
         'test-1.23.zip': ([], ['mkdir test-1.23',
                                'cd test-1.23',
                                'unzip -q ../$1'], []),
         'test-1.23.cpio': ([], ['cpio -i --make-directories \
                                  <$1 2>/dev/null'], []),
         'test-1.23_all.deb': ([], ['TD=$PWD',
                                    'mkdir test-1.23',
                                    'cd /tmp',
                                    'ar x $TD/$1 data.tar.gz',
                                    'cd $TD/test-1.23',
                                    'tar -zxf /tmp/data.tar.gz',
                                    'rm /tmp/data.tar.gz'], []),
         'test-recursive-badperms.tar.bz2': (
    ['-r'],
    ['mkdir test-recursive-badperms',
     'cd test-recursive-badperms',
     'tar -jxf ../$1',
     'mkdir test-badperms',
     'cd test-badperms',
     'tar -xf ../test-badperms.tar',
     'chmod 755 testdir'],
    ['if [ "x`cat test-recursive-badperms/test-badperms/testdir/testfile`" = \
      "xhey" ]',
     'then exit 0; else exit 1; fi']
    )}

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
    def __init__(self, directory, archive_filename, info):
        self.directory = directory
        self.archive_filename = os.path.join(directory, archive_filename)
        self.arguments, self.shell_commands, self.shell_test = info
        
    def get_results(self, commands):
        status = subprocess.call(commands)
        if status != 0:
            return None
        process = subprocess.Popen(['find'], stdout=subprocess.PIPE)
        process.wait()
        output = process.stdout.read(-1)
        process.stdout.close()
        return set(output.split('\n'))
        
    def write_script(self, commands):
        script = open(TESTSCRIPT_NAME, 'w')
        script.write("%s%s\n" % (SCRIPT_PROLOGUE, '\n'.join(commands)))
        script.close()
        subprocess.call(['chmod', 'u+w', TESTSCRIPT_NAME])

    def get_shell_results(self):
        self.write_script(self.shell_commands)
        return self.get_results(['sh', TESTSCRIPT_NAME, self.archive_filename])

    def get_extractor_results(self):
        script = os.path.join(self.directory, '../scripts/x')
        return self.get_results([script] + self.arguments +
                                [self.archive_filename])
        
    def get_posttest_result(self):
        if not self.shell_test:
            return 0
        self.write_script(self.shell_test)
        return subprocess.call(['sh', TESTSCRIPT_NAME])

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
        posttest_result = self.get_posttest_result()
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
        elif posttest_result != 0:
            print "FAILED:", self.archive_filename
            print "Posttest returned status code", posttest_result
            print actual
            return False
        else:
            print "Passed:", self.archive_filename
            return True


def run_tests(directory, testnames):
    successes = 0
    failures = 0
    for testname in testnames:
        test = ExtractorTest(directory, testname, tests[testname])
        if test.run():
            successes += 1
        else:
            failures += 1
    return successes, failures
    
results = []
testnames = tests.keys()
testnames.sort()
results.append(run_tests('.', testnames))
os.mkdir('inside-dir')
os.chdir('inside-dir')
results.append(run_tests('..', testnames))
os.chdir('..')
subprocess.call(['rm', '-rf', 'inside-dir'])
print "Totals: %s successes, %s failures" % \
      tuple([sum(total) for total in zip(*results)])
