import unittest

from rac_generator.logic import (
    build_device_description,
    generate_bacnet_instance,
    generate_equipment_name,
    generate_fqr,
    infer_heat_flags,
)


class LogicTests(unittest.TestCase):
    def test_equipment_name(self):
        self.assertEqual(generate_equipment_name("VAV", "-", 1, 2), "VAV-01")
        self.assertEqual(generate_equipment_name("AHU", "", 3, 1), "AHU3")

    def test_instance_formula(self):
        self.assertEqual(generate_bacnet_instance("S3-SNE03", "FC-1", 6, None), 1003106)

    def test_fqr_formula(self):
        self.assertEqual(generate_fqr("S3-SNE03", "FC-1", "M4-CVM03050-0", 1003106), "031CV006")

    def test_description(self):
        self.assertEqual(
            build_device_description("MR-VAV-01", "Public Vestibule", "150A"),
            "MR-VAV-01 - Public Vestibule Rm 150A",
        )

    def test_heat_flags(self):
        self.assertEqual(infer_heat_flags("VAV-CLG"), (False, False))
        self.assertEqual(infer_heat_flags("VAV-RH"), (True, False))
        self.assertEqual(infer_heat_flags("VAV-RAD"), (True, True))


if __name__ == "__main__":
    unittest.main()
