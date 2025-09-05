#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 SensorStim Neurotechnology GmbH <support@capture2go.com>
#
# SPDX-License-Identifier: MIT

import argparse
import asyncio
import copy
import json
import os
import time
import uuid
from datetime import timedelta
from pathlib import Path

import capture2go as c2g


PROFILE_TEMPLATE = {
    'type': 'capture2go_measurement_profile',
    'version': 1,
    'internalSensors': {
        'camera': None,
        'videoRotation': 'portrait',
        'microphone': None,
        'imu': None,
        'location': 0,
    },
    'sensors': [],  # To be filled with [{'name': 'imu1', 'id': 'IMU_1234ab'}, ...].
    'settings': {
        'quatOnly': False,
        'noMagData': False,
        'imuDataRate': 200,
        'duration': 0,
        'transferLater': False,
    },
    'stages': [
        {
            'type': 'measurement',
            'version': 1,
            'annotateButtons': ['Start', 'End', 'Repeat'],
        }
    ],
}

INFO_TEMPLATE = {
    'type': 'capture2go_recording',
    'version': 1,
    'name': 'Recording',
    'uuid': '',
    'filename': '',
    'startTimestamp': 0,  # In milliseconds.
    'startDate': '',      # '%Y-%m-%d %H:%M:%S'.
    'transferIncomplete': [],
}


class Annotations:
    def __init__(self, path: Path | str, startTime: float):
        self.path = Path(path)
        self.startTimeSec = startTime
        with open(self.path, 'w') as f:
            f.write('date,timestamp,elapsed,internal,event\n')

    def annotate(self, event: str, internal: bool = False):
        now = time.time()
        dateStr = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(now))
        elapsedTd = timedelta(seconds=int((now - self.startTimeSec)))
        with open(self.path, 'a') as f:
            f.write(f'{dateStr},{int(now * 1_000_000_000)},{elapsedTd},{int(internal)},{event}\n')


async def setupRecording(index: int, imu: c2g.AbstractDevice, filename: str, syncId: int):
    mode = c2g.pkg.CmdSetMeasurementMode(
        fullPackedMode=c2g.pkg.SamplingMode.MODE_200HZ,
        statusMode=1,
        syncMode=c2g.pkg.SyncMode.SYNC_SENDER if index == 0 else c2g.pkg.SyncMode.SYNC_RECEIVER,
        syncId=syncId,
    )

    await imu.init(setTime=(index == 0), abortRecording=True, abortStreaming=True)
    await imu.sendAndAwaitAck(mode, c2g.pkg.DataMeasurementMode)
    await imu.sendAndAwaitAck(c2g.pkg.CmdSetRecordingConfig(filename=filename.encode()), c2g.pkg.DataRecordingConfig)


async def startRecording(imu: c2g.AbstractDevice):
    await imu.sendAndAwaitAck(c2g.pkg.CmdStartRecording(), c2g.pkg.AckStartRecording)

    # Discard all packages received until now (`sendAndAwaitAck` won't clear them from the queue).
    async for package in imu:
        if isinstance(package, c2g.pkg.AckStartRecording):
            break


async def stopRecording(imu: c2g.AbstractDevice):
    await imu.sendAndAwaitAck(c2g.pkg.CmdStopRecording(), c2g.pkg.AckStopRecording)


async def downloadAndDelete(imu: c2g.AbstractDevice, filename: str, recordingDir: Path) -> bool:
    # Get file size from sensor.
    sizePkg = await imu.sendAndAwaitAck(c2g.pkg.CmdFsGetSize(filename=filename.encode()), c2g.pkg.DataFsSize)
    assert isinstance(sizePkg, c2g.pkg.DataFsSize), 'failed to get size from sensor'
    assert sizePkg.filename == filename.encode()
    size = sizePkg.fileSize

    # Download file contents.
    await imu.send(c2g.pkg.CmdFsGetBytes(filename=filename.encode(), startPos=0, endPos=0))
    received = 0
    outPath = recordingDir / 'raw' / f'{filename}_{imu.name}.bin'
    with open(outPath, 'wb') as f:
        async for package in imu:
            if not isinstance(package, c2g.pkg.DataFsBytes):
                continue

            if package.offset != received:
                print(f'[{imu.name}] Error: Offset {package.offset} does not match expected {received}. Aborting.')
                await imu.send(c2g.pkg.CmdFsStopGetBytes())
                return False

            received += len(package.payload)
            print(f'[{imu.name}] Received {len(package.payload)} bytes, '
                  f'{received} of {size} received ({received/size*100:.1f}%)')
            f.write(package.payload)

            if received == size:
                print(f'[{imu.name}] File transfer complete. Saved as {outPath}.')
                await imu.sendAndAwaitAck(c2g.pkg.CmdFsDeleteFile(filename=filename.encode()), c2g.pkg.AckFsDeleteFile)
                return True

    return False


async def record(imus: list[c2g.AbstractDevice]):
    startTime = time.time()
    recordingId = str(uuid.uuid4())
    baseTimeStr = time.strftime('%Y-%m-%d_%H%M%S', time.localtime(startTime))
    filename = f'{baseTimeStr}_{recordingId}'
    recordingDir = Path(f'{baseTimeStr}_Recording')
    os.makedirs(recordingDir / 'raw')

    # Initialize all IMUs and set the measurement and recording config.
    syncId = c2g.utils.generateSyncId()
    await asyncio.gather(*[setupRecording(i, imu, filename, syncId) for i, imu in enumerate(imus)])

    # Write profile.json to be compatible with recordings created by the mobile app.
    profile = copy.deepcopy(PROFILE_TEMPLATE)
    profile['sensors'] = [
        {'name': f'imu{i+1}', 'id': imu.name}
        for i, imu in enumerate(imus)
    ]
    with open(recordingDir / 'profile.json', 'w') as f:
        json.dump(profile, f, indent=2)

    # Write info.json to be compatible with recordings created by the mobile app.
    info = copy.deepcopy(INFO_TEMPLATE)
    info['uuid'] = recordingId
    info['filename'] = filename
    info['startTimestamp'] = int(startTime * 1000)
    info['startDate'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(startTime))
    info['transferIncomplete'] = [imu.name for imu in imus]
    with open(recordingDir / 'info.json', 'w') as f:
        json.dump(info, f, indent=2)

    # Start recording on all devices in parallel.
    await asyncio.gather(*[startRecording(imu) for imu in imus])

    annotations = Annotations(recordingDir / 'annotations.csv', startTime)
    annotations.annotate('MEASUREMENT_STARTED', internal=True)

    print('Recording... Press Ctrl+C to stop.')
    try:
        while True:
            for imu in imus:
                if (package := imu.poll()) is not None:
                    if isinstance(package, c2g.pkg.DataStatus):
                        print('.', end='', flush=True)
                    else:
                        print(f'\n{imu.name}: received during recording:', package)
            await asyncio.sleep(0.05)
    except (KeyboardInterrupt, asyncio.CancelledError):
        print('Recording stopped by user.')

    # Stop recording on all devices.
    await asyncio.gather(*[stopRecording(imu) for imu in imus])

    annotations.annotate('MEASUREMENT_STOPPED', internal=True)

    # Download files from the devices.
    for imu in imus:
        print(f'[{imu.name}] Downloading...')
        ok = await downloadAndDelete(imu, filename, recordingDir)
        if ok:
            info['transferIncomplete'].remove(imu.name)

    # Update info.json with final `transferIncomplete` list.
    with open(recordingDir / 'info.json', 'w') as f:
        json.dump(info, f, indent=2)

    if len(info['transferIncomplete']) == 0:
        print('All device recordings downloaded and deleted successfully.')
    else:
        print('Warning: some recordings failed to transfer:', info['transferIncomplete'])


async def main():
    parser = argparse.ArgumentParser(description='Record 200 Hz data from one or more IMUs and download the result.')
    parser.add_argument('devices', metavar='DEVICE', nargs='*', help='IMU device names (e.g., "IMU_*" or "usb")')
    args = parser.parse_args()

    if not args.devices:
        print('WARNING: No device names given, scanning only (use `--help` to print a help message).')

    imus = await c2g.connect(args.devices)

    try:
        await record(imus)
    finally:
        await asyncio.gather(*[imu.disconnect() for imu in imus])


if __name__ == '__main__':
    asyncio.run(main())
