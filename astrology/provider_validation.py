from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from math import floor
from typing import Any, Dict, List, Mapping, Optional


ZODIAC_SIGNS = (
    "Aries",
    "Taurus",
    "Gemini",
    "Cancer",
    "Leo",
    "Virgo",
    "Libra",
    "Scorpio",
    "Sagittarius",
    "Capricorn",
    "Aquarius",
    "Pisces",
)


@dataclass(frozen=True)
class ValidationIssue:
    path: str
    expected: Any
    actual: Any


@dataclass
class ValidationResult:
    issues: List[ValidationIssue] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.issues


def _get(source: Any, key: str, default: Any = None) -> Any:
    if isinstance(source, Mapping):
        return source.get(key, default)
    return getattr(source, key, default)


def _planet_map(planets: Any) -> Dict[str, Any]:
    result = {}
    for planet in planets or []:
        name = _get(planet, "celestial_body") or _get(planet, "name")
        if name:
            result[str(name)] = planet
    return result


def _longitude(planet: Any) -> Optional[float]:
    longitude = _get(planet, "sidereal_longitude")
    if longitude is not None:
        return float(longitude)

    sign = _get(planet, "sign")
    degrees = _get(planet, "sign_degrees")
    if sign not in ZODIAC_SIGNS or degrees is None:
        return None
    return ZODIAC_SIGNS.index(sign) * 30 + float(degrees)


def _normalized(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _dasha_periods(chart: Any) -> Any:
    dashas = _get(chart, "dashas")
    return _get(dashas, "all", _get(dashas, "periods", {}))


def _items(source: Any) -> list[tuple[str, Any]]:
    if isinstance(source, Mapping):
        return list(source.items())
    if hasattr(source, "__dict__"):
        return list(vars(source).items())
    return []


def _first_dasha(periods: Any) -> tuple[Optional[str], Any]:
    mahadashas = _get(periods, "mahadashas", {})
    entries = _items(mahadashas)
    if not entries:
        return None, None
    return entries[0]


def validate_provider_chart(
    chart: Any,
    reference: Mapping[str, Any],
    longitude_tolerance: float = 1e-6,
) -> ValidationResult:
    """Compare an already-supplied provider chart with independent fixture data."""
    issues: List[ValidationIssue] = []
    d1 = _get(chart, "d1_chart")
    houses = _get(d1, "houses", [])
    planets = _planet_map(_get(d1, "planets", []))

    ascendant = _get(reference, "ascendant", {})
    actual_ascendant = houses[0] if houses else None
    for field_name in ("sign", "degree"):
        expected = _get(ascendant, field_name)
        actual_field = "sign_degrees" if field_name == "degree" else field_name
        actual = _get(actual_ascendant, actual_field)
        if expected is not None and actual != expected:
            issues.append(ValidationIssue(f"ascendant.{field_name}", expected, actual))

    reference_planets = _get(reference, "planets", {})
    for name, expected_planet in reference_planets.items():
        actual_planet = planets.get(name)
        if actual_planet is None:
            issues.append(ValidationIssue(f"planets.{name}", "present", None))
            continue
        expected_longitude = _get(expected_planet, "longitude")
        actual_longitude = _longitude(actual_planet)
        if expected_longitude is not None and (
            actual_longitude is None
            or abs(actual_longitude - float(expected_longitude)) > longitude_tolerance
        ):
            issues.append(ValidationIssue(f"planets.{name}.longitude", expected_longitude, actual_longitude))
        for field_name in ("sign", "house", "nakshatra", "pada"):
            expected = _get(expected_planet, field_name)
            actual = _get(actual_planet, field_name)
            if expected is not None and actual != expected:
                issues.append(ValidationIssue(f"planets.{name}.{field_name}", expected, actual))

    panchanga = _get(chart, "panchanga")
    moon_reference = _get(reference, "moon", {})
    for field_name in ("nakshatra", "pada"):
        expected = _get(moon_reference, field_name)
        actual = _get(panchanga, "nakshatra") if field_name == "nakshatra" else _get(planets.get("Moon"), "pada")
        if expected is not None and actual != expected:
            issues.append(ValidationIssue(f"moon.{field_name}", expected, actual))

    reference_houses = _get(reference, "houses", [])
    actual_houses = {int(_get(house, "number")): house for house in houses or []}
    for expected_house in reference_houses:
        number = int(_get(expected_house, "number"))
        expected_sign = _get(expected_house, "sign")
        actual_sign = _get(actual_houses.get(number), "sign")
        if expected_sign is not None and actual_sign != expected_sign:
            issues.append(ValidationIssue(f"houses.{number}.sign", expected_sign, actual_sign))

    reference_divisions = _get(reference, "divisional_charts", {})
    actual_divisions = _get(chart, "divisional_charts", {})
    for division_name, expected_division in reference_divisions.items():
        actual_division = _get(actual_divisions, division_name)
        if actual_division is None:
            issues.append(ValidationIssue(f"divisional_charts.{division_name}", "present", None))
            continue
        actual_division_planets = _planet_map(_get(actual_division, "planets", []))
        for planet_name, expected_planet in _get(expected_division, "planets", {}).items():
            actual_planet = actual_division_planets.get(planet_name)
            for field_name in ("sign", "house"):
                expected = _get(expected_planet, field_name)
                actual = _get(actual_planet, field_name)
                if expected is not None and actual != expected:
                    issues.append(ValidationIssue(
                        f"divisional_charts.{division_name}.planets.{planet_name}.{field_name}",
                        expected,
                        actual,
                    ))

    expected_dasha = _get(reference, "vimshottari", {})
    actual_lord, actual_period = _first_dasha(_dasha_periods(chart))
    expected_lord = _get(expected_dasha, "starting_lord")
    if expected_lord is not None and actual_lord != expected_lord:
        issues.append(ValidationIssue("vimshottari.starting_lord", expected_lord, actual_lord))
    for field_name in ("start", "end"):
        expected = _get(expected_dasha, field_name)
        actual = _normalized(_get(actual_period, field_name))
        if expected is not None and actual != expected:
            issues.append(ValidationIssue(f"vimshottari.{field_name}", expected, actual))

    return ValidationResult(issues)


def equal_house_number(ascendant_longitude: float, planet_longitude: float) -> int:
    """Replicate the provider's equal 30-degree house placement."""
    return floor((planet_longitude - ascendant_longitude) % 360 / 30) + 1


def whole_sign_house_number(ascendant_sign: str, planet_sign: str) -> int:
    """Calculate a whole-sign house number without selecting a preferred method."""
    ascendant_index = ZODIAC_SIGNS.index(ascendant_sign)
    planet_index = ZODIAC_SIGNS.index(planet_sign)
    return (planet_index - ascendant_index) % 12 + 1
