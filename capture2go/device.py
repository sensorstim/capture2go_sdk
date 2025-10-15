# SPDX-FileCopyrightText: 2025 SensorStim Neurotechnology GmbH <support@capture2go.com>
#
# SPDX-License-Identifier: MIT

import asyncio
import time
from typing import Any, Callable, Literal, TypeVar, Union

from . import pkg
from .parsing import Unpacker

DeviceState = Literal['disconnected', 'connecting', 'connected']
StateListener = Callable[['AbstractDevice', DeviceState], Any]
DataListener = Callable[['AbstractDevice', bytes | bytearray, int | None], Any]
PackageListener = Callable[['AbstractDevice', pkg.AbstractPackage, int | None], Any]
T = TypeVar('T', bound="pkg.AbstractPackage")


class DeviceIsRecording(RuntimeError):
    """
    Raised by :py:meth:`AbstractDevice.init` if the device is currently recording
    and the parameter ``abortRecording`` was not set to ``True``.
    """
    pass


class DeviceIsStreaming(RuntimeError):
    """
    Raised by :py:meth:`AbstractDevice.init` if the device is currently streaming
    and the parameter ``abortStreaming`` was not set to ``True``.
    """
    pass


class AbstractDevice:
    """
    Base class that represents a single IMU device (BLE or USB).

    This class can be used to send packages to the device and receive packages. Callbacks can be registered for state
    changes and for received packages.

    Standard async usage for receiving packages::

        await imu.connect()
        await imu.init()
        await imu.send(...)
        async for package in imu:
            print(package)

        # or:
        package = await imu.apoll()  # waits until a package is available
        print(package)

    Non-blocking usage::

        package = imu.poll()
        if package is not None:
            print(package)

        # or:
        while (package := imu.poll()) is not None:
            print(package)

    """
    name: str
    """The device name (e.g., ``IMU_ab1234``), might be an empty string until initialized."""
    state: DeviceState
    """The current state of the device connection. (:py:data:`DeviceState`)"""
    status: pkg.DataStatus | None
    """Provides access to the last received status package from the device."""
    deviceInfo: pkg.DataDeviceInfo | None
    """Provides access to the last received device info package from the device."""

    def __init__(self):
        self.name = ''
        self.state = 'disconnected'
        self.status = None
        self.deviceInfo = None

        self.unpacker = Unpacker(ignoreInitialGarbage=True)
        self._queue = asyncio.Queue()
        self._statusReceived = asyncio.Event()
        self._deviceInfoReceived = asyncio.Event()
        self._connectSentinel = object()
        self._disconnectSentinel = object()

        self._stateListeners: set[StateListener] = set()
        self._dataWithRtListeners: set[DataListener] = set()
        self._dataListeners: set[DataListener] = set()
        self._packageListeners: set[PackageListener] = set()

    async def connect(self):
        """Opens a connection to the device."""
        raise NotImplementedError()

    async def disconnect(self):
        """Closes the connection to the device."""
        raise NotImplementedError()

    async def init(self, setTime=False, abortRecording=False, abortStreaming=False):
        """Performs initial communication with the device to ensure a consistent state.

        This function should be called immediately after :py:meth:`AbstractDevice.connect`. It will send a
        :py:class:`pkg.CmdGetDeviceInfo` package and wait for the response as well as the initial
        :py:class:`pkg.DataStatus` package. Depending on the arguments, it will perform additional initialization
        steps.

        Args:
            setTime (bool, optional): Set the sensor clock based on the current system time. Defaults to False.
            abortRecording (bool, optional): Aborts any ongoing recording. Defaults to False, in which case
                :py:exc:`DeviceIsRecording` is raised if the device is recording.
            abortStreaming (bool, optional): Aborts any ongoing streaming and clears the send buffer. Defaults to False,
                in which case :py:exc:`DeviceIsStreaming` is raised if the device is streaming.
        """
        assert self.state == 'connected'

        # Request device info. (Status is sent automatically immediately after connecting.)
        # Note: For USB devices, it's sending CmdGetDeviceInfo is also necessary to start communication.
        await self.send(pkg.CmdGetDeviceInfo())

        await self._statusReceived.wait()
        assert self.status is not None

        if self.status.sensorState == pkg.SensorState.RECORDING:
            if abortRecording:
                await self.send(pkg.CmdStopRecording())
            else:
                raise DeviceIsRecording()
        elif self.status.sensorState == pkg.SensorState.STREAMING:
            if abortStreaming:
                self.unpacker.waitForAckStopStreamingAndClearBuffer = True
                await self.send(pkg.CmdStopStreamingAndClearBuffer())

                # Wait for ACK and filter out data packages from aborted streaming.
                keep = []
                async for package in self:
                    name = package.__class__.__name__
                    if (name.startswith(('DataFull', 'DataQuat'))
                            or name in ('DataRawBurst', 'DataAccZBurst', 'DataFsBytes')):
                        continue  # Ignore data packages but keep everything else.
                    keep.append(package)
                    if isinstance(package, pkg.AckStopStreamingAndClearBuffer):
                        break
                while not self._queue.empty():
                    keep.append(self._queue.get_nowait())

                # Put packages back in queue.
                for package in keep:
                    self._queue.put_nowait(package)

                if not self._deviceInfoReceived.is_set():
                    await self.send(pkg.CmdGetDeviceInfo())
            else:
                raise DeviceIsStreaming()

        await self._deviceInfoReceived.wait()

        # Set the clock on the sensor based on the current system time.
        # Note: When working with multiple devices, only set this for one device (the sender) and configure the other
        # devices as sync receivers in CmdSetMeasurementMode.
        if setTime:
            await self.send(pkg.CmdSetAbsoluteTime(newTimestamp=time.time_ns()))

    async def send(self, package: pkg.AbstractPackage):
        """Sends a package to the device.

        Args:
            package (pkg.AbstractPackage): The package to be sent.
        """
        raise NotImplementedError()

    async def sendAndAwaitAck(
        self,
        package: pkg.AbstractPackage,
        ackCls: type[T],
        timeout: float = 3.0
    ) -> Union[T, pkg.SensorError]:
        """Sends a package to the device and waits for the acknowledgement (or an error or a timeout).

        The return value is either the expected acknowledgement package or a ``SensorError`` package that refers to the
        sent package.

        Raises a ``TimeoutError`` if the package was not received within ``timeout`` seconds.

        Args:
            package (pkg.AbstractPackage): The package to be sent.
            ackCls (type[T]): The class of the expected acknowledgement package.
            timeout (float, optional): Maximum time in seconds to wait for the acknowledgement. Defaults to 3.
        """
        loop = asyncio.get_running_loop()
        future = loop.create_future()

        def listener(device, received: pkg.AbstractPackage, timestamp):
            if type(received) is ackCls:
                if not future.done():
                    future.set_result(received)
            if type(received) is pkg.SensorError and received.command == package.header:
                if not future.done():
                    future.set_result(received)

        self.addPackageListener(listener)
        try:
            await self.send(package)
            try:
                result = await asyncio.wait_for(future, timeout=timeout)
            except asyncio.TimeoutError:
                raise TimeoutError(f'Timeout waiting for ACK ({ackCls.__name__})')
            return result
        finally:
            self.removePackageListener(listener)

    def addStateListener(self, listener: StateListener):
        """Registers a callback function that is called when the connection state changes.

        Args:
            listener (:py:data:`StateListener`): A function that gets called with the device and the new state as
                parameters.
        """
        self._stateListeners.add(listener)

    def removeStateListener(self, listener: StateListener):
        """Unregisters a callback function that is called when the connection state changes.

        Args:
            listener (:py:data:`StateListener`): A callback function that was previously registered as a state
                listener.
        """
        self._stateListeners.remove(listener)

    def addDataWithRtListener(self, listener: DataListener):
        """Registers a callback that is invoked when raw data (including RT packages) is received.

        The callback is called before real-time (RT) packages are extracted from the incoming BLE chunk. This is
        useful if you need access to the unmodified BLE payload.

        Args:
            listener (:py:data:`DataListener`): A function that gets called with the device, the raw data chunk
                (including RT packages), and an optional receive timestamp.
        """
        self._dataWithRtListeners.add(listener)

    def removeDataWithRtListener(self, listener: DataListener):
        """Unregisters a previously registered raw data (with RT) listener.

        Args:
            listener (:py:data:`DataListener`): A callback function that was previously registered as a data (with RT)
                listener.
        """
        self._dataWithRtListeners.remove(listener)

    def addDataListener(self, listener: DataListener):
        """Registers a callback that is invoked when data is received (after RT extraction).

        The callback is called after real-time (RT) packages have been removed (if present) and before the data is
        fed to the unpacker. Use this to observe the stream that is parsed into packages.

        Args:
            listener (:py:data:`DataListener`): A function that gets called with the device, the data chunk after RT
                extraction, and an optional receive timestamp.
        """
        self._dataListeners.add(listener)

    def removeDataListener(self, listener: DataListener):
        """Unregisters a previously registered data listener.

        Args:
            listener (:py:data:`DataListener`): A callback function that was previously registered as a data listener.
        """
        self._dataListeners.remove(listener)

    def addPackageListener(self, listener: PackageListener):
        """Registers a callback that is invoked for each extracted package.

        The callback is called for every package produced by the unpacker. It is invoked before the package is enqueued
        for iteration/polling.

        Args:
            listener (:py:data:`PackageListener`): A function that gets called with the device, the package,
                and an optional receive timestamp.
        """
        self._packageListeners.add(listener)

    def removePackageListener(self, listener: PackageListener):
        """Unregisters a previously registered package listener.

        Args:
            listener (:py:data:`PackageListener`): A callback function that was previously registered as a package
                listener.
        """
        self._packageListeners.remove(listener)

    def poll(self):
        """
        Polls the device for received packages. Returns either a package or None.
        """
        try:
            while True:
                package = self._queue.get_nowait()
                if package is self._connectSentinel or package is self._disconnectSentinel:
                    continue
                return package
        except asyncio.QueueEmpty:
            return None

    async def apoll(self):
        """
        Asynchronous poll method that returns the next package. If no package is available, the method waits without
        blocking the event loop.
        """
        while True:
            package = await self._queue.get()
            if package is self._connectSentinel:
                continue
            if package is self._disconnectSentinel:
                if self._queue.empty():
                    raise StopAsyncIteration
                else:
                    continue  # Ignore because the device must have been reconnected in the meantime.
            return package

    def __aiter__(self):
        return self

    async def __anext__(self):
        package = await self.apoll()
        return package

    def _feed(self, data: bytes | bytearray, timestamp: int | None, extractRtPackages: bool):
        if extractRtPackages:
            for listener in self._dataWithRtListeners:
                listener(self, data, timestamp)
            data = self.unpacker.extractRtPackages(data, timestamp)

        for listener in self._dataListeners:
            listener(self, data, timestamp)
        self.unpacker.feed(data)

        while True:
            try:
                package = next(self.unpacker)

                if isinstance(package, pkg.DataDeviceInfo):
                    self.deviceInfo = package
                    self.name = f'IMU_{package.parse()["serial"]}'
                    self._deviceInfoReceived.set()
                elif isinstance(package, pkg.DataStatus):
                    self.status = package
                    self._statusReceived.set()
                elif (isinstance(package, pkg.DataClockRoundtrip) and timestamp is not None
                      and package.hostReceiveTimestamp == 0):
                    package.hostReceiveTimestamp = timestamp

                for listener in self._packageListeners:
                    listener(self, package, timestamp)
                self._queue.put_nowait(package)
            except StopIteration:
                return


class FilePlaybackDevice(AbstractDevice):
    """
    Device that replays data from a file as if it were a live IMU device.

    This is useful for development and testing, allowing you to execute processing code without interacting with real
    hardware.

    Limitations:
        - Stored packages are played back without any delay, so this will not work for timing-sensitive code.
        - Any packages sent to the device (e.g., via ``send``) will be ignored.

    Args:
        filename (str): Path to the binary file containing recorded IMU data to play back.
    """
    def __init__(self, filename: str):
        super().__init__()
        self.f = open(filename, 'rb')
        self.unpacker = Unpacker(self.f, ignoreInitialGarbage=False)
        self.state = 'connected'

    async def connect(self):
        self.state = 'connected'
        for listener in self._stateListeners:
            listener(self, 'connected')

    async def disconnect(self):
        self.state = 'disconnected'
        for listener in self._stateListeners:
            listener(self, 'disconnected')

    async def init(self, setTime=False, abortRecording=False, abortStreaming=False):
        pass

    async def send(self, package):
        print(f'warning: ignoring "send" in FilePlaybackDevice ({package})')

    def poll(self):
        # try:
        return next(self.unpacker)
        # except StopIteration:
        #     return None

    async def apoll(self):
        # return self.poll()
        try:
            return self.poll()
        except StopIteration:
            raise StopAsyncIteration
