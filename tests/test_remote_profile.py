from pathlib import Path
import unittest
import yaml


class ProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).resolve().parents[1] / "experimental/sg05lp3/remote_observe.yaml"
        cls.profile = yaml.safe_load(path.read_text())
        cls.items = cls.profile["parameters"][0]["items"]
        cls.by_address = {item["registers"][0]: item for item in cls.items}

    def test_no_writable_entities(self):
        self.assertEqual(self.profile["default"]["code"], 3)
        for item in self.items:
            self.assertEqual(item["platform"], "sensor")
            self.assertNotIn("configurable", item)
            self.assertNotIn("code", item)

    def test_unique_explicit_addresses(self):
        addresses = [item["registers"][0] for item in self.items]
        self.assertEqual(len(addresses), 14)
        self.assertEqual(len(set(addresses)), 14)
        self.assertEqual(set(addresses), {1100, 1101, *range(1104, 1116)})

    def test_voltage_current_soc_units_not_pr_mapping(self):
        for address, unit in ((1107, "V"), (1108, "A"), (1110, "%")):
            self.assertEqual(self.by_address[address]["uom"], unit)
            self.assertEqual(self.by_address[address]["scale"], 0.1)
        self.assertNotIn("lookup", self.by_address[1100])

    def test_signed_power_definitions(self):
        for address in (1109, 1111, 1112, 1113, 1114):
            self.assertEqual(self.by_address[address]["rule"], 2)
            self.assertEqual(self.by_address[address]["scale"], 0.1)
            self.assertEqual(self.by_address[address]["uom"], "%")
