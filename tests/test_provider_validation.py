import json
import unittest
from pathlib import Path
from types import SimpleNamespace

from astrology.provider_validation import (
    equal_house_number,
    validate_provider_chart,
    whole_sign_house_number,
)


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "provider_reference.json"


def _namespace(value):
    if isinstance(value, dict):
        return SimpleNamespace(**{key: _namespace(item) for key, item in value.items()})
    if isinstance(value, list):
        return [_namespace(item) for item in value]
    return value


class TestProviderValidation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with FIXTURE_PATH.open() as fixture_file:
            cls.fixture = json.load(fixture_file)
        cls.provider_chart = _namespace(cls.fixture["provider"])
        cls.reference = cls.fixture["reference"]

    def test_fixture_matches_all_validation_fields(self):
        result = validate_provider_chart(self.provider_chart, self.reference)

        self.assertTrue(result.passed, result.issues)

    def test_mismatch_reports_precise_field(self):
        reference = json.loads(json.dumps(self.reference))
        reference["planets"]["Moon"]["pada"] = 4

        result = validate_provider_chart(self.provider_chart, reference)

        self.assertFalse(result.passed)
        self.assertEqual(result.issues[0].path, "planets.Moon.pada")
        self.assertEqual(result.issues[0].expected, 4)
        self.assertEqual(result.issues[0].actual, 1)

    def test_equal_and_whole_sign_house_methods_are_both_visible(self):
        expected = self.fixture["house_method_difference"]

        equal_house = equal_house_number(
            expected["ascendant_longitude"],
            expected["planet_longitude"],
        )
        whole_sign_house = whole_sign_house_number(
            expected["ascendant_sign"],
            expected["planet_sign"],
        )

        self.assertEqual(equal_house, expected["equal_house"])
        self.assertEqual(whole_sign_house, expected["whole_sign_house"])
        self.assertNotEqual(equal_house, whole_sign_house)


if __name__ == "__main__":
    unittest.main()
