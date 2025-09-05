#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 SensorStim Neurotechnology GmbH <support@capture2go.com>
#
# SPDX-License-Identifier: MIT
import asyncio
import capture2go as c2g


async def main():
    # Configure which sensor to connect to and if USB or BLE should be used.
    name = 'usb'  # Connect via USB (only one device can be connected).
    # name = '/dev/tty.usbmodemab12341'  # Connect to specific device via USB (use COM port name like COM1 on Windows).
    # name = 'IMU_ab1234'  # Connect via BLE, replace with your device ID.

    # Connect to device and initialize.
    devices = await c2g.connect([name])
    imu = devices[0]
    await imu.init(setTime=True, abortRecording=True, abortStreaming=True)

    # Configure the measurement mode and start data streaming.
    await imu.send(c2g.pkg.CmdSetMeasurementMode(
        timestamp=0,
        fullFloat200HzEnabled=False,
        fullFixedMode=c2g.pkg.SamplingMode.MODE_DISABLED,
        fullPackedMode=c2g.pkg.SamplingMode.MODE_200HZ,
        quatFloatMode=c2g.pkg.SamplingMode.MODE_DISABLED,
        quatFixedMode=c2g.pkg.SamplingMode.MODE_DISABLED,
        quatPackedMode=c2g.pkg.SamplingMode.MODE_DISABLED,
        statusMode=1,
        calibDataMode=c2g.pkg.CalibrationDataMode.CALIB_DATA_DISABLED,
        processExtensionMode=c2g.pkg.ProcessExtensionMode.NO_EXTENSION,
        syncMode=c2g.pkg.SyncMode.NO_SYNC,
        syncId=0,
        disableBiasEstimation=False,
        disableMagDistRejection=False,
        disableMagData=False,
    ))
    await imu.send(c2g.pkg.CmdStartStreaming())

    # Or alternatively, configure real-time streaming.
    # await imu.send(c2g.pkg.CmdStartRealTimeStreaming(
    #     mode=c2g.pkg.RealTimeDataMode.REAL_TIME_DATA_QUAT,
    #     rateLimit=0
    # ))

    # Print all packages received from the sensor.
    async for package in imu:
        print(package)

if __name__ == '__main__':
    asyncio.run(main())
