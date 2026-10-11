"""Experimental SG05LP3 codecs and observation. No live write implementation.

Not imported by the integration entry point. This module has no HA dependency,
does not create a connection and never sends FC06/FC16 commands.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_DOWN
from typing import Protocol

MODEL = "SUN-15K-SG05LP3-EU-SM2"
FIRMWARE = ("1001-C05F", "2107-1184-1809", "D20A")
# Deye's firmware-specific email resolves the conflicting document definitions.
# Command values only: these are not a decoder for observed operating status.
# The reported firmware above has not been reverified by this offline module.
MODE_ENTRY_VALUE = 0
MODE_EXIT_VALUE = 1
MODE_SEMANTICS_EVIDENCE = "VENDOR_CONFIRMED_NOT_LIVE_VERIFIED"
READ_BLOCKS = ((1100, 2), (1104, 12))
READ_ADDRESSES = frozenset((1100, 1101, *range(1104, 1116)))
UNRESOLVED = (
    "1100 vendor-confirmed command semantics not physically tested on this firmware",
    "1101 refresh operation and timing not fully specified",
    "LSW-5 Remote Mode writes and watchdog cadence not verified",
    "TOU watchdog fallback not physically verified on this firmware",
)


class SafetyError(ValueError):
    """Invalid or unsafe input; do not silently substitute defaults."""


class WriteBlocked(SafetyError):
    """All live writes are blocked in this implementation."""


def _integer(value: object, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise SafetyError(f"Expected integer in [{minimum}, {maximum}]")
    return value


def _decimal(value: object) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float, str, Decimal)):
        raise SafetyError("Expected a finite number")
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise SafetyError("Expected a finite number") from exc
    if not result.is_finite():
        raise SafetyError("Expected a finite number")
    return result


def encode_i16(value: int) -> int:
    """Two's-complement wire representation for unsigned HA service inputs."""
    return _integer(value, -32768, 32767) & 0xFFFF


def decode_i16(value: int) -> int:
    value = _integer(value, 0, 65535)
    return value - 65536 if value & 0x8000 else value


def power_to_raw(power_w: object, rated_power_w: object = 15000) -> int:
    """1109: 0.1% of rated power; + discharge, - charge; round toward zero."""
    power, rated = _decimal(power_w), _decimal(rated_power_w)
    if rated <= 0 or abs(power) > rated * Decimal("1.2"):
        raise SafetyError("Power outside the documented +/-120% range")
    return int((power / rated * 1000).to_integral_value(rounding=ROUND_DOWN))


def raw_to_power(raw: int, rated_power_w: object = 15000) -> Decimal:
    raw = _integer(raw, -1200, 1200)
    rated = _decimal(rated_power_w)
    if rated <= 0:
        raise SafetyError("Rated power must be positive")
    return Decimal(raw) * rated / 1000


def soc_to_raw(soc_percent: object) -> int:
    soc = _decimal(soc_percent)
    if not 0 <= soc <= 100:
        raise SafetyError("SOC outside [0, 100]%")
    return int((soc * 10).to_integral_value(rounding=ROUND_DOWN))


def validate_watchdog(seconds: int) -> int:
    """Never allow the documented watchdog-off sentinel 65535."""
    return _integer(seconds, 10, 18000)


@dataclass(frozen=True)
class PowerPreview:
    requested_w: Decimal
    quantized_w: Decimal
    intent: str
    register: int
    raw_signed: int
    wire_unsigned: int
    function_code: int = 0x10
    executable: bool = False
    blockers: tuple[str, ...] = UNRESOLVED


def preview_power(power_w: object, rated_power_w: object = 15000) -> PowerPreview:
    """Arithmetic preview only: no service payload, mode-entry or send operation."""
    raw = power_to_raw(power_w, rated_power_w)
    return PowerPreview(
        requested_w=_decimal(power_w),
        quantized_w=raw_to_power(raw, rated_power_w),
        intent="DISCHARGE" if raw > 0 else "CHARGE" if raw < 0 else "HOLD",
        register=1109,
        raw_signed=raw,
        wire_unsigned=encode_i16(raw),
    )


@dataclass(frozen=True)
class DecodedSnapshot:
    """Current response only. No cached previous response can satisfy this read."""
    received_at: datetime
    raw: tuple[tuple[int, int], ...]
    power_request_percent: Decimal
    target_soc_percent: Decimal
    watchdog_off: bool
    # Evidence status, not an assertion that Remote Mode is active/inactive.
    mode_interpretation: str = MODE_SEMANTICS_EVIDENCE
    # Even complete readback proves neither physical response nor safe fallback.
    live_control_verified: bool = False


def decode_snapshot(values: dict[int | str, int], received_at: datetime) -> DecodedSnapshot:
    if received_at.tzinfo is None or received_at.utcoffset() is None:
        raise SafetyError("Timestamp must include a timezone")
    normalized: dict[int, int] = {}
    for key, value in values.items():
        if type(key) is int:
            address = key
        elif isinstance(key, str) and key.isascii() and key.isdecimal():
            address = int(key)
        else:
            raise SafetyError("Register keys must be decimal addresses")
        if address not in READ_ADDRESSES or address in normalized:
            raise SafetyError("Unexpected or duplicate register")
        normalized[address] = _integer(value, 0, 65535)
    if set(normalized) != READ_ADDRESSES:
        raise SafetyError("Incomplete response")
    power = _integer(decode_i16(normalized[1109]), -1200, 1200)
    soc = _integer(normalized[1110], 0, 1000)
    watchdog = normalized[1101]
    if watchdog != 65535:
        # A countdown may legitimately reach 0, unlike a configured timeout.
        _integer(watchdog, 0, 18000)
    return DecodedSnapshot(
        received_at=received_at,
        raw=tuple(sorted(normalized.items())),
        power_request_percent=Decimal(power) / 10,
        target_soc_percent=Decimal(soc) / 10,
        watchdog_off=watchdog == 65535,
    )


class ExistingDevice(Protocol):
    """Use the existing HA Solarman device; never create a competing connection."""
    async def execute(self, code: int, address: int, **kwargs: object) -> object: ...


class ReadOnlyProbe:
    """Explicitly invoked probe; no scheduler, retry storm, writes or new socket."""

    def __init__(self, existing_device: ExistingDevice):
        self._device = existing_device

    async def read(self) -> DecodedSnapshot:
        values: dict[int, int] = {}
        for address, count in READ_BLOCKS:
            response = await self._device.execute(0x03, address, count=count)
            if not isinstance(response, (list, tuple)) or len(response) != count:
                raise SafetyError("Missing or malformed FC03 response")
            for offset, value in enumerate(response):
                values[address + offset] = _integer(value, 0, 65535)
        return decode_snapshot(values, datetime.now(timezone.utc))

    async def write(self, *args: object, **kwargs: object) -> None:
        # Deliberately unconditional: no flag/config/helper can unlock writes.
        raise WriteBlocked("Live writes not implemented; separate supervised stage required")
