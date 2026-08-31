import unittest

from rac_generator.logic import (
    build_dependency_levels,
    build_device_description,
    generate_bacnet_instance,
    generate_equipment_name,
    generate_fqr,
    infer_heat_flags,
    recalculate_record,
    split_served_by,
    validate_records_for_sct,
)
from rac_generator.models import DeviceRecord


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

    def test_split_served_by(self):
        self.assertEqual(split_served_by("AHU-1 && AHU-2"), ["AHU-1", "AHU-2"])

    def test_dependency_levels_are_top_down(self):
        vav = DeviceRecord(equipment_name="VAV-1", served_by="AHU-1")
        plant = DeviceRecord(equipment_name="PLANT-1")
        ahu = DeviceRecord(equipment_name="AHU-1", served_by="PLANT-1")
        levels = build_dependency_levels([vav, plant, ahu])
        self.assertEqual([[r.equipment_name for r in level] for level in levels], [["PLANT-1"], ["AHU-1"], ["VAV-1"]])

    def test_preexisting_parent_does_not_add_level(self):
        vav = DeviceRecord(equipment_name="VAV-1", served_by="AHU-EXISTING")
        levels = build_dependency_levels([vav], "AHU-EXISTING")
        self.assertEqual([[r.equipment_name for r in level] for level in levels], [["VAV-1"]])

    def test_cycle_is_rejected(self):
        a = DeviceRecord(equipment_name="A", served_by="B")
        b = DeviceRecord(equipment_name="B", served_by="A")
        with self.assertRaises(ValueError):
            build_dependency_levels([a, b])

    def test_device_name_fqr_is_independent_of_instance(self):
        record = DeviceRecord(device_name="MR-VAV-01")
        recalculate_record(record, {"Generic": {}}, generate_instance=False, fqr_mode="Device Name (SCT recommended)")
        self.assertIsNone(record.instance)
        self.assertEqual(record.fqr, "MR-VAV-01")

    def test_preflight_catches_missing_served_by_parent(self):
        record = DeviceRecord(
            site_hierarchy="Site/Bldg/Floor",
            leaf_space="101",
            device_name="MR-VAV-01",
            fqr="MR-VAV-01",
            equipment_name="VAV-01",
            served_by="AHU-DOES-NOT-EXIST",
            engine_name="SNE01",
            trunk_name="FC-1",
            controller_template="VAV",
            mac_address=4,
        )
        errors, _warnings = validate_records_for_sct([record])
        self.assertTrue(any("neither generated" in error for error in errors))

    def test_preflight_catches_bad_mstp_mac(self):
        record = DeviceRecord(
            site_hierarchy="Site/Bldg/Floor",
            leaf_space="101",
            device_name="MR-VAV-01",
            fqr="MR-VAV-01",
            equipment_name="VAV-01",
            engine_name="SNE01",
            trunk_name="FC-1",
            controller_template="VAV",
            mac_address=2,
        )
        errors, _warnings = validate_records_for_sct([record])
        self.assertTrue(any("between 4 and 127" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
