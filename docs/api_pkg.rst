.. SPDX-FileCopyrightText: 2025 SensorStim Neurotechnology GmbH <support@capture2go.com>
..
.. SPDX-License-Identifier: MIT

Package Definitions (c2g.pkg)
===============================

Introduction
------------

This page documents the ``capture2go.pkg`` submodule, which contains protocol and data structure definitions.

.. note::

   The defined enums and classes correspond directly to what is described in the :doc:`protocol documentation <protocol>`.

   The main thing to know is that the package objects have a parse function that turns the object into a dict of numbers and numpy arrays, with some useful processing like converting from fixed point numbers to floats in physical units.

All Members
-----------

.. autodata:: capture2go.pkg.packages
   :annotation: = dict[SensorHeader, type[AbstractPackage]]

.. autoclass:: capture2go.pkg.SensorHeader
   :members:
   :undoc-members:

.. autoclass:: capture2go.pkg.ErrorCode
   :members:
   :undoc-members:

.. autoclass:: capture2go.pkg.SensorState
   :members:
   :undoc-members:

.. autoclass:: capture2go.pkg.ConnectionState
   :members:
   :undoc-members:

.. autoclass:: capture2go.pkg.SamplingMode
   :members:
   :undoc-members:

.. autoclass:: capture2go.pkg.SyncMode
   :members:
   :undoc-members:

.. autoclass:: capture2go.pkg.ProcessExtensionMode
   :members:
   :undoc-members:

.. autoclass:: capture2go.pkg.CalibrationDataMode
   :members:
   :undoc-members:

.. autoclass:: capture2go.pkg.RealTimeDataMode
   :members:
   :undoc-members:

.. automodule:: capture2go.pkg
   :members:
   :show-inheritance:
   :exclude-members: packages, SensorHeader, ErrorCode, SensorState, ConnectionState, SamplingMode, SyncMode, ProcessExtensionMode, CalibrationDataMode, RealTimeDataMode
