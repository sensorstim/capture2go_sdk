.. SPDX-FileCopyrightText: 2025 SensorStim Neurotechnology GmbH <support@capture2go.com>
..
.. SPDX-License-Identifier: MIT

Main API Reference
==================

This page documents the main classes and functions available in the top-level ``capture2go`` namespace.

.. currentmodule:: capture2go

Device Classes
--------------

.. autoclass:: AbstractDevice
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: BleDevice
   :members:
   :undoc-members:
   :show-inheritance:
   :exclude-members: send, connect, disconnect

.. autoclass:: UsbDevice
   :members:
   :undoc-members:
   :show-inheritance:
   :exclude-members: send, connect, disconnect

.. autoclass:: FilePlaybackDevice
   :members:
   :undoc-members:
   :show-inheritance:
   :exclude-members: send, connect, disconnect, init, poll, apoll

Scanning and Connecting
-----------------------

.. autoclass:: BleScanner
   :members:
   :undoc-members:
   :show-inheritance:

.. autofunction:: connect

Parsing
-------

.. autoclass:: Unpacker
   :members:
   :undoc-members:
   :show-inheritance:

.. autofunction:: loadBinaryFile

Exceptions
----------

.. autoclass:: DeviceIsRecording

.. autoclass:: DeviceIsStreaming

Type Aliases
------------

.. autodata:: DeviceState
.. autodata:: StateListener
.. autodata:: DataListener
.. autodata:: PackageListener
