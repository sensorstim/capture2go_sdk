# SPDX-FileCopyrightText: 2025 SensorStim Neurotechnology GmbH <support@capture2go.com>
#
# SPDX-License-Identifier: MIT

import asyncio
import threading
import time
import serial

from .device import AbstractDevice


def _readSerial(ser: serial.Serial, loop: asyncio.AbstractEventLoop, device: 'UsbDevice'):
    """
    This function is running in a thread to continuously read data from the serial port.
    Without using threads, the receive buffer might fill up easily when data processing takes too long.
    """
    try:
        while True:
            waiting = ser.in_waiting
            data = ser.read(waiting if waiting >= 16 else 256)
            if data:
                loop.call_soon_threadsafe(device._onData, time.time_ns(), data)
    except (serial.SerialException, OSError, TypeError):
        loop.call_soon_threadsafe(device._onData, time.time_ns(), None)  # Disconnect sentinel.


class UsbDevice(AbstractDevice):
    """
    Represents a USB-connected IMU device.

    Args:
        device (str): Path to the serial device (e.g., ``/dev/tty.usbmodem...`` or ``COM1`` on Windows).
        baud (int, optional): Baud rate for the serial connection. Defaults to 2147483647.
    """
    def __init__(self, device: str, baud=2147483647):
        super().__init__()
        self._device = device
        self._baud = baud
        self._ser = None
        self._thread = None

    async def connect(self):
        assert self._ser is None, 'must be disconnected'

        self._ser = serial.Serial(self._device, self._baud, timeout=0.01)
        self._ser.reset_input_buffer()

        self._thread = threading.Thread(target=_readSerial, args=(self._ser, asyncio.get_running_loop(), self))
        self._thread.daemon = True
        self._thread.start()

        self._deviceInfoReceived.clear()
        self._statusReceived.clear()
        self.state = 'connected'
        for listener in self._stateListeners:
            listener(self, 'connected')
        # The connect sentinel ensures that the queue is not empty if a disconnect sentinel is found.
        self._queue.put_nowait(self._connectSentinel)

    async def disconnect(self):
        self._disconnect()

    async def send(self, package):
        assert self._ser is not None
        self._ser.write(package.pack())
        self._ser.flush()

    def _disconnect(self):
        if self.state == 'disconnected':
            return
        assert self._ser is not None
        assert self._thread is not None

        self._ser.close()
        del self._ser
        self._ser = None

        self._thread.join()
        self._thread = None
        self.state = 'disconnected'
        for listener in self._stateListeners:
            listener(self, 'disconnected')
        self._queue.put_nowait(self._disconnectSentinel)

    def _onData(self, timestamp: int, data: bytes | None):
        if data is None:
            if self.state != 'disconnected':
                self._disconnect()
            return
        self._feed(data, timestamp, extractRtPackages=False)
