[![Read the Docs](https://img.shields.io/readthedocs/capture2go)](https://capture2go.readthedocs.io/)
[![PyPI version](https://img.shields.io/pypi/v/capture2go)](https://pypi.org/project/capture2go/)
[![Python versions](https://img.shields.io/pypi/pyversions/capture2go)](https://pypi.org/project/capture2go/)
[![License: MIT](https://img.shields.io/github/license/sensorstim/capture2go_sdk)](https://github.com/sensorstim/capture2go_sdk/blob/main/LICENSES/MIT.txt)

# Capture2Go Python SDK
<!--
SPDX-FileCopyrightText: 2025 SensorStim Neurotechnology GmbH <support@capture2go.com>

SPDX-License-Identifier: MIT
-->

## Introduction

[Capture2Go](https://capture2go.com) is the wearable sensor platform by [SensorStim Neurotechnology GmbH](https://sensorstim.de). The main product is the Capture2Go IMU, a wireless motion sensor with advanced on-chip sensor fusion.

This Python SDK is meant for power users who want to integrate Capture2Go devices into their own application. It supports scanning for sensors over BLE, connecting to sensors over BLE and USB, and communicating with the sensors to record and stream sensor data.

The SDK is based on the [bleak](https://github.com/hbldh/bleak) Bluetooth library, uses [asyncio](https://docs.python.org/3/library/asyncio.html), and works on Linux, macOS, and Windows. Note that the performance depends on the Bluetooth hardware and the Bluetooth stack of the operating system.

If you want to integrate Capture2Go devices in your own application without using Python, please check the documentation of the communication protocol (see below).

If you only want to use the sensors to record data in a simple and efficient way, please take a look at our [mobile measurement app](https://capture2go.com/app).

## Installation

The `capture2go` package can easily be installed from [PyPI](https://pypi.org/project/capture2go/) via `pip`:

```sh
pip install capture2go
```

To install the package from source, clone this repository and execute the following command in the root directory of this repository:

```sh
pip install .
```

In general, it is recommended to use a [virtual environment](https://docs.python.org/3/library/venv.html). Depending on your setup, you might need to use `pip` instead of `pip3` and/or use the `--user` flag. When developing this SDK itself, use the `-e` flag to install the package in editable mode.

## Example Code

The folder `examples/` contains example code that shows how to use the SDK. To understand what the code is doing, run the scripts with the `--help` flag and look at the source code.

## Documentation

The documentation of the SDK is available on https://capture2go.readthedocs.io/.

## Documentation of the Communication Protocol

The documentation of the communication protocol can be found in the documentation and in [protocol/Capture2Go_Communication_Protocol.md](protocol/Capture2Go_Communication_Protocol.md).

## License

The Capture2Go SDK is licensed under the terms of the [MIT license](https://spdx.org/licenses/MIT.html).

## Contact

support@capture2go.com
