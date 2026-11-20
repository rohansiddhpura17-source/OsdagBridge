import math
import unittest
from osdagbridge.core.bridge_types.plate_girder.validator import BridgeInputValidator
from osdagbridge.core.bridge_types.plate_girder.plategirderbridge import PlateGirderBridge

class NonfiniteBoundaryTests(unittest.TestCase):
    def test_basic_material_and_advanced_reject_nonfinite(self):
        v = BridgeInputValidator()
        fields = [(v.validate_basic_inputs, "geometry.span"),
                  (v.validate_material_inputs, "material.girder.fy"),
                  (v.validate_material_inputs, "material.deck.density"),
                  (v.validate_additional_inputs, "typical_section.deck_thickness")]
        for func, key in fields:
            for value in [float("nan"), float("inf"), -float("inf"), "NaN", "Infinity", "-Infinity", "1e999"]:
                with self.subTest(key=key, value=value):
                    self.assertIsNotNone(func(key, {key: value}))
    def test_set_input_rejects_without_replacing_previous_state(self):
        b = object.__new__(PlateGirderBridge)
        b.input_dict = {"previous": 1}
        for value in [float("nan"), float("inf"), -float("inf"), "nan", "inf", "-inf", "1e999"]:
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "geometry.span.*finite"):
                    b.set_input({"geometry.span": value})
                self.assertEqual(b.input_dict, {"previous": 1})
    def test_nested_nonfinite_rejected(self):
        with self.assertRaisesRegex(ValueError, r"bounds\[1\].*finite"):
            PlateGirderBridge._normalize_input_dict({"bounds": [20, "nan"]})
    def test_valid_values_and_enums_unchanged(self):
        self.assertEqual(PlateGirderBridge._normalize_input_dict(
            {"span": "30.0", "count": "3", "mode": "Optimized", "bounds": ["20","45"], "enabled": True}),
            {"span": 30.0, "count": 3, "mode": "Optimized", "bounds": [20,45], "enabled": True})
if __name__ == "__main__":
    unittest.main(verbosity=2)
