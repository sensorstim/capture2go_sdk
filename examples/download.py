#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 SensorStim Neurotechnology GmbH <support@capture2go.com>
#
# SPDX-License-Identifier: MIT

import argparse
import asyncio
import sys
from pathlib import Path
import capture2go as c2g


async def listFiles(imu: c2g.AbstractDevice) -> list[str]:
    names: list[str] = []
    await imu.send(c2g.pkg.CmdFsListFiles())
    count = None
    print(f'Listing files on {imu.name}...')
    async for package in imu:
        if isinstance(package, c2g.pkg.DataFsFileCount):
            count = package.fileCount
            if count == 0:
                print('No files found.')
                break
        elif isinstance(package, c2g.pkg.DataFsFile):
            name = package.filename.decode()
            size = package.size
            index = package.index
            names.append(name)
            print(f'{index + 1:3d}/{count}  {size:10d}  {name}')
            if count is not None and (index + 1) == count:
                print('Done.')
                break
        elif isinstance(package, c2g.pkg.DataStatus):
            continue  # Ignore.
    return names


async def downloadFile(imu: c2g.AbstractDevice, filename: str, delete: bool = False) -> bool:
    sizePkg = await imu.sendAndAwaitAck(c2g.pkg.CmdFsGetSize(filename=filename.encode()), c2g.pkg.DataFsSize)
    assert isinstance(sizePkg, c2g.pkg.DataFsSize), 'failed to get size from sensor'
    assert sizePkg.filename == filename.encode()
    size = sizePkg.fileSize

    outPath = Path(f'{filename}_{imu.name}.bin')
    if outPath.exists():
        print(f'Error: Output file {outPath} already exists.', file=sys.stderr)
        sys.exit(1)

    print(f'Downloading {filename!r} ({size} bytes)...')
    with open(outPath, 'wb') as f:
        await imu.send(c2g.pkg.CmdFsGetBytes(filename=filename.encode(), startPos=0, endPos=0))
        received = 0
        async for package in imu:
            if not isinstance(package, c2g.pkg.DataFsBytes):
                continue  # Ignore unrelated packages while downloading.

            if package.offset != received:
                print(f'Error: offset {package.offset} does not match expected {received}. Aborting.')
                await imu.send(c2g.pkg.CmdFsStopGetBytes())
                return False

            f.write(package.payload)
            received += len(package.payload)
            print(f'Received {len(package.payload)} bytes, {received} of {size} received ({received/size*100:.1f}%)')

            if received == size:
                print(f'File transfer complete. Saved as {outPath}.')
                if delete:
                    await imu.sendAndAwaitAck(
                        c2g.pkg.CmdFsDeleteFile(filename=filename.encode()),
                        c2g.pkg.AckFsDeleteFile,
                    )
                    print(f'Deleted {filename!r} from device.')
                return True
    return False


async def downloadAll(imu: c2g.AbstractDevice, delete: bool = False):
    files = await listFiles(imu)

    existing = [path for name in files if (path := Path(f'{name}_{imu.name}.bin')).exists()]
    if existing:
        print(f'Error: The following {len(existing)} output file(s) already exist:', file=sys.stderr)
        for p in existing:
            print(f' - {p}', file=sys.stderr)
        print('Aborting.')
        sys.exit(1)

    successful = 0
    failed: list[str] = []
    for i, filename in enumerate(files):
        print(f'Downloading file {i+1} of {len(files)}: {filename!r}...')
        ok = await downloadFile(imu, filename, delete=delete)
        if ok:
            successful += 1
        else:
            failed.append(filename)

    if successful == len(files):
        print(f'All {len(files)} file(s) downloaded successfully.')
    else:
        print(f'Downloaded {successful}/{len(files)} file(s). Failed: {failed}.')


async def formatStorage(imu: c2g.AbstractDevice):
    print(f'Formatting storage on {imu.name}...')
    await imu.sendAndAwaitAck(c2g.pkg.CmdFsFormatFilesystem(), c2g.pkg.AckFsFormatFilesystem)
    print('Formatting complete.')


async def run(args: argparse.Namespace):
    imu, = await c2g.connect([args.device])
    try:
        # Init the device (setTime=True helps for listing; harmless for other ops)
        await imu.init(setTime=True, abortRecording=True, abortStreaming=True)

        if args.all:
            await downloadAll(imu, delete=args.delete)
        elif args.ls:
            await listFiles(imu)
        elif args.format:
            await formatStorage(imu)
        else:
            await downloadFile(imu, args.filename, delete=args.delete)
    finally:
        await imu.disconnect()


def main():
    parser = argparse.ArgumentParser(description='List, download, or manage files on a Capture2Go IMU.')
    parser.add_argument('device', help='IMU device name ("IMU_*" or "usb")')
    parser.add_argument('filename', nargs='?', help='Recording name to download')
    parser.add_argument('--delete', action='store_true',
                        help='Delete the file(s) on the device after successful download')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--ls', action='store_true', help='List files on the device')
    group.add_argument('--all', action='store_true', help='Download all files from the device')
    group.add_argument('--format', action='store_true', help='Format the device storage (ERASES ALL FILES)')

    args = parser.parse_args()
    if args.filename and (args.ls or args.all or args.format):
        parser.error('FILENAME cannot be combined with --ls, --all, or --format')
    if not (args.ls or args.all or args.format or args.filename):
        parser.error('No action specified. Use --ls, --all, --format, or provide a FILENAME to download.')

    asyncio.run(run(args))


if __name__ == '__main__':
    main()
