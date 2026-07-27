from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import streamlit as st
from jyotishganit import calculate_birth_chart

PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]


def build_city_options(cities: dict[str, dict[str, Any]], min_population: int = 50000) -> list[str]:
    options = []
    for city in cities.values():
        if (city.get("population") or 0) <= min_population:
            continue
        name = city.get("name")
        country_code = city.get("countrycode")
        if name and country_code:
            options.append(f"{name}, {country_code}")
    return sorted(options)


def city_to_coords(city_name: str | None, cities: dict[str, dict[str, Any]]) -> tuple[float, float, str] | None:
    if not city_name:
        return None

    query = city_name.split(",")[0].strip().lower()
    for city in cities.values():
        if city.get("name", "").lower() == query:
            return city.get("latitude"), city.get("longitude"), city.get("timezone")

    if "," in city_name:
        name, country_code = [part.strip() for part in city_name.split(",", 1)]
        for city in cities.values():
            if (
                city.get("name", "").lower() == name.lower()
                and city.get("countrycode", "").lower() == country_code.lower()
            ):
                return city.get("latitude"), city.get("longitude"), city.get("timezone")

    return None


def tz_offset(tzname: str, birth_dt: datetime) -> float:
    try:
        return birth_dt.replace(tzinfo=ZoneInfo(tzname)).utcoffset().total_seconds() / 3600
    except Exception:
        return 5.5


@st.cache_data(show_spinner=False)
def get_cached_birth_chart(birth_inputs: tuple[datetime, float, float, float]):
    birth_date, latitude, longitude, timezone_offset = birth_inputs
    return calculate_birth_chart(
        birth_date=birth_date,
        latitude=latitude,
        longitude=longitude,
        timezone_offset=timezone_offset,
        name="",
    )


def build_birth_chart(birth_date: datetime, latitude: float, longitude: float, timezone_offset: float, name: str):
    chart = get_cached_birth_chart((birth_date, latitude, longitude, timezone_offset))
    try:
        chart.name = name
    except Exception:
        pass
    return chart


def current_dasha(chart: Any) -> str:
    try:
        cur = chart.dashas.current
        maha = cur["mahadashas"]
        maha_name = next(iter(maha))
        node = maha[maha_name]
        line = f"Current Mahadasha: {maha_name}"

        antar = node.get("antardashas")
        if antar:
            antar_name = next(iter(antar))
            line += f" -> Antardasha: {antar_name}"
            praty = antar[antar_name].get("pratyantardashas")
            if praty:
                line += f" -> Pratyantardasha: {next(iter(praty))}"
        return line
    except Exception as exc:
        return f"Current period: unavailable ({exc})"


def chart_intro_message(name: str, chart: Any) -> str:
    try:
        lagna = chart.d1_chart.houses[0].sign
        planet = chart.d1_chart.planets[0]
        return (
            f"Namaste {name}. With {lagna} rising, I already see a strong {planet.sign} "
            f"imprint shaping the way you move through the world. What is asking for your attention today?"
        )
    except Exception:
        return f"Namaste {name}. I’ve read your chart. What is asking for your attention today?"


def build_placement_rows(chart: Any) -> list[dict[str, Any]]:
    rows = []
    for index, planet in enumerate(PLANETS):
        try:
            placement = chart.d1_chart.planets[index]
            rows.append(
                {
                    "planet": planet,
                    "sign": placement.sign,
                    "house": placement.house,
                    "dignity": placement.dignities.dignity,
                    "motion": placement.motion_type,
                    "rules": placement.has_lordship_houses,
                }
            )
        except Exception:
            pass
    return rows


def div_summary(chart: Any, key: str, label: str) -> str:
    try:
        div_chart = chart.divisional_charts.get(key)
        if not div_chart:
            return ""
        lines = [label]
        for house in getattr(div_chart, "houses", []) or []:
            for occupant in getattr(house, "occupants", []) or []:
                body = getattr(occupant, "celestial_body", None) or getattr(occupant, "name", None)
                sign = getattr(occupant, "sign", None)
                if body and sign:
                    lines.append(f"  {body}: {sign} (House {house.number})")
        return "\n".join(lines)
    except Exception:
        return ""


def chart_summary(chart: Any) -> str:
    lines = [f"Ascendant (Lagna): {chart.d1_chart.houses[0].sign}"]
    for index, planet in enumerate(PLANETS):
        try:
            placement = chart.d1_chart.planets[index]
            extra = ""
            if getattr(placement, "conjuncts", None):
                extra += f", with {'+'.join(placement.conjuncts)}"
            gives = (getattr(placement, "aspects", {}) or {}).get("gives", [])
            if gives:
                houses = ",".join(str(item["to_house"]) for item in gives)
                extra += f", aspects houses {houses}"
            lines.append(
                f"{planet}: {placement.sign} (House {placement.house}), {placement.dignities.dignity}, "
                f"{placement.motion_type}, rules {placement.has_lordship_houses}{extra}"
            )
        except Exception:
            pass
    lines.append(f"Moon Nakshatra: {chart.panchanga.nakshatra}")
    lines.append(current_dasha(chart))
    return "\n".join(lines)
