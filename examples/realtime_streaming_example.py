#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 SensorStim Neurotechnology GmbH <support@capture2go.com>
#
# SPDX-License-Identifier: MIT

import argparse
import asyncio
import numpy as np

import capture2go as c2g


async def printOrientation(index: int, imu: c2g.AbstractDevice, mag: bool, euler: bool, raw: bool):
    indentation = ' '*(60*index)
    setTime = index == 0
    await imu.init(setTime=setTime)
    await imu.send(c2g.pkg.CmdStartRealTimeStreaming(mode=c2g.pkg.RealTimeDataMode.REAL_TIME_DATA_QUAT, rateLimit=0))
    async for package in imu:
        if raw or not isinstance(package, c2g.pkg.DataQuatFixedRt):
            print(f'{imu}: {package}')
        else:
            parsed = package.parse()
            t = parsed['timestamp']/1e9
            if mag:
                # Note: This is the same as `quat = c2g.utils.addHeading(parsed['quat'], parsed['delta'])`.
                quat = parsed['quat9D']
            else:
                quat = parsed['quat']
            if euler:
                angles = c2g.utils.eulerAngles(quat, 'zxy', True)
                orientation = f'{np.round(np.rad2deg(angles), 2)}'
            else:
                orientation = f'{quat}'
            print(f'{t:.3f} {indentation}{orientation}')


async def main():
    parser = argparse.ArgumentParser(description='Example for real-time streaming of IMU orientations.')
    parser.add_argument('-m', '--mag', action='store_true', help='use magnetometer data, i.e., print 9D orientations')
    parser.add_argument('-e', '--euler', action='store_true', help='print intrinsic z-x\'-y\'\' Euler angles '
                        'instead of quaternions')
    parser.add_argument('-r', '--raw', action='store_true', help='print full received packages')
    parser.add_argument('devices', metavar='DEVICE', nargs='*', help='IMU device names ("IMU_*" or "usb")')
    args = parser.parse_args()

    if not args.devices:
        print('WARNING: No device names given, scanning only (use `--help` to print a help message).')

    imus = await c2g.connect(args.devices)

    try:
        await asyncio.gather(*[printOrientation(i, imu, args.mag, args.euler, args.raw) for i, imu in enumerate(imus)])
    except asyncio.CancelledError:
        print('cancelled.')
    await asyncio.gather(*[imu.disconnect() for imu in imus])


if __name__ == '__main__':
    asyncio.run(main())
