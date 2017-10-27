#!/usr/bin/env python
# Copyright (c) 2014 Quanlong. All rights reserved.
#
# \author: Quanlong <quanlong.he@gmail.com>
#
# Updated by Ivo Pisarovic 2017.
# Added swift syntax.
#
# Example run:
# python generate_localized_strings.py -p ProjectFolderName -o "ProjectFolderName/cs.lproj/Localizable.strings"

import subprocess
import re
import optparse
import sys
import os

def LoadRecords(file):
    """
    Load localized strings from given |file|.
    """
    records = list()

    with open(file, 'r') as f:
        pattern = '^/\* (.*) \*/\n"(.*)" = "(.*)";$'
        ere_posix = re.compile(pattern, re.MULTILINE)

        # Parse all records
        for i in ere_posix.finditer(f.read()):
            records.append({
                'key': i.group(2),
                'description': i.group(1),
                'localized_value': i.group(3)
            })

    return records

def OverrideRecords(a, b):
    """
    Given set a and b, return a | (a & b)

    a & b = M
    L = a - M
    R = b - M
    a | (a & b) = L | (M - R)
    """
    a_keys = set([i['key'] for i in a])
    b_keys = set([i['key'] for i in b])

    m_keys = a_keys & b_keys
    l_keys = a_keys - m_keys
    r_keys = b_keys - m_keys

    # L
    records = filter(lambda x:x['key'] not in m_keys, a)

    # M - R
    records.extend(filter(lambda x:x['key'] in m_keys, b))

    # Remove duplicated keys
    records = [dict(tupleized)
                for tupleized in set(tuple(i.items()) for i in records)]

    # Sort by key
    records = sorted(records, key=lambda k: k['key'])

    print 'Keys: %d (+%d, -%d)' % (len(records), len(l_keys), len(r_keys))

    return records

def MultiFileFind(pattern, file_globs):
    """Implements fast multi-file find.

    Given an |pattern| string, find matching files by running git grep
    on |pattern| in files matching any pattern in |file_globs|.

    Args:
    pattern: 'NSLocalizedString\("([_A-Z]+)", comment: "(.*)"\)'
        file_globs: ['*.cc', '*.h', '*.m', '*.mm']

    Returns the lines of matched.

    Raises an exception on error.
    """
    out, err = subprocess.Popen(
        ['git', 'grep', '-h', '-E', pattern, '--'] + file_globs,
        stdout=subprocess.PIPE,
        shell=False).communicate()

    records = list()
    ere_posix = re.compile(pattern)
    for i in ere_posix.finditer(out):
        key = i.group(1)
        description = key
        if len(i.groups()) >= 2:
            description = i.group(2)
        records.append({
            'key': key,
            'description': description,
            'localized_value': description
        })

    print "Found %d keys with pattern '%s'" % (len(records), pattern)

    return records

def Render(records, template, output):
    """Render records to file.

    Renderer |records| to |output| file with given |template|.

    Args:
        records: a list of dict, dict should have 'key', 'descritpion'
            and 'localized_value' keys.
        template: string of renderer template.
        output: dev.strings
    """
    with open(output, 'wb') as f:
        for r in records:
            f.write(template % r)

    print 'Render keys into', output

def main():
    parser = optparse.OptionParser(usage=' %prog [-o <output_file>] [-t template]')
    parser.add_option('-p',
                      type='string',
                      action='store',
                      dest='project_path',
                      default='.',
                      metavar='<project_path>',
                      help='Project path')
    parser.add_option('-o',
                      type='string',
                      action='store',
                      dest='renderered_file',
                      default='Assets/en.lproj/Localizable.strings',
                      metavar='<renderered_file>',
                      help='Output file')
    parser.add_option('-t',
                      type='string',
                      action='store',
                      dest='template',
                      default= """\
/* %(description)s */
"%(key)s" = "%(key)s";

""",
                      metavar='<template>',
                      help='Template string')

    opts, args = parser.parse_args()

    opts.renderered_file = os.path.abspath(opts.renderered_file)

    records = list()

    os.chdir(opts.project_path)

    # Scan source files.
    records.extend(MultiFileFind('NSLocalizedString\("([^"]+)", comment: "([^"]*)"\)', ['*.swift']))
    records.extend(MultiFileFind('"([^"]+)".localized', ['*.swift']))

    # Scan storyboards and xibs.
    records.extend(MultiFileFind(
        '="\^([_A-Z]+)\^([^=]+)"[ >]',
        ['*.storyboard', '*.xib']))

    # Scan storyboards and xibs for long strings
    records.extend(MultiFileFind(
        '>\^([_A-Z]+)\^(.*?)<',
        ['*.storyboard', '*.xib']))

    records = OverrideRecords(records, LoadRecords(opts.renderered_file))

    # Render to file.
    Render(records, opts.template, opts.renderered_file)

if __name__ == '__main__':
      sys.exit(main())
