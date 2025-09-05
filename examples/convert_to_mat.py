#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 SensorStim Neurotechnology GmbH <support@capture2go.com>
#
# SPDX-License-Identifier: MIT

import os
import argparse
import gzip
import numpy as np
import scipy.io as spio
from collections import defaultdict

import capture2go


def dumpFile(filename: str):
    print(f'{filename}:')
    with open(filename, 'rb') as f:
        unpacker = capture2go.Unpacker(f)
        for entry in unpacker:
            print(entry)


def loadFile(filename: str) -> dict[str, dict[str, np.ndarray]]:
    entries_by_key = defaultdict(list)
    with gzip.open(filename, 'rb') if filename.endswith('.gz') else open(filename, 'rb') as f:
        unpacker = capture2go.Unpacker(f, ignoreInitialGarbage=True)
        for pkg in unpacker:
            key = pkg.__class__.__name__
            entries_by_key[key].append(pkg.parse())

    data: dict[str, dict[str, np.ndarray]] = {}
    for key, entries in entries_by_key.items():
        if not entries:
            continue
        data[key] = {}
        for k in entries[0]:
            first = entries[0][k]
            if isinstance(first, np.ndarray):
                if first.ndim == 2:
                    val = np.concatenate([e[k] for e in entries])
                else:
                    val = np.array([e[k] for e in entries])
            else:
                val = np.array([e[k] for e in entries])
            data[key][k] = val
    return data


def generateMatFilename(filename: str, out: str | None):
    assert not filename.endswith('.mat'), 'input filename cannot end with .mat'
    if out is not None:
        return out
    if filename.endswith('.gz'):
        return os.path.splitext(filename[:-3])[0] + '.mat'
    else:
        return os.path.splitext(filename)[0] + '.mat'


def main():
    parser = argparse.ArgumentParser(description='Converts binary Capture2Go recordings to .mat files.')
    parser.add_argument('-o', '--out', help='output filename, default: derived from input filename')
    parser.add_argument('-f', '--force', action='store_true', help='overwrite existing output file')
    parser.add_argument('-d', '--dump', action='store_true', help='print parsed package content to stdout')
    parser.add_argument('files', metavar='FILE', nargs='+', help='input filename(s)')
    args = parser.parse_args()

    for file in args.files:
        if not os.path.exists(file):
            parser.error(f'input file not found: "{file}"')

    if args.dump:
        for file in args.files:
            dumpFile(file)
        return

    for file in args.files:
        out = generateMatFilename(file, args.out)

        if not args.force and os.path.exists(out):
            parser.error(f'output file already exists: "{out}" (use -f to overwrite)')

    for file in args.files:
        out = generateMatFilename(file, args.out)
        data = loadFile(file)
        spio.savemat(out, data, long_field_names=True, do_compression=True, oned_as='column')


if __name__ == '__main__':
    main()
