from __future__ import annotations

from typing import Any


def build_city_options(cities: dict[str, dict[str, Any]], min_population: int = 50000) -> list[str]:
    """Build a searchable list of city labels in a stable, user-friendly form."""
    options = []
    for city in cities.values():
        population = city.get("population") or 0
        if population < min_population:
            continue
        name = city.get("name", "")
        country_code = city.get("countrycode", "")
        if name and country_code:
            options.append(f"{name}, {country_code}")
    return sorted(options)


def lookup_city_coords(city_value: str | None, cities: dict[str, dict[str, Any]]) -> tuple[float, float, str] | None:
    """Look up coordinates and timezone from either a label or a plain city name."""
    if not city_value:
        return None

    raw_query = city_value.split(",")[0].strip().lower()
    for city in cities.values():
        if city.get("name", "").lower() == raw_query:
            return city.get("latitude"), city.get("longitude"), city.get("timezone")

    if "," in city_value:
        name, country_code = [part.strip() for part in city_value.split(",", 1)]
        for city in cities.values():
            if city.get("name", "").lower() == name.lower() and city.get("countrycode", "").lower() == country_code.lower():
                return city.get("latitude"), city.get("longitude"), city.get("timezone")

    return None


def div_summary(chart: Any, key: str, label: str) -> str:
    """Return a compact divisional chart summary for use in the astrologer prompt."""
    try:
        div_chart = chart.divisional_charts.get(key)
        if not div_chart:
            return ""
        lines = [label]
        for house in getattr(div_chart, "houses", []) or []:
            for occupant in getattr(house, "occupants", []) or []:
                body = getattr(occupant, "celestial_body", None) or getattr(occupant, "name", None)
                sign = getattr(occupant, "sign", None)
                house_number = getattr(house, "number", None)
                if body and sign and house_number is not None:
                    lines.append(f"  {body}: {sign} (House {house_number})")
        return "\n".join(lines)
    except Exception:
        return ""
