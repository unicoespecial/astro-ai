SIGN_NUM = {"Aries": 1, "Taurus": 2, "Gemini": 3, "Cancer": 4, "Leo": 5, "Virgo": 6,
            "Libra": 7, "Scorpio": 8, "Sagittarius": 9, "Capricorn": 10,
            "Aquarius": 11, "Pisces": 12}

ABBR = {"Sun": "Su", "Moon": "Mo", "Mars": "Ma", "Mercury": "Me", "Jupiter": "Ju",
        "Venus": "Ve", "Saturn": "Sa", "Rahu": "Ra", "Ketu": "Ke"}

HOUSE_POS = {1: (200, 70), 2: (100, 32), 3: (32, 100), 4: (72, 200),
             5: (32, 300), 6: (100, 368), 7: (200, 330), 8: (300, 368),
             9: (368, 300), 10: (328, 200), 11: (368, 100), 12: (300, 32)}


def render_chart_svg(chart):
    parts = []
    for house in chart.d1_chart.houses:
        x, y = HOUSE_POS[house.number]

        parts.append(
            f'<text x="{x}" y="{y}" fill="#8a7a5c" font-size="13" '
            f'text-anchor="middle" font-family="serif">{SIGN_NUM.get(house.sign, "")}</text>')

        names = []
        for occupant in house.occupants:
            raw = occupant if isinstance(occupant, str) else getattr(occupant, "celestial_body", str(occupant))
            names.append(ABBR.get(raw, raw[:2]))

        for index, name in enumerate(names):
            parts.append(
                f'<text x="{x}" y="{y + 17 + index * 15}" fill="#efe7d6" font-size="13" '
                f'text-anchor="middle" font-family="sans-serif">{name}</text>')

    return f'''<svg viewBox="0 0 400 400" width="100%" style="max-width:420px"
      xmlns="http://www.w3.org/2000/svg">
      <rect x="0" y="0" width="400" height="400" fill="none" stroke="#8a7a5c" stroke-width="1.5"/>
      <line x1="0" y1="0" x2="400" y2="400" stroke="#8a7a5c" stroke-width="1"/>
      <line x1="400" y1="0" x2="0" y2="400" stroke="#8a7a5c" stroke-width="1"/>
      <polygon points="200,0 400,200 200,400 0,200" fill="none" stroke="#8a7a5c" stroke-width="1"/>
      {"".join(parts)}
    </svg>'''
