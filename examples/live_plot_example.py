#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 SensorStim Neurotechnology GmbH <support@capture2go.com>
#
# SPDX-License-Identifier: MIT

import argparse
import asyncio
import matplotlib
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import threading
import queue

import capture2go as c2g

# matplotlib.use('QtAgg')


async def getImuData(name: str, q: queue.Queue):
    imu, = await c2g.connect([name])
    await imu.init(setTime=True, abortStreaming=True)
    await imu.send(c2g.pkg.CmdSetMeasurementMode(fullPackedMode=c2g.pkg.SamplingMode.MODE_200HZ, statusMode=1))
    await imu.send(c2g.pkg.CmdStartStreaming())
    try:
        async for package in imu:
            q.put(package)
    except asyncio.CancelledError:
        print('Stopping streaming.')
        await imu.send(c2g.pkg.CmdStopStreaming())
        await imu.disconnect()


class ImuDataPlot:
    def __init__(self):
        self.queue = queue.Queue()

        self.N = 800  # Number of samples to plot (at 200 Hz).
        self.t = np.arange(-self.N, 0, dtype=float)/200
        self.gyr = np.full((self.N, 3), np.nan)
        self.acc = np.full((self.N, 3), np.nan)
        self.mag = np.full((self.N, 3), np.nan)
        self.euler = np.full((self.N, 3), np.nan)

        self.createPlot()

        self.anim = FuncAnimation(self.fig, self.updatePlot, interval=40, blit=True, cache_frame_data=False)

    def createPlot(self):
        self.fig = plt.figure(figsize=(10, 8), constrained_layout=True)
        self.ax = self.fig.subplots(2, 2)

        for ax in (self.ax[0, 0], self.ax[0, 1], self.ax[1, 0]):
            ax.set_prop_cycle('color', ['#d62728', '#2ca02c', '#1f77b4'])  # Use RGB color cycle.

        self.gyrLines = self.ax[0, 0].plot(self.t, self.gyr)
        self.ax[0, 0].set_xlim(self.t[0], self.t[-1])
        self.ax[0, 0].set_ylim(-800, 800)
        self.ax[0, 0].set_title('Gyroscope [°/s]')
        self.ax[0, 0].set_xlabel('Time [s]')
        self.ax[0, 0].legend('xyz', loc='upper left')

        self.accLines = self.ax[0, 1].plot(self.t, self.acc)
        self.ax[0, 1].set_xlim(self.t[0], self.t[-1])
        self.ax[0, 1].set_ylim(-20, 20)
        self.ax[0, 1].set_title('Accelerometer [m/s²]')
        self.ax[0, 1].set_xlabel('Time [s]')
        self.ax[0, 1].legend('xyz', loc='upper left')

        self.magLines = self.ax[1, 0].plot(self.t, self.mag)
        self.ax[1, 0].set_xlim(self.t[0], self.t[-1])
        self.ax[1, 0].set_ylim(-100, 100)
        self.ax[1, 0].set_title('Magnetometer [µT]')
        self.ax[1, 0].set_xlabel('Time [s]')
        self.ax[1, 0].legend('xyz', loc='upper left')

        self.ax[1, 1].set_prop_cycle('color', ['#1f77b4', '#d62728', '#2ca02c', ])  # Use BRG color cycle.
        self.eulerLines = self.ax[1, 1].plot(self.t, self.euler)
        self.ax[1, 1].set_xlim(self.t[0], self.t[-1])
        self.ax[1, 1].set_ylim(-180, 180)
        self.ax[1, 1].set_title('Orientation as z-x\'-y\'\' Euler angles [°]')
        self.ax[1, 1].set_xlabel('Time [s]')
        self.ax[1, 1].legend(['z', 'x\'', 'y\'\''], loc='upper left')

        for ax in self.ax.flatten():
            ax.grid()

    def updatePlot(self, frame):
        # Read IMU data from the queue.
        while True:
            try:
                package = self.queue.get_nowait()
                if isinstance(package, c2g.pkg.DataFullPacked):
                    parsed = package.parse()
                    self.gyr = np.vstack([self.gyr[8:], np.rad2deg(parsed['gyr'])])
                    self.acc = np.vstack([self.acc[8:], parsed['acc']])
                    self.mag = np.vstack([self.mag[8:], parsed['mag']])

                    euler = np.zeros((8, 3))
                    for i in range(8):
                        euler[i] = np.rad2deg(c2g.utils.eulerAngles(parsed['quat9D'][i], 'zxy', True))
                    self.euler = np.vstack([self.euler[8:], euler])
                else:
                    print('package:', package)
            except queue.Empty:
                break

        # Update the plot.
        for i, line in enumerate(self.gyrLines):
            line.set_ydata(self.gyr[:, i])
        for i, line in enumerate(self.accLines):
            line.set_ydata(self.acc[:, i])
        for i, line in enumerate(self.magLines):
            line.set_ydata(self.mag[:, i])
        for i, line in enumerate(self.eulerLines):
            line.set_ydata(self.euler[:, i])

        return self.gyrLines + self.accLines + self.magLines + self.eulerLines


def main():
    parser = argparse.ArgumentParser(description='Example for real-time streaming of IMU orientations.')
    parser.add_argument('device', help='IMU device name ("IMU_*" or "usb)')
    args = parser.parse_args()

    print(f'Using matplotlib backend {matplotlib.get_backend()!r}.')

    plot = ImuDataPlot()

    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_until_complete, args=(getImuData(args.device, plot.queue),), daemon=True)
    thread.start()

    plt.show()

    for task in asyncio.all_tasks(loop):
        task.cancel()
    thread.join()


if __name__ == '__main__':
    main()
