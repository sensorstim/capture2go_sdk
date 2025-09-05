.. SPDX-FileCopyrightText: 2025 SensorStim Neurotechnology GmbH <support@capture2go.com>
..
.. SPDX-License-Identifier: MIT

Examples
========

The `"examples" directory of the repository <https://github.com/sensorstim/capture2go_sdk/tree/main/examples>`_ contains runnable scripts demonstrating typical usage patterns.

Minimal Print Example
---------------------

``minimal_print_example.py`` is a minimal starting point for custom scripts that communicate with a Capture2Go device. The script connects to a Capture2Go device, configures IMU data streaming and prints all received packages.

To keep it as simple as possible, this example does not use command line arguments. By default, the script will try to connect to a device over USB. To change this and connect over BLE, edit the code and change the ``name`` variable.

Key features demonstrated:

* Connecting to a device via USB or BLE.
* Configuring measurement mode and starting data streaming.
* Printing received packages.

Real-Time Streaming
-------------------

``realtime_streaming_example.py`` streams real-time orientations from one or more devices.

Run with help:

.. code-block:: bash

    python examples/realtime_streaming_example.py --help

Example invocation (single device):

.. code-block:: bash

    python examples/realtime_streaming_example.py IMU_ab1234

Key features demonstrated:

* Scanning and connecting to multiple devices (BLE and USB shortcut ``usb``).
* Starting real-time quaternion streaming.
* Converting to Euler angles.

Live Plotting
-------------

``live_plot_example.py`` plots 200 Hz gyroscope, accelerometer, magnetometer and orientation data in real time.

Requirements: ``matplotlib``.

.. code-block:: bash

    pip install matplotlib
    python examples/live_plot_example.py IMU_ab1234

Key features demonstrated:

* Starting full 200 Hz packed streaming.
* Parsing batched data packages.
* Euler angle conversion.
* Running BLE communication in a separate thread for compatibility with non-asyncio libraries such as matplotlib.


Recording and Downloading Data
------------------------------

``recording_example.py`` creates a 200 Hz recording from one or more devices (until Ctrl+C is pressed), then downloads the recording.

Example invocation:

.. code-block:: bash

    python examples/recording_example.py IMU_ab1234 IMU_cd5678

Key features demonstrated:

* Recording to internal storage of the device.
* Synchronizing the clock of multiple devices.
* 200 Hz data recording to the internal storage.
* Downloading files from devices.

.. note::
    The data is written in a format compatible with the `mobile measurement app <https://capture2go.com/app>`__, so the resulting folder can be zipped and imported into the app (and then exported as CSV, for example).

Downloading and Managing Files
------------------------------

``download.py`` downloads files from a Capture2Go device.

The example script also supports listing files, downloading all files, and formatting the storage.

Run with help:

.. code-block:: bash

    python examples/download.py --help

Download a specific file from a device:

.. code-block:: bash

    python examples/download.py IMU_ab1234 my_recording

Delete the file on the device after a successful download:

.. code-block:: bash

    python examples/download.py IMU_ab1234 my_recording --delete

List all files on the device:

.. code-block:: bash

    python examples/download.py IMU_ab1234 --ls

Download all files from the device:

.. code-block:: bash

    python examples/download.py IMU_ab1234 --all

Download all files and delete them from the device after successful transfer:

.. code-block:: bash

    python examples/download.py IMU_ab1234 --all --delete

Format the device storage (erases all files):

.. code-block:: bash

    python examples/download.py IMU_ab1234 --format

Key features demonstrated:

* Downloading files from the device.
* Listing files on the device.
* Deleting files on the device.
* Formatting the device storage.

Converting Recordings to MATLAB
-------------------------------

``convert_to_mat.py`` takes a binary file of sensor data (as created by the recording example or the `mobile measurement app <https://capture2go.com/app>`__), parses it, and writes the data to a MATLAB ``.mat`` file.

Requirements: ``scipy``.

Example invocation:

.. code-block:: bash

    python examples/convert_to_mat.py my_recording.bin

Key features demonstrated:

* Parsing binary sensor data files.
* Exporting to MATLAB ``.mat`` format for further analysis.

.. note::
    The resulting ``.mat`` is a nested struct, with one key per package type. For each value, the data from multiple packages is joined into a single array. Use the processing code from this example as a starting point for further data processing. This approach is useful if you prefer a more low-level alternative to the CSV files created by the `mobile measurement app <https://capture2go.com/app>`__.
