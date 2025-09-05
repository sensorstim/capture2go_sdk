# SPDX-FileCopyrightText: 2025 SensorStim Neurotechnology GmbH <support@capture2go.com>
#
# SPDX-License-Identifier: MIT

import asyncio
import sys
import time
from pathlib import Path
from typing import AsyncGenerator

from bleak import BleakScanner, BleakClient
from bleak.backends.device import BLEDevice as BleakBLEDevice
from bleak.backends.scanner import AdvertisementData
from bleak.backends.characteristic import BleakGATTCharacteristic

from . import pkg
from .device import AbstractDevice


NUS_SERVICE = '80030001-e629-4c98-9324-aa7fc0c66de7'
NUS_RX = '80030002-e629-4c98-9324-aa7fc0c66de7'
NUS_TX = '80030003-e629-4c98-9324-aa7fc0c66de7'


class BleDevice(AbstractDevice):
    """
    Represents a single BLE IMU device.

    Usually created by :func:`capture2go.connect` or :class:`capture2go.BleScanner`.

    Args:
        device (:class:`~bleak.backends.device.BLEDevice`): The BLE device instance.
        rssi (int, optional): Initial RSSI value. Defaults to 0.
    """
    device: BleakBLEDevice
    """The underlying bleak ``BLEDevice`` instance."""
    rssi: int
    """The most recently observed RSSI (signal strength) for this device (updated only while scanning)."""

    def __init__(self, device: BleakBLEDevice, rssi=0):
        super().__init__()
        self.device = device
        self.rssi = rssi
        self.name = device.name if device.name is not None else ''

        self._client = None

    def __repr__(self) -> str:
        return f'BleDevice(state={self.state}, rssi={self.rssi})'

    async def send(self, package: pkg.AbstractPackage):
        data = package.pack()
        if self._client is None:
            raise RuntimeError('trying to send while BleakClient does not exist yet')
        await self._client.write_gatt_char(NUS_RX, data)

    async def connect(self):
        self._client = BleakClient(self.device, disconnected_callback=self._onDisconnect)
        self.state = 'connecting'
        for listener in self._stateListeners:
            listener(self, 'connecting')
        await self._client.connect()
        await self._client.start_notify(NUS_TX, self._onData)
        # The connect sentinel ensures that the queue is not empty if a disconnect sentinel is found.
        self._queue.put_nowait(self._connectSentinel)
        self._deviceInfoReceived.clear()
        self._statusReceived.clear()
        self.state = 'connected'
        for listener in self._stateListeners:
            listener(self, 'connected')

    async def disconnect(self):
        if self.state != 'disconnected' and self._client is not None:
            await self._client.disconnect()
            self.state = 'disconnected'
            for listener in self._stateListeners:
                listener(self, 'disconnected')

    def _onData(self, _: BleakGATTCharacteristic, data: bytearray):
        # print(f'received: {data.hex()!r}')
        self._feed(data, time.time_ns(), True)

    def _onDisconnect(self, _: BleakClient):
        self.state = 'disconnected'
        for listener in self._stateListeners:
            listener(self, 'disconnected')
        self._queue.put_nowait(self._disconnectSentinel)


class BleScanner:
    """BLE device scanner for IMU sensors.

    Usage example (see also :func:`capture2go.connect`)::

        async def findDevice(name: str):
            scanner = BleScanner()
            async for found in scanner.scan():
                print(f'Discovered devices: {found}.')
                if name in found:
                    return found[name]
    """
    def __init__(self):
        self.devices = {}

    async def scan(self) -> AsyncGenerator[dict[str, BleDevice], None]:
        """Asynchronously scan for BLE IMU devices.

        Yields:
            dict[str, BleDevice]: A dictionary mapping device names to :class:`BleDevice` objects.

        This is an async generator that yields the current set of discovered devices every second or when a new device
        is found or updated.
        """
        self.devices.clear()
        updated = asyncio.Event()

        def callback(device: BleakBLEDevice, advertisementData: AdvertisementData):
            if device.name in self.devices:
                self.devices[device.name].rssi = advertisementData.rssi
            else:
                self.devices[device.name] = BleDevice(device, advertisementData.rssi)
            updated.set()

        async with BleakScanner(callback, service_uuids=[NUS_SERVICE]):
            while True:
                try:
                    await asyncio.wait_for(updated.wait(), timeout=1.0)
                except (asyncio.exceptions.TimeoutError, TimeoutError):
                    pass
                updated.clear()
                yield self.devices.copy()


async def connect(names: list[str]) -> list[AbstractDevice]:
    """
    Connect to one or more IMU devices by name.

    Pass device names like ``IMU_1234b`` to connect to a sensor over BLE.

    To connect to a single device over USB, use ``usb`` as the device name. This will throw a RuntimeError if multiple
    USB devices are found.

    To connect to multiple or specific USB devices, pass device names (like ``/dev/tty.usbmodem*`` or ``COM1`` on
    Windows).

    If BLE devices names are passed, a Bluetooth scan is started and connection is initiated once all devices are
    discovered.

    Args:
        names (list[str]): List of device names (e.g., ['IMU_1234ab', 'usb', ...]).

    Returns:
        list[AbstractDevice]: List of connected :class:`AbstractDevice` instances
        (e.g., :class:`BleDevice`, :class:`UsbDevice`).

    Raises:
        RuntimeError: If no matching USB device is found or multiple USB devices are found.
    """
    devices: dict[str, AbstractDevice | None] = {}

    for name in names:
        if name.startswith('IMU_'):
            devices[name] = None
        elif name == 'usb':
            port = _discoverUsbSerialPort()
            from .usb import UsbDevice
            devices[name] = UsbDevice(port)
        else:
            if sys.platform in ('win32', 'cygwin', 'msys'):
                assert name.upper().startswith('COM')
            else:
                assert name.startswith('/dev/') and Path(name).is_char_device()
            from .usb import UsbDevice
            devices[name] = UsbDevice(name)

    if not names or any(device is None for device in devices.values()):
        scanner = BleScanner()
        async for found in scanner.scan():
            devices.update(found)
            missing = [name for name in names if devices[name] is None]
            print(f'Devices: {found}, missing: {", ".join(missing) if missing else "none"}.')
            if names and not missing:
                print('All devices discovered, connecting...')
                break

    deviceList = [device for name in names if (device := devices[name]) is not None]
    assert len(deviceList) == len(names), 'did not discover all devices'
    await asyncio.gather(*[imu.connect() for imu in deviceList])
    print('Connected.')
    return deviceList


def _discoverUsbSerialPort():
    if sys.platform in ('win32', 'cygwin', 'msys'):
        from serial.tools import list_ports
        ports = [p.device for p in list_ports.comports() if p.device.upper().startswith('COM')]
        if len(ports) == 1:
            return ports[0]
        elif len(ports) > 1:
            raise RuntimeError(f'More than one COM port found: {ports}. Pass a specific COMx name instead of "usb".')
        else:
            raise RuntimeError('No COM port found.')
    else:
        if sys.platform == 'darwin':
            pattern = 'tty.usbmodem??????1'
        else:
            pattern = 'ttyACM*'
        candidates = list(Path('/dev').glob(pattern))
        if len(candidates) == 1:
            return str(candidates[0].absolute())
        elif len(candidates) > 1:
            raise RuntimeError(f'More than one /dev/{pattern} devices found: {sorted([str(c) for c in candidates])}.')
        else:
            raise RuntimeError(f'No /dev/{pattern} device found.')
