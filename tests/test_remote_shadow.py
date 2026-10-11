import importlib.util
from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest

path = Path(__file__).resolve().parents[1] / "custom_components/solarman/remote_shadow.py"
spec = importlib.util.spec_from_file_location("remote_shadow_test", path)
remote = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = remote
spec.loader.exec_module(remote)


def snapshot():
    return {address: 0 for address in remote.READ_ADDRESSES} | {1101: 60, 1110: 500}


class CodecTests(unittest.TestCase):
    def test_all_i16_roundtrip(self):
        for raw in range(-32768, 32768):
            self.assertEqual(remote.decode_i16(remote.encode_i16(raw)), raw)

    def test_documented_15kw_examples(self):
        self.assertEqual(remote.power_to_raw(-300), -20)
        self.assertEqual(remote.encode_i16(-20), 65516)
        self.assertEqual(remote.power_to_raw(300), 20)
        self.assertEqual(remote.raw_to_power(-20), -300)

    def test_entity_percent_is_not_raw(self):
        self.assertEqual(remote.power_to_raw(-3000, 20000), -150)
        data = snapshot() | {1109: remote.encode_i16(-150)}
        self.assertEqual(remote.decode_snapshot(data, datetime.now(timezone.utc))
                         .power_request_percent, -15)

    def test_rounding_does_not_increase_magnitude(self):
        self.assertEqual(remote.power_to_raw(299), 19)
        self.assertEqual(remote.power_to_raw(-299), -19)
        self.assertEqual(remote.power_to_raw(-14), 0)

    def test_bad_power_inputs(self):
        for value in ("nan", "inf", "-inf", None, True, "oops", 18001, -18001):
            with self.subTest(value=value), self.assertRaises(remote.SafetyError):
                remote.power_to_raw(value)

    def test_invalid_rating(self):
        for rating in (0, -1, True, "nan"):
            with self.subTest(rating=rating), self.assertRaises(remote.SafetyError):
                remote.power_to_raw(0, rating)

    def test_unsigned_signed_bounds(self):
        for value in (-1, 65536, True, 1.2):
            with self.subTest(value=value), self.assertRaises(remote.SafetyError):
                remote.decode_i16(value)
        for value in (-32769, 32768, False):
            with self.subTest(value=value), self.assertRaises(remote.SafetyError):
                remote.encode_i16(value)

    def test_soc_scale(self):
        self.assertEqual(remote.soc_to_raw("54.3"), 543)
        self.assertEqual(remote.soc_to_raw(100), 1000)
        for soc in (-1, 101, "nan", True):
            with self.subTest(soc=soc), self.assertRaises(remote.SafetyError):
                remote.soc_to_raw(soc)

    def test_watchdog_disabled_is_rejected(self):
        for timeout in (0, 9, 18001, 65535, True):
            with self.subTest(timeout=timeout), self.assertRaises(remote.SafetyError):
                remote.validate_watchdog(timeout)
        self.assertEqual(remote.validate_watchdog(10), 10)
        self.assertEqual(remote.validate_watchdog(18000), 18000)

    def test_every_preview_non_executable(self):
        for power in (0, -300, 300, 18000):
            preview = remote.preview_power(power)
            self.assertFalse(preview.executable)
            self.assertEqual(preview.function_code, 16)
            self.assertEqual(preview.register, 1109)
            self.assertGreaterEqual(len(preview.blockers), 4)
        self.assertEqual(remote.preview_power(1).intent, "HOLD")

    def test_string_keys_and_unknown_mode_remain_raw(self):
        data = {str(k): v for k, v in snapshot().items()}
        result = remote.decode_snapshot(data, datetime.now(timezone.utc))
        self.assertEqual(result.target_soc_percent, 50)
        self.assertEqual(result.mode_interpretation, "UNRESOLVED")
        self.assertFalse(result.live_control_verified)

    def test_incomplete_duplicate_or_extra_snapshot(self):
        cases = [snapshot() | {1102: 0}, snapshot() | {"1100": 0},
                 {k: v for k, v in snapshot().items() if k != 1110}]
        for data in cases:
            with self.subTest(data=data), self.assertRaises(remote.SafetyError):
                remote.decode_snapshot(data, datetime.now(timezone.utc))

    def test_bad_response_values(self):
        for address, value in ((1109, 1201), (1110, 1001), (1100, -1),
                               (1101, 18001), (1104, True), (1105, "2")):
            with self.subTest(address=address), self.assertRaises(remote.SafetyError):
                remote.decode_snapshot(snapshot() | {address: value},
                                       datetime.now(timezone.utc))

    def test_no_naive_timestamp(self):
        with self.assertRaises(remote.SafetyError):
            remote.decode_snapshot(snapshot(), datetime.now())

    def test_watchdog_read_can_be_off_or_zero(self):
        now = datetime.now(timezone.utc)
        self.assertTrue(remote.decode_snapshot(snapshot() | {1101: 65535}, now).watchdog_off)
        self.assertFalse(remote.decode_snapshot(snapshot() | {1101: 0}, now).watchdog_off)


class FakeDevice:
    def __init__(self):
        self.calls = []
        self.malformed = False

    async def execute(self, code, address, **kwargs):
        self.calls.append((code, address, kwargs))
        if self.malformed:
            return None
        return [snapshot()[r] for r in range(address, address + kwargs["count"])]


class ProbeTests(unittest.IsolatedAsyncioTestCase):
    async def test_only_fc03_and_allowlisted_ranges(self):
        device = FakeDevice()
        result = await remote.ReadOnlyProbe(device).read()
        self.assertEqual(device.calls, [(3, 1100, {"count": 2}), (3, 1104, {"count": 12})])
        self.assertEqual(set(dict(result.raw)), remote.READ_ADDRESSES)
        self.assertFalse(result.live_control_verified)

    async def test_write_blocked_including_zero(self):
        device = FakeDevice()
        for power in (0, 300, -300):
            with self.subTest(power=power), self.assertRaises(remote.WriteBlocked):
                await remote.ReadOnlyProbe(device).write(power)
        self.assertEqual(device.calls, [])

    async def test_previous_success_cannot_satisfy_next_failure(self):
        device = FakeDevice()
        probe = remote.ReadOnlyProbe(device)
        await probe.read()
        device.malformed = True
        with self.assertRaises(remote.SafetyError):
            await probe.read()

    async def test_transport_error_propagates(self):
        class Failed:
            async def execute(self, *args, **kwargs):
                raise TimeoutError("test transport timeout")
        with self.assertRaises(TimeoutError):
            await remote.ReadOnlyProbe(Failed()).read()


if __name__ == "__main__":
    unittest.main()
