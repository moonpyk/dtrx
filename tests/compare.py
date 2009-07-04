#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# compare.py -- High-level tests for dtrx.
# Copyright © 2006-2009 Brett Smith <brettcsmith@brettcsmith.org>.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 3 of the License, or (at your
# option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, see <http://www.gnu.org/licenses/>.

import os
import re
import subprocess
import syck
import sys
import tempfile

from sets import Set as set

if os.path.exists('scripts/dtrx') and os.path.exists('tests'):
    os.chdir('tests')
elif os.path.exists('../scripts/dtrx') and os.path.exists('../tests'):
    pass
else:
    print "ERROR: Can't run tests in this directory!"
    sys.exit(2)

X_SCRIPT = os.path.realpath('../scripts/dtrx')
ROOT_DIR = os.path.realpath(os.curdir)
OUTCOMES = ['error', 'failed', 'passed']
TESTSCRIPT_NAME = 'testscript.sh'
SCRIPT_PROLOGUE = """#!/bin/sh
set -e
"""

input_buffer = tempfile.TemporaryFile()
output_buffer = tempfile.TemporaryFile()

class ExtractorTestError(Exception):
    pass


class ExtractorTest(object):
    def __init__(self, **kwargs):
        setattr(self, 'name', kwargs['name'])
        setattr(self, 'options', kwargs.get('options', '-n').split())
        setattr(self, 'filenames', kwargs.get('filenames', '').split())
        for key in ('directory', 'prerun', 'posttest', 'baseline', 'error',
                    'input', 'output', 'cleanup'):
            setattr(self, key, kwargs.get(key, None))
        for key in ('grep', 'antigrep'):
            value = kwargs.get(key, [])
            if isinstance(value, str):
                value = [value]
            setattr(self, key, value)
        
    def get_results(self, commands, stdin=None):
        print >>output_buffer, "Output from %s:" % (' '.join(commands),)
        output_buffer.flush()
        status = subprocess.call(commands, stdout=output_buffer,
                                 stderr=output_buffer, stdin=stdin)
        process = subprocess.Popen(['find', '!', '-name', TESTSCRIPT_NAME],
                                   stdout=subprocess.PIPE)
        process.wait()
        output = process.stdout.read(-1)
        process.stdout.close()
        return status, set(output.split('\n'))
        
    def write_script(self, commands):
        script = open(TESTSCRIPT_NAME, 'w')
        script.write("%s%s\n" % (SCRIPT_PROLOGUE, commands))
        script.close()
        subprocess.call(['chmod', 'u+w', TESTSCRIPT_NAME])

    def run_script(self, key):
        commands = getattr(self, key)
        if commands is not None:
            if self.directory:
                directory_hint = '../'
            else:
                directory_hint = ''
            self.write_script(commands)
            subprocess.call(['sh', TESTSCRIPT_NAME, directory_hint])

    def get_shell_results(self):
        self.run_script('prerun')
        self.write_script(self.baseline)
        return self.get_results(['sh', TESTSCRIPT_NAME] + self.filenames)

    def get_extractor_results(self):
        self.run_script('prerun')
        input_buffer.seek(0, 0)
        input_buffer.truncate()
        if self.input:
            input_buffer.write(self.input)
            if not self.input.endswith('\n'):
                input_buffer.write('\n')
            input_buffer.seek(0, 0)
        input_buffer.flush()
        return self.get_results([X_SCRIPT] + self.options + self.filenames,
                                input_buffer)
        
    def get_posttest_result(self):
        if not self.posttest:
            return 0
        self.write_script(self.posttest)
        return subprocess.call(['sh', TESTSCRIPT_NAME])

    def clean(self):
        self.run_script('cleanup')
        if self.directory:
            target = os.path.join(ROOT_DIR, self.directory)
            extra_options = ['!', '-name', TESTSCRIPT_NAME]
        else:
            target = ROOT_DIR
            extra_options = ['(', '(', '-type', 'd',
                             '!', '-name', 'CVS',
                             '!', '-name', '.svn', ')',
                             '-or', '-name', 'test-text',
                             '-or', '-name', 'test-onefile', ')']
        status = subprocess.call(['find', target,
                                  '-mindepth', '1', '-maxdepth', '1'] +
                                 extra_options +
                                 ['-exec', 'rm', '-rf', '{}', ';'])
        if status != 0:
            raise ExtractorTestError("cleanup exited with status code %s" %
                                     (status,))

    def show_status(self, status, message=None):
        raw_status = status.lower()
        if raw_status != 'passed':
            output_buffer.seek(0, 0)
            sys.stdout.write(output_buffer.read(-1))
        if message is None:
            last_part = ''
        else:
            last_part = ': %s' % (message,)
        print "%7s: %s%s" % (status, self.name, last_part)
        return raw_status

    def compare_results(self, actual):
        posttest_result = self.get_posttest_result()
        self.clean()
        status, expected = self.get_shell_results()
        self.clean()
        if expected != actual:
            print >>output_buffer, "Only in baseline results:"
            print >>output_buffer, '\n'.join(expected.difference(actual))
            print >>output_buffer, "Only in actual results:"
            print >>output_buffer, '\n'.join(actual.difference(expected))
            return self.show_status('FAILED')
        elif posttest_result != 0:
            print >>output_buffer, "Posttest gave status code", posttest_result
            return self.show_status('FAILED')
        return self.show_status('Passed')
    
    def have_error_mismatch(self, status):
        if self.error and (status == 0):
            return "dtrx did not return expected error"
        elif (not self.error) and (status != 0):
            return "dtrx returned error code %s" % (status,)
        return None

    def grep_output(self, output):
        for pattern in self.grep:
            if not re.search(pattern.replace(' ', '\\s+'), output,
                             re.MULTILINE):
                return "output did not match %s" % (pattern)
        for pattern in self.antigrep:
            if re.search(pattern.replace(' ', '\\s+'), output, re.MULTILINE):
                return "output matched antigrep %s" % (self.antigrep)
        return None

    def check_output(self, output):
        if ((self.output is not None) and
            (self.output.strip() != output.strip())):
            return "output did not match provided text"
        return None

    def check_results(self):
        output_buffer.seek(0, 0)
        output_buffer.truncate()
        self.clean()
        status, actual = self.get_extractor_results()
        output_buffer.seek(0, 0)
        output_buffer.readline()
        output = output_buffer.read(-1)
        problem = (self.have_error_mismatch(status) or
                   self.check_output(output) or self.grep_output(output))
        if problem:
            return self.show_status('FAILED', problem)
        if self.baseline:
            return self.compare_results(actual)
        else:
            self.clean()
            return self.show_status('Passed')

    def run(self):
        if self.directory:
            os.mkdir(self.directory)
            os.chdir(self.directory)
        try:
            result = self.check_results()
        except ExtractorTestError, error:
            result = self.show_status('ERROR', error)
        if self.directory:
            os.chdir(ROOT_DIR)
            subprocess.call(['chmod', '-R', '700', self.directory])
            subprocess.call(['rm', '-rf', self.directory])
        return result


test_db = open('tests.yml')
test_data = syck.load(test_db.read(-1))
test_db.close()
tests = [ExtractorTest(**data) for data in test_data]
for original_data in test_data:
    if (original_data.has_key('directory') or
        (not original_data.has_key('baseline'))):
        continue
    data = original_data.copy()
    data['name'] += ' in ..'
    data['directory'] = 'inside-dir'
    data['filenames'] = ' '.join(['../%s' % filename for filename in
                                  data.get('filenames', '').split()])
    tests.append(ExtractorTest(**data))
results = [test.run() for test in tests]
counts = {}
for outcome in OUTCOMES:
    counts[outcome] = 0
for result in results:
    counts[result] += 1
print " Totals:", ', '.join(["%s %s" % (counts[key], key) for key in OUTCOMES])
input_buffer.close()
output_buffer.close()
