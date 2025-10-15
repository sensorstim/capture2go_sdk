# SPDX-FileCopyrightText: 2025 SensorStim Neurotechnology GmbH <support@capture2go.com>
#
# SPDX-License-Identifier: MIT

import ctypes
import zlib
from collections import defaultdict
from pathlib import Path

import numpy as np

from . import pkg


class Unpacker:
    """
    Unpacks and parses the binary IMU protocol data stream into package objects.

    This class can be used to feed raw bytes (from a file, serial port, or BLE) and iterate over parsed packages.

    Args:
        f (file-like, optional): File-like object to read data from. If None, data must be fed manually.
        ignoreInitialGarbage (bool, optional): If True, ignore bytes until a valid frame is found. This can be useful if
            file parsing is started in the middle of a byte stream and initial invalid data is to be expected. Defaults
            to False.

    Example::

        unpacker = Unpacker()
        unpacker.feed(receivedData)
        for package in unpacker:
            print(package)
    """
    def __init__(self, f=None, ignoreInitialGarbage=False):
        self.f = f
        self.ignoreInitialGarbage = ignoreInitialGarbage
        self.waitForAckStopStreamingAndClearBuffer = False
        self.buffer = bytearray()
        self.rtPackages = []

    def feed(self, data: bytes | bytearray):
        """
        Add new binary data to the internal buffer for parsing.

        Args:
            data (bytes | bytearray): Raw bytes to add to the buffer.
        """
        self.buffer.extend(data)
        # print(f'feed {self.buffer.hex()}')

    def clear(self):
        """
        Clear the internal buffer.
        """
        self.buffer.clear()

    def extractRtPackages(self, data: bytes | bytearray, receiveTimestamp=None):
        """
        Extract and parse real-time (RT) packages from data received over BLE.

        Every raw package sent over BLE contains a byte indicating the count of RT packages, followed by the RT
        packages and then by the data stream. When receiving this data, the RT packages first have to be extracted
        using this method. Then, the remaining data chunk can be passed to :py:meth:`feed`.

        The parsed packages are stored in this class and returned first when iterating over the data.

        Args:
            data (bytes | bytearray): Raw bytes containing RT packages.
            receiveTimestamp (int, optional): Timestamp (in nanoseconds, from :py:func:`time.time_ns`) to be used when
                ``DataClockRoundtrip`` packages are received. Defaults to None.

        Raises:
            RuntimeError: If a package cannot be parsed or CRC check fails.

        Returns:
            bytes | bytearray: Remaining data after RT packages have been extracted.
        """
        if len(data) == 0:
            return data
        count = 0xFF - data[0]
        pos = 1
        assert count <= 3, f'unexpected number of RT packages: {count}'

        for _ in range(count):
            assert len(data) >= pos + 8, 'not enough data available to extract frame of RT package'

            frame = pkg.SensorSerialPackage.frombytes(data[pos:])
            assert frame.startByte == 2, f'frame error in RT stream, {frame}'
            assert len(data) >= pos + 8 + frame.payloadSize, 'not enough data available to extract RT package ' \
                f'(data has {len(data)} bytes, package {hex(frame.header)} with size {frame.payloadSize} ' \
                f'expected from {pos+6}..{pos+8+frame.payloadSize})'
            expected_crc = zlib.crc32(data[pos+6:pos+frame.payloadSize+8])
            assert expected_crc == frame.crc32, f'crc mismatch: {expected_crc} != {frame.crc32}, ' \
                                                f'cmd: 0x{frame.header:04X}, size: {frame.payloadSize}, ' \
                                                f'content: 0x{data[pos+6:pos+frame.payloadSize+8].hex()}'

            try:
                cls = pkg.packages[frame.header]
            except KeyError:
                raise RuntimeError(f'unknown class {hex(frame.header)}')

            if frame.payloadSize != (sizeof := ctypes.sizeof(cls)):  # type: ignore
                raise RuntimeError('Unexpected payload size for package: '
                                   f'{frame.payloadSize} != {sizeof}, cmd: 0x{frame.header:04X}, cls: {cls}')

            package = cls.frombytes(data[pos+8:pos+frame.payloadSize+8])

            if isinstance(package, pkg.DataClockRoundtrip) and receiveTimestamp is not None:
                package.hostReceiveTimestamp = receiveTimestamp

            self.rtPackages.append(package)
            pos += frame.payloadSize + 8

        return data[pos:]

    def __iter__(self):
        return self

    def __next__(self):
        if self.rtPackages:
            return self.rtPackages.pop(0)

        while True:
            self._ensureAvailable(8)

            frame = pkg.SensorSerialPackage.frombytes(self.buffer)
            if self.waitForAckStopStreamingAndClearBuffer:
                if frame.startByte != 2:
                    del self.buffer[:1]
                    continue
                elif frame.header != pkg.SensorHeader.ACK_STOP_STREAMING_AND_CLEAR_BUFFER:
                    del self.buffer[:1]
                    continue
                else:
                    self.waitForAckStopStreamingAndClearBuffer = False
            elif self.ignoreInitialGarbage:
                if frame.startByte != 2:
                    del self.buffer[:1]
                    continue
            else:
                assert frame.startByte == 2, f'frame error, {frame}'

            self._ensureAvailable(8 + frame.payloadSize)
            expected_crc = zlib.crc32(self.buffer[6:frame.payloadSize+8])
            if expected_crc != frame.crc32:
                if self.ignoreInitialGarbage:
                    del self.buffer[:1]
                    continue
                else:
                    raise RuntimeError(f'crc mismatch: {expected_crc} != {frame.crc32}, '
                                       f'cmd: 0x{frame.header:04X}, size: {frame.payloadSize}, '
                                       f'content: 0x{self.buffer[6:frame.payloadSize+8].hex()}')

            try:
                cls = pkg.packages[frame.header]
            except KeyError:
                del self.buffer[:frame.payloadSize + 8]
                print(f'unknown class {hex(frame.header)}')
                continue

            if not getattr(cls, 'variable_size', False):
                if frame.payloadSize != (sizeof := ctypes.sizeof(cls)):  # type: ignore
                    raise RuntimeError('Unexpected payload size for package: '
                                       f'{frame.payloadSize} != {sizeof}, cmd: 0x{frame.header:04X}, cls: {cls}')

            package = cls.frombytes(self.buffer[8:frame.payloadSize+8])
            del self.buffer[:frame.payloadSize + 8]
            self.ignoreInitialGarbage = False
            return package

    def _ensureAvailable(self, N):
        if self.f is not None and len(self.buffer) < N:
            self.feed(self.f.read(N - len(self.buffer)))
        if len(self.buffer) < N:
            raise StopIteration


def loadBinaryFile(filename: str | Path) -> dict[str, dict[str, np.ndarray]]:
    """
    Load and parse a binary Capture2Go recording file into NumPy arrays.

    This function reads a binary file (optionally gzip-compressed), unpacks all packages, and organizes them by
    package type. Each package type is converted to a dictionary of NumPy arrays, with one array per field.

    Args:
        filename (str | Path): Path to the binary recording file. Can be a string or pathlib.Path object.
            Files with a `.gz` extension are automatically decompressed.

    Returns:
        Nested dictionary where the outer key is the package class name (e.g., ``DataFullPacked200Hz``) and the value
        is a dictionary mapping field names to NumPy arrays containing all values for that field.
    """
    entries_by_key = defaultdict(list)
    is_gzip = Path(filename).suffix == '.gz'
    if is_gzip:
        import gzip

    with gzip.open(filename, 'rb') if is_gzip else open(filename, 'rb') as f:
        unpacker = Unpacker(f, ignoreInitialGarbage=True)
        for package in unpacker:
            key = package.__class__.__name__
            entries_by_key[key].append(package.parse())

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
