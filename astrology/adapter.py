from __future__ import annotations

from typing import Any, Dict, List, Optional

from .models import Ascendant, BirthData, Chart, Dasha, DivisionalChart, House, Nakshatra, Planet


def _safe_dict_get(mapping: Any, key: str, default: Any = None) -> Any:
    if isinstance(mapping, dict):
        return mapping.get(key, default)
    return getattr(mapping, key, default)


def _as_house_list(source_houses: Any) -> List[House]:
    if not source_houses:
        return []
    return [House.from_source(item) for item in source_houses]


def _as_planet_list(source_planets: Any) -> List[Planet]:
    if not source_planets:
        return []
    return [Planet.from_source(item) for item in source_planets]


def _as_divisional_chart_map(source_divisions: Any) -> Dict[str, DivisionalChart]:
    if not source_divisions:
        return {}

    result: Dict[str, DivisionalChart] = {}
    if isinstance(source_divisions, dict):
        for key, value in source_divisions.items():
            result[str(key)] = DivisionalChart.from_source(value, str(key))
    return result


def _as_nakshatra(source: Any) -> Nakshatra:
    if source is None:
        return Nakshatra()
    if isinstance(source, dict):
        return Nakshatra.from_source(source)
    return Nakshatra.from_source(getattr(source, "nakshatra", None) or source)


def _as_dasha(source: Any) -> Optional[Dasha]:
    if source is None:
        return None
    if isinstance(source, dict):
        return Dasha.from_source(source)
    return Dasha.from_source(getattr(source, "current", None) or source)


def chart_from_jyotishganit(source: Any) -> Chart:
    """Convert the chart object produced by jyotishganit into the canonical model."""
    if source is None:
        raise ValueError("jyotishganit chart source is required")

    d1_chart = getattr(source, "d1_chart", None)
    if d1_chart is None:
        raise ValueError("jyotishganit chart missing required d1_chart data")

    houses = _as_house_list(getattr(d1_chart, "houses", None))
    planets = _as_planet_list(getattr(d1_chart, "planets", None))

    ascendant_source = houses[0] if houses else None
    ascendant = Ascendant.from_source(ascendant_source)

    person = getattr(source, "person", None)
    birth_dt = getattr(person, "birth_datetime", None) if person is not None else None
    birth_data = BirthData(
        date=birth_dt.strftime("%Y-%m-%d") if birth_dt else "",
        time=birth_dt.strftime("%H:%M") if birth_dt else "",
        latitude=getattr(person, "latitude", getattr(source, "latitude", None)),
        longitude=getattr(person, "longitude", getattr(source, "longitude", None)),
        timezone_offset=getattr(person, "timezone_offset", getattr(source, "timezone_offset", None)),
        city=getattr(person, "city", None),
        name=getattr(person, "name", getattr(source, "name", None)),
        raw=source,
    )

    panchanga = getattr(source, "panchanga", None)
    nakshatra = _as_nakshatra(_safe_dict_get(panchanga, "nakshatra"))

    dashas = _as_dasha(_safe_dict_get(getattr(source, "dashas", None), "current"))
    divisional_charts = _as_divisional_chart_map(getattr(source, "divisional_charts", None))

    return Chart(
        name=getattr(person, "name", getattr(source, "name", None)),
        birth_data=birth_data,
        ascendant=ascendant,
        planets=planets,
        houses=houses,
        nakshatra=nakshatra,
        dashas=dashas,
        divisional_charts=divisional_charts,
        raw=source,
    )
