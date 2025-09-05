.. SPDX-FileCopyrightText: 2025 SensorStim Neurotechnology GmbH <support@capture2go.com>
..
.. SPDX-License-Identifier: MIT

Getting Started
===============

Introduction
------------

`Capture2Go <https://capture2go.com>`__ is the wearable sensor platform by `SensorStim Neurotechnology GmbH <https://sensorstim.de>`__. The main product is the Capture2Go IMU, a wireless motion sensor with advanced on-chip sensor fusion.

This Python SDK is meant for advanced users who want to integrate Capture2Go devices into their own application. It supports scanning for devices over BLE, connecting to devices over BLE and USB, and communicating with the devices to record and stream sensor data.

The SDK is based on the `bleak <https://github.com/hbldh/bleak>`__ Bluetooth library, uses `asyncio <https://docs.python.org/3/library/asyncio.html>`__, and works on Linux, macOS, and Windows. Note that the performance depends on the Bluetooth hardware and the Bluetooth stack of the operating system.

If you want to integrate Capture2Go devices in your own application using a programming language other than Python, please read the :doc:`documentation of the communication protocol <protocol>`.

If you only want to use the sensors to record data in a simple and efficient way, please take a look at our `mobile measurement app <https://capture2go.com/app>`__.

Installation
------------

The ``capture2go`` package can easily be installed from `PyPI <https://pypi.org/project/capture2go/>`__ via ``pip``:

.. code-block:: bash

    pip install capture2go

To install the package from source, clone this repository and execute ``pip install .`` in the root directory of this repository:

.. code-block:: bash

    git clone https://github.com/sensorstim/capture2go.git
    cd capture2go
    pip install .

In general, it is recommended to use a `virtual environment <https://docs.python.org/3/library/venv.html>`__. Depending on your setup, you might need to use ``pip3`` instead of ``pip`` and/or use the ``--user`` flag. When developing this SDK itself, use the ``-e`` flag to install the package in editable mode. Run ``pip install '.[docs]'`` if you also want to install the dependencies needed to build the Sphinx documentation locally.


Minimal Usage Example
---------------------

The snippet below scans for a specific device, connects to it over BLE, starts real-time quaternion streaming, and prints orientation data.

.. code-block:: python

    import asyncio
    import capture2go as c2g


    async def main():
        devices = await c2g.connect(['IMU_ab1234'])  # Replace with your device ID.
        imu = devices[0]
        await imu.init(setTime=True)
        await imu.send(c2g.pkg.CmdStartRealTimeStreaming(
            mode=c2g.pkg.RealTimeDataMode.REAL_TIME_DATA_QUAT,
            rateLimit=0
        ))
        async for package in imu:
            if isinstance(package, c2g.pkg.DataQuatFixedRt):
                parsed = package.parse()
                print(parsed['timestamp'], parsed['quat'])

    asyncio.run(main())

For more complex examples, please see the :doc:`examples page <examples>`.

Recording, Streaming, Real-Time Streaming
-----------------------------------------

The Capture2Go IMU supports three primary data acquisition modes. The choice of mode depends on your application's requirements regarding latency, sampling rate regularity, and data integrity.

**Recording**

In recording mode, sensor samples are generated at a fixed regular sampling rate and stored directly on the device's internal flash memory. The recorded data can be downloaded after the recording session, during the session, or in a combination of both. This mode guarantees data capture without gaps, even if the Bluetooth connection is interrupted. However, latency is higher than in other modes, even when downloading and parsing data during an ongoing recording. The recording mode is ideal for experiments where data integrity is critical and analysis is performed later. This is the mode used by the mobile app.

**Streaming**

In streaming mode, the device generates samples at a fixed regular sampling rate and stores them in a transmission buffer on the device. Data from this buffer is sent over BLE to the host. This mode offers medium latency, which may increase if wireless communication is disturbed. Data is typically gap-free unless the transmission buffer overflows. The streaming mode is suitable for applications that require a regular sampling rate and can tolerate moderate latency, such as real-time algorithmic processing.

**Real-Time Streaming**

In real-time streaming mode, samples are generated and transmitted whenever a BLE packet is sent. The actual timing depends on the operating system and Bluetooth hardware. This mode provides minimal latency but the data has an irregular sampling rate. The real-time streaming mode is best suited for real-time visualization and feedback applications, where low latency is more important than a fixed sampling rate.

**Summary Table**

.. list-table::
     :header-rows: 1

     * - Mode
       - Sampling
       - Latency
       - Data Integrity
       - Typical Use Case
     * - Recording
       - Fixed
       - High
       - No gaps
       - Experiments, batch analysis
     * - Streaming
       - Fixed
       - Medium
       - Gap-free unless buffer overflows
       - Real-time processing
     * - Real-Time Streaming
       - Irregular
       - Low
       - May have gaps
       - Visualization, feedback, low-latency control


.. note::

  The device supports combining the recording mode with real-time streaming, or combining the streaming mode with real-time streaming. For example, the current orientation can be transmitted with real-time streaming to achieve low-latency feedback, while the full data is sent using streaming mode at a fixed sampling rate and without gaps -- ideal for further processing steps.

**Data Output Modes**

The IMU can provide different types of measured data, depending on the selected mode:

- **full**: Includes gyroscope data, accelerometer data, magnetometer data, and both 6D and 9D orientation estimates.
- **full 6D**: Same as **full**, but excludes magnetometer data.
- **quat**: Provides only 6D and 9D orientation estimates.

For more details on measurement modes and data output modes, see the :doc:`protocol documentation <protocol>`.
