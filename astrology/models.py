from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


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


@dataclass
class BirthData:
    date: str
    time: str
    latitude: float
    longitude: float
    timezone_offset: float
    city: Optional[str] = None
    name: Optional[str] = None
    raw: Optional[Any] = None


@dataclass
class Planet:
    name: str
    sign: Optional[str] = None
    sidereal_longitude: Optional[float] = None
    degree_within_sign: Optional[float] = None
    nakshatra: Optional[str] = None
    pada: Optional[int] = None
    house: Optional[int] = None
    motion_type: Optional[str] = None
    dignity: Optional[str] = None
    lordship_houses: List[int] = field(default_factory=list)
    aspects: List[Dict[str, Any]] = field(default_factory=list)
    conjuncts: List[str] = field(default_factory=list)
    raw: Optional[Any] = None

    @classmethod
    def from_source(cls, source: Any) -> "Planet":
        if source is None:
            return cls(name="")

        sign = getattr(source, "sign", None)
        degree_within_sign = getattr(source, "sign_degrees", None)
        sidereal_longitude = getattr(source, "sidereal_longitude", None)
        if sidereal_longitude is None and sign in ZODIAC_SIGNS and degree_within_sign is not None:
            sidereal_longitude = ZODIAC_SIGNS.index(sign) * 30 + float(degree_within_sign)

        dignities = getattr(source, "dignities", None)
        dignity_value = getattr(dignities, "dignity", None) if dignities is not None else None

        aspects_raw = getattr(source, "aspects", {}) or {}
        gives = aspects_raw.get("gives", []) if isinstance(aspects_raw, dict) else []

        return cls(
            name=str(getattr(source, "celestial_body", None) or getattr(source, "name", "")),
            sign=sign,
            sidereal_longitude=sidereal_longitude,
            degree_within_sign=degree_within_sign,
            nakshatra=getattr(source, "nakshatra", None),
            pada=getattr(source, "pada", None),
            house=getattr(source, "house", None),
            motion_type=getattr(source, "motion_type", None),
            dignity=dignity_value,
            lordship_houses=list(getattr(source, "has_lordship_houses", []) or []),
            aspects=list(gives),
            conjuncts=list(getattr(source, "conjuncts", []) or []),
            raw=source,
        )


@dataclass
class House:
    number: int
    sign: Optional[str] = None
    occupants: List[str] = field(default_factory=list)
    raw: Optional[Any] = None

    @classmethod
    def from_source(cls, source: Any) -> "House":
        if source is None:
            return cls(number=0)

        occupants = []
        for occupant in getattr(source, "occupants", []) or []:
            if hasattr(occupant, "celestial_body"):
                occupants.append(str(occupant.celestial_body))
            elif hasattr(occupant, "name"):
                occupants.append(str(occupant.name))
            elif isinstance(occupant, str):
                occupants.append(occupant)

        return cls(
            number=int(getattr(source, "number", 0)),
            sign=getattr(source, "sign", None),
            occupants=occupants,
            raw=source,
        )


@dataclass
class Ascendant:
    sign: Optional[str] = None
    longitude: Optional[float] = None
    degree: Optional[float] = None
    raw: Optional[Any] = None

    @classmethod
    def from_source(cls, source: Any) -> "Ascendant":
        if source is None:
            return cls()

        return cls(
            sign=getattr(source, "sign", None),
            longitude=getattr(source, "longitude", getattr(source, "sidereal_longitude", None)),
            degree=getattr(source, "degree", getattr(source, "sign_degrees", None)),
            raw=source,
        )


@dataclass
class Nakshatra:
    name: Optional[str] = None
    pada: Optional[int] = None
    raw: Optional[Any] = None

    @classmethod
    def from_source(cls, source: Any) -> "Nakshatra":
        if source is None:
            return cls()

        if isinstance(source, str):
            return cls(name=source, raw=source)

        if isinstance(source, dict):
            return cls(
                name=source.get("name") or source.get("nakshatra"),
                pada=source.get("pada"),
                raw=source,
            )

        return cls(
            name=getattr(source, "name", None) or getattr(source, "nakshatra", None),
            pada=getattr(source, "pada", None),
            raw=source,
        )


@dataclass
class Dasha:
    name: Optional[str] = None
    antardashas: Dict[str, "Dasha"] = field(default_factory=dict)
    pratyantardashas: Dict[str, "Dasha"] = field(default_factory=dict)
    raw: Optional[Any] = None

    @property
    def current(self) -> "Dasha":
        return self

    @classmethod
    def from_source(cls, source: Any) -> "Dasha":
        if source is None:
            return cls()

        if isinstance(source, dict):
            if "mahadashas" in source and isinstance(source["mahadashas"], dict):
                mahas = source["mahadashas"]
                maha_name, maha_node = next(iter(mahas.items()), (None, {})) if mahas else (None, {})
                antardashas = {}
                praty = {}

                if isinstance(maha_node, dict):
                    antardashas_raw = maha_node.get("antardashas", {})
                    if isinstance(antardashas_raw, dict):
                        for key, value in antardashas_raw.items():
                            antardashas[key] = cls.from_source({key: value})
                    praty_raw = maha_node.get("pratyantardashas", {})
                    if isinstance(praty_raw, dict):
                        for key, value in praty_raw.items():
                            praty[key] = cls.from_source({key: value})

                return cls(
                    name=maha_name,
                    antardashas=antardashas,
                    pratyantardashas=praty,
                    raw=source,
                )

            first_name, node = next(iter(source.items()), (None, {}))
            antardashas = {}
            praty = {}

            if isinstance(node, dict):
                antardashas_raw = node.get("antardashas", {})
                if isinstance(antardashas_raw, dict):
                    for key, value in antardashas_raw.items():
                        antardashas[key] = cls.from_source({key: value})
                praty_raw = node.get("pratyantardashas", {})
                if isinstance(praty_raw, dict):
                    for key, value in praty_raw.items():
                        praty[key] = cls.from_source({key: value})

            return cls(
                name=first_name,
                antardashas=antardashas,
                pratyantardashas=praty,
                raw=source,
            )

        return cls(name=getattr(source, "name", None), raw=source)


@dataclass
class DivisionalChart:
    name: str
    houses: List[House] = field(default_factory=list)
    planets: List[Planet] = field(default_factory=list)
    raw: Optional[Any] = None

    @classmethod
    def from_source(cls, source: Any, name: str) -> "DivisionalChart":
        if source is None:
            return cls(name=name)

        houses = [House.from_source(item) for item in getattr(source, "houses", []) or []]
        planets = [Planet.from_source(item) for item in getattr(source, "planets", []) or []]

        return cls(
            name=name,
            houses=houses,
            planets=planets,
            raw=source,
        )


@dataclass
class Chart:
    name: Optional[str] = None
    birth_data: Optional[BirthData] = None
    ascendant: Optional[Ascendant] = None
    planets: List[Planet] = field(default_factory=list)
    houses: List[House] = field(default_factory=list)
    nakshatra: Optional[Nakshatra] = None
    dashas: Optional[Dasha] = None
    divisional_charts: Dict[str, DivisionalChart] = field(default_factory=dict)
    raw: Optional[Any] = None

    @classmethod
    def from_source(cls, source: Any) -> "Chart":
        if source is None:
            raise ValueError("jyotishganit chart source is required")

        d1_chart = getattr(source, "d1_chart", None)
        if d1_chart is None:
            raise ValueError("jyotishganit chart missing required d1_chart data")

        house_objects = [House.from_source(item) for item in getattr(d1_chart, "houses", []) or []]
        planet_objects = [Planet.from_source(item) for item in getattr(d1_chart, "planets", []) or []]
        ascendant_obj = Ascendant.from_source(house_objects[0]) if house_objects else Ascendant()

        panchanga = getattr(source, "panchanga", None)
        nakshatra_obj = Nakshatra.from_source(getattr(panchanga, "nakshatra", None)) if panchanga is not None else Nakshatra()

        dashas_obj = Dasha.from_source(getattr(getattr(source, "dashas", None), "current", None)) if getattr(source, "dashas", None) else None

        divisional_map = {}
        for key, value in (getattr(source, "divisional_charts", {}) or {}).items():
            divisional_map[str(key)] = DivisionalChart.from_source(value, str(key))

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

        return cls(
            name=getattr(person, "name", getattr(source, "name", None)),
            birth_data=birth_data,
            ascendant=ascendant_obj,
            planets=planet_objects,
            houses=house_objects,
            nakshatra=nakshatra_obj,
            dashas=dashas_obj,
            divisional_charts=divisional_map,
            raw=source,
        )
