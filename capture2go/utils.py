# SPDX-FileCopyrightText: 2025 SensorStim Neurotechnology GmbH <support@capture2go.com>
#
# SPDX-License-Identifier: MIT

import math
import random

import numpy as np


def qmult(q1: np.ndarray, q2: np.ndarray) -> np.ndarray:
    """
    Multiply two quaternions.

    Args:
        q1 (np.ndarray): First quaternion, shape (4,).
        q2 (np.ndarray): Second quaternion, shape (4,).

    Returns:
        np.ndarray: The product quaternion, shape (4,).
    """
    assert q1.shape == q2.shape == (4,)
    return np.array(
        [
            q1[0]*q2[0] - q1[1]*q2[1] - q1[2]*q2[2] - q1[3]*q2[3],
            q1[0]*q2[1] + q1[1]*q2[0] + q1[2]*q2[3] - q1[3]*q2[2],
            q1[0]*q2[2] - q1[1]*q2[3] + q1[2]*q2[0] + q1[3]*q2[1],
            q1[0]*q2[3] + q1[1]*q2[2] - q1[2]*q2[1] + q1[3]*q2[0],
        ], float)


def rotate(q: np.ndarray, v: np.ndarray) -> np.ndarray:
    """
    Rotate a 3D vector by a quaternion.

    Args:
        q (np.ndarray): Quaternion, shape (4,).
        v (np.ndarray): 3D vector, shape (3,).

    Returns:
        np.ndarray: Rotated 3D vector, shape (3,).
    """
    q = q.copy()
    assert q.shape == (4,)
    assert v.shape == (3,)
    return np.array(
        [
            (1 - 2*q[2]**2 - 2*q[3]**2)*v[0] + 2*v[1]*(q[2]*q[1] - q[0]*q[3]) + 2*v[2]*(q[0]*q[2] + q[3]*q[1]),
            2*v[0]*(q[0]*q[3] + q[2]*q[1]) + v[1]*(1 - 2*q[1]**2 - 2*q[3]**2) + 2*v[2]*(q[2]*q[3] - q[1]*q[0]),
            2*v[0]*(q[3]*q[1] - q[0]*q[2]) + 2*v[1]*(q[0]*q[1] + q[3]*q[2]) + v[2]*(1 - 2*q[1]**2 - 2*q[2]**2),
        ], float)


def rotateinv(q: np.ndarray, v: np.ndarray) -> np.ndarray:
    """
    Rotate a 3D vector by the inverse of a quaternion.

    Args:
        q (np.ndarray): Quaternion, shape (4,).
        v (np.ndarray): 3D vector, shape (3,).

    Returns:
        np.ndarray: Rotated 3D vector, shape (3,).
    """
    q = q.copy()
    assert q.shape == (4,)
    assert v.shape == (3,)
    return np.array(
        [
            (1 - 2*q[2]**2 - 2*q[3]**2)*v[0] + 2*v[1]*(q[2]*q[1] + q[0]*q[3]) + 2*v[2]*(-q[0]*q[2] + q[3]*q[1]),
            2*v[0]*(-q[0]*q[3] + q[2]*q[1]) + v[1]*(1 - 2*q[1]**2 - 2*q[3]**2) + 2*v[2]*(q[2]*q[3] + q[1]*q[0]),
            2*v[0]*(q[3]*q[1] + q[0]*q[2]) + 2*v[1]*(-q[0]*q[1] + q[3]*q[2]) + v[2]*(1 - 2*q[1]**2 - 2*q[2]**2),
        ], float)


def quatFromGyr(gyr: np.ndarray, rate: float) -> np.ndarray:
    """
    Create an axis-angle quaternion from gyroscope measurements (not integrated).

    Args:
        gyr (np.ndarray): Angular velocity vector(s), shape (..., 3).
        rate (float): Sampling rate (Hz).

    Returns:
        np.ndarray: Quaternion(s), shape (..., 4).
    """
    norm = np.linalg.norm(gyr, axis=-1)
    angle = norm / rate
    zeroaxis = angle < np.finfo(float).eps
    norm[zeroaxis] = 1  # angle and gyr will be zero
    q = np.zeros(gyr.shape[:-1] + (4,), float)
    q[..., 0] = np.cos(angle / 2)
    q[..., 1] = np.sin(angle / 2) * gyr[..., 0] / norm
    q[..., 2] = np.sin(angle / 2) * gyr[..., 1] / norm
    q[..., 3] = np.sin(angle / 2) * gyr[..., 2] / norm
    return q


def addHeading(q: np.ndarray, delta: float) -> np.ndarray:
    """
    Add a heading (yaw) rotation to a quaternion.

    Args:
        q (np.ndarray): Quaternion, shape (4,).
        delta (float): Heading angle in radians.

    Returns:
        np.ndarray: Resulting quaternion, shape (4,).
    """
    return qmult(np.array([np.cos(delta/2), 0, 0, np.sin(delta/2)], float), q)


def eulerAngles(q: np.ndarray, axes: str = 'zyx', intrinsic: bool = True) -> np.ndarray:
    """
    Convert a quaternion to Euler angles.

    Args:
        q (np.ndarray): Quaternion, shape (4,).
        axes (str, optional): Rotation sequence, e.g., 'zyx'. Defaults to 'zyx'.
        intrinsic (bool, optional): If True, use intrinsic rotations. Defaults to True.

    Returns:
        np.ndarray: Euler angles in radians, order depends on axes and intrinsic.

    Raises:
        ValueError: If the axes sequence is invalid.
    """
    axisIdentifiers = {
        1: 1, '1': 1, 'x': 1, 'X': 1, 'i': 1,
        2: 2, '2': 2, 'y': 2, 'Y': 2, 'j': 2,
        3: 3, '3': 3, 'z': 3, 'Z': 3, 'k': 3,
    }
    if len(axes) != 3:
        raise ValueError('invalid Euler rotation sequence')

    if intrinsic:
        axes = axes[::-1]
    try:
        a = axisIdentifiers[axes[0]]
        b = axisIdentifiers[axes[1]]
        c = axisIdentifiers[axes[2]]
        d = 'invalid'
        if a == c:
            d = (set([1, 2, 3]) - set([a, b])).pop()
    except KeyError:
        raise ValueError('invalid Euler rotation sequence')
    if b == a or b == c:
        raise ValueError('invalid Euler rotation sequence')

    # sign factor depending on the axes order
    if b == (a % 3) + 1:  # cyclic order
        s = 1
    else:  # anti-cyclic order
        s = -1

    if a == c:  # proper Euler angles
        angle1 = np.arctan2(q[a] * q[b] - s * q[d] * q[0],
                            q[b] * q[0] + s * q[a] * q[d])
        angle2 = np.arccos(np.clip(q[0] ** 2 + q[a] ** 2 - q[b] ** 2 - q[d] ** 2, -1, 1))
        angle3 = np.arctan2(q[a] * q[b] + s * q[d] * q[0],
                            q[b] * q[0] - s * q[a] * q[d])
    else:  # Tait-Bryan
        angle1 = np.arctan2(2 * (q[a] * q[0] + s * q[b] * q[c]),
                            q[0] ** 2 - q[a] ** 2 - q[b] ** 2 + q[c] ** 2)
        angle2 = np.arcsin(np.clip(2 * (q[b] * q[0] - s * q[a] * q[c]), -1, 1))
        angle3 = np.arctan2(2 * (s * q[a] * q[b] + q[c] * q[0]),
                            q[0] ** 2 + q[a] ** 2 - q[b] ** 2 - q[c] ** 2)

    if intrinsic:
        return np.array((angle3, angle2, angle1), float)
    else:
        return np.array((angle1, angle2, angle3), float)


def decodeQuat(quat: int) -> tuple[np.ndarray, bool, bool]:
    """
    Decode a compressed 64-bit integer quaternion to a 4-element array.

    Args:
        quat (int): 64-bit integer encoding a quaternion.

    Returns:
        tuple[np.ndarray, bool, bool]:
            - np.ndarray: Decoded quaternion, shape (4,).
            - bool: outRest flag.
            - bool: outMagDist flag.
    """
    out = np.empty(4)
    outRest = bool((quat >> 62) & 1)
    outMagDist = bool((quat >> 63) & 1)
    ax = (quat >> 60) & 3
    sqSum = 0
    for i in range(3, 0, -1):
        val = float(quat & 0xFFFFF) / float(0xFFFFF / math.sqrt(2)) - 1/math.sqrt(2)
        sqSum += val**2
        out[(ax+i) % 4] = val
        quat >>= 20
    if sqSum > 1:  # Note: This should never ever happen. Do not remove this warning!
        print(f'warning: invalid quat {quat} with sqSum {sqSum}')
        out.fill(np.nan)
    else:
        out[ax] = math.sqrt(1-sqSum)
    return out, outRest, outMagDist


def generateSyncId() -> int:
    """
    Generate a random 64-bit synchronization ID.

    When setting the measurement mode, the same ID should be used for all devices that should be synchronized. Whenever
    the set of sensors changes, generate a new ID.

    Returns:
        int: A random 64-bit integer.
    """
    return random.getrandbits(64)
