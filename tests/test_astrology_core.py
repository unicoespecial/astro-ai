import unittest
from types import SimpleNamespace

from astrology import Chart, Dasha, DivisionalChart, House, Nakshatra, Planet, BirthData, chart_from_jyotishganit


class TestAstrologyCore(unittest.TestCase):
    def _make_chart(self):
        house_1 = SimpleNamespace(
            number=1,
            sign="Aries",
            occupants=["Sun", "Moon"],
        )
        house_2 = SimpleNamespace(number=2, sign="Taurus", occupants=["Mars"])

        planet_sun = SimpleNamespace(
            celestial_body="Sun",
            name="Sun",
            sign="Aries",
            house=1,
            motion_type="Direct",
            dignities=SimpleNamespace(dignity="Exaltation"),
            has_lordship_houses=[1, 2],
            aspects={"gives": [{"to_house": 3}]},
            conjuncts=["Moon"],
        )
        planet_moon = SimpleNamespace(
            celestial_body="Moon",
            name="Moon",
            sign="Taurus",
            house=2,
            motion_type="Retrograde",
            dignities=SimpleNamespace(dignity="Own sign"),
            has_lordship_houses=[2],
            aspects={"gives": []},
            conjuncts=[],
        )

        d1 = SimpleNamespace(
            houses=[house_1, house_2],
            planets=[planet_sun, planet_moon],
        )

        division = SimpleNamespace(
            houses=[
                SimpleNamespace(number=1, occupants=[SimpleNamespace(name="Sun", sign="Aries")]),
                SimpleNamespace(number=2, occupants=[SimpleNamespace(name="Moon", sign="Taurus")]),
            ]
        )

        dasha_current = {
            "mahadashas": {
                "Sun": {
                    "antardashas": {
                        "Moon": {"pratyantardashas": {"Mars": {}}}
                    }
                }
            }
        }

        chart = SimpleNamespace(
            name="Test User",
            birth_date="2024-01-01",
            birth_time="09:30",
            latitude=28.6139,
            longitude=77.2090,
            timezone_offset=5.5,
            birth_city="Delhi",
            d1_chart=d1,
            panchanga=SimpleNamespace(nakshatra="Ashwini"),
            dashas=SimpleNamespace(current=dasha_current),
            divisional_charts={"d9": division},
        )
        return chart

    def test_birth_data_model_can_store_key_fields(self):
        data = BirthData(
            date="2024-01-01",
            time="09:30",
            latitude=28.6139,
            longitude=77.2090,
            timezone_offset=5.5,
            city="Delhi",
            name="Test User",
        )
        self.assertEqual(data.city, "Delhi")
        self.assertEqual(data.latitude, 28.6139)

    def test_chart_adapter_builds_canonical_chart(self):
        source = self._make_chart()
        chart = chart_from_jyotishganit(source)

        self.assertIsInstance(chart, Chart)
        self.assertEqual(chart.name, "Test User")
        self.assertEqual(chart.ascendant.sign, "Aries")
        self.assertEqual(chart.nakshatra.name, "Ashwini")
        self.assertEqual(len(chart.planets), 2)
        self.assertEqual(chart.planets[0].name, "Sun")
        self.assertEqual(chart.houses[0].number, 1)
        self.assertEqual(chart.dashas.current.name, "Sun")
        self.assertEqual(chart.divisional_charts["d9"].name, "d9")
        self.assertTrue(chart.raw is source)

    def test_dasha_model_preserves_nested_structure(self):
        source = {
            "mahadashas": {
                "Sun": {
                    "antardashas": {
                        "Moon": {"pratyantardashas": {"Mars": {}}}
                    }
                }
            }
        }
        dasha = Dasha.from_source(source)
        self.assertEqual(dasha.name, "Sun")
        self.assertIn("Moon", dasha.antardashas)
        self.assertEqual(dasha.antardashas["Moon"].name, "Moon")
        self.assertIn("Mars", dasha.antardashas["Moon"].pratyantardashas)

    def test_divisional_chart_and_house_model(self):
        d9 = DivisionalChart.from_source(
            SimpleNamespace(
                houses=[
                    SimpleNamespace(number=1, occupants=[SimpleNamespace(name="Sun", sign="Aries")]),
                    SimpleNamespace(number=2, occupants=[SimpleNamespace(name="Moon", sign="Taurus")]),
                ]
            ),
            name="d9",
        )
        self.assertEqual(d9.name, "d9")
        self.assertEqual(d9.houses[0].number, 1)
        self.assertEqual(d9.houses[0].occupants[0], "Sun")


if __name__ == "__main__":
    unittest.main()
