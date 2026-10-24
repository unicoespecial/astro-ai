import unittest
from datetime import datetime

from jyotishganit import calculate_birth_chart

from astrology import chart_from_jyotishganit


class TestJyotishganitIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.chart = calculate_birth_chart(
            birth_date=datetime(2005, 7, 4, 9, 10, 0),
            latitude=26.44,
            longitude=80.33,
            timezone_offset=5.5,
            name='Test User',
        )
        cls.canonical = chart_from_jyotishganit(cls.chart)

    def test_lossless_mapping_for_d1_fields(self):
        source = self.chart
        canon = self.canonical

        self.assertEqual(canon.name, source.person.name)
        self.assertEqual(canon.birth_data.name, source.person.name)
        self.assertEqual(canon.birth_data.date, source.person.birth_datetime.strftime('%Y-%m-%d'))
        self.assertEqual(canon.birth_data.time, source.person.birth_datetime.strftime('%H:%M'))
        self.assertEqual(canon.birth_data.latitude, source.person.latitude)
        self.assertEqual(canon.birth_data.longitude, source.person.longitude)
        self.assertEqual(canon.birth_data.timezone_offset, source.person.timezone_offset)
        self.assertEqual(canon.ascendant.sign, source.d1_chart.houses[0].sign)
        self.assertEqual(len(canon.houses), len(source.d1_chart.houses))
        self.assertEqual(len(canon.planets), len(source.d1_chart.planets))
        self.assertEqual(
            [p.name for p in canon.planets],
            [getattr(p, 'celestial_body', getattr(p, 'name', None)) for p in source.d1_chart.planets],
        )
        self.assertEqual(
            [p.sign for p in canon.planets],
            [getattr(p, 'sign', None) for p in source.d1_chart.planets],
        )
        self.assertEqual(
            [p.house for p in canon.planets],
            [getattr(p, 'house', None) for p in source.d1_chart.planets],
        )

    def test_lossless_mapping_for_optional_fields_when_present(self):
        source = self.chart
        canon = self.canonical

        for source_planet, canon_planet in zip(source.d1_chart.planets, canon.planets):
            self.assertEqual(canon_planet.raw, source_planet)
            self.assertEqual(canon_planet.motion_type, getattr(source_planet, 'motion_type', None))
            self.assertEqual(canon_planet.dignity, getattr(getattr(source_planet, 'dignities', None), 'dignity', None))
            self.assertEqual(canon_planet.lordship_houses, list(getattr(source_planet, 'has_lordship_houses', []) or []))
            self.assertEqual(canon_planet.aspects, list((getattr(source_planet, 'aspects', {}) or {}).get('gives', [])))
            self.assertEqual(canon_planet.conjuncts, list(getattr(source_planet, 'conjuncts', []) or []))

    def test_nakshatra_and_dasha_are_preserved_from_library(self):
        source = self.chart
        canon = self.canonical

        self.assertEqual(canon.nakshatra.name, source.panchanga.nakshatra)
        self.assertIsNotNone(canon.dashas)
        self.assertEqual(canon.dashas.current.name, next(iter(source.dashas.current['mahadashas'])))

    def test_divisional_charts_are_preserved_when_present(self):
        source = self.chart
        canon = self.canonical

        self.assertIn('d9', canon.divisional_charts)
        self.assertIn('d10', canon.divisional_charts)
        self.assertEqual(canon.divisional_charts['d9'].name, 'd9')
        self.assertEqual(canon.divisional_charts['d10'].name, 'd10')
        self.assertEqual(len(canon.divisional_charts['d9'].houses), len(source.divisional_charts['d9'].houses))
        self.assertEqual(len(canon.divisional_charts['d10'].houses), len(source.divisional_charts['d10'].houses))

    def test_missing_required_source_raises_clear_error(self):
        with self.assertRaises(ValueError):
            from astrology.adapter import chart_from_jyotishganit
            chart_from_jyotishganit(None)

        class IncompleteChart:
            pass

        with self.assertRaises(ValueError):
            from astrology.adapter import chart_from_jyotishganit
            chart_from_jyotishganit(IncompleteChart())


if __name__ == '__main__':
    unittest.main()
