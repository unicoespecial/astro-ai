import streamlit as st
import psycopg2
import bcrypt
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from jyotishganit import calculate_birth_chart
from groq import Groq
import geonamescache

st.set_page_config(page_title="AI Astrologer", page_icon="🔮", layout="centered")
st.markdown("""
<style>
  h1, h2, h3 { font-family: Georgia, serif !important; font-weight: 500 !important; }
  section[data-testid="stSidebar"] { background: #16151a; border-right: 1px solid #2a2730; }
  .stButton button {
      background: transparent; border: 1px solid #3d3a45; color: #e8e2d6;
      border-radius: 2px; font-size: 0.85rem;
  }
  .stButton button:hover { border-color: #c9a227; color: #c9a227; }
  .stChatMessage { background: transparent !important; border-bottom: 1px solid #1e1c23; }
  .card { border: 1px solid #2a2730; padding: 18px 20px; height: 100%; }
  .card h4 { color: #c9a227; font-family: Georgia, serif; font-size: 0.95rem; margin: 0 0 8px 0; }
  .card p { color: #9a9490; font-size: 0.85rem; line-height: 1.5; margin: 0; }
  .hero-line { color: #e8e2d6; font-size: 1.02rem; line-height: 1.6; margin: 0 0 1.4rem 0; max-width: 680px; }
  .soft-note { color: #9a9490; font-size: 0.92rem; line-height: 1.6; margin: 0 0 1rem 0; }
  .placement-card { border: 1px solid #2a2730; padding: 0.8rem 0.9rem; margin-bottom: 0.7rem; border-radius: 6px; }
  .placement-name { color: #c9a227; font-weight: 600; margin-bottom: 0.15rem; }
  .placement-meta { color: #9a9490; font-size: 0.9rem; line-height: 1.45; }
  .mini-pill { color: #c9a227; border: 1px solid #2a2730; padding: 0.35rem 0.6rem; border-radius: 999px; display: inline-block; font-size: 0.82rem; margin-bottom: 0.6rem; }
</style>
""", unsafe_allow_html=True)

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
_cities = geonamescache.GeonamesCache().get_cities()


def build_city_options(cities):
    options = []
    for city in cities.values():
        if (city.get("population") or 0) <= 50000:
            continue
        name = city.get("name")
        country_code = city.get("countrycode")
        if name and country_code:
            options.append(f"{name}, {country_code}")
    return sorted(options)


_city_options = build_city_options(_cities)


# ---------- DATABASE ----------
def get_connection():
    return psycopg2.connect(st.secrets["DB_URL"])   


def init_db():
    con = get_connection()
    cur = con.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY, name TEXT, summary TEXT, memory TEXT,
        password_hash TEXT)""")
    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash TEXT")
    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS birth_date TEXT")
    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS birth_time TEXT")
    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS birth_city TEXT")
    con.commit()
    con.close()


def hash_password(password):
    """Scramble a password for storage. One-way — cannot be unscrambled."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def check_password(password, stored_hash):
    """Does the typed password match the stored scramble?"""
    if not stored_hash:
        return False
    return bcrypt.checkpw(password.encode(), stored_hash.encode())


def load_user(username):
    con = get_connection()
    cur = con.cursor()
    cur.execute("SELECT name, summary, memory, password_hash, birth_date, birth_time, birth_city FROM users WHERE username = %s",
                (username,))
    row = cur.fetchone()
    con.close()
    return row  # None if new, else (name, summary, memory, password_hash, birth_date, birth_time, birth_city)


def save_user(username, password_hash=None):
    con = get_connection()
    cur = con.cursor()
    birth_date = st.session_state.get("birth_date", "")
    birth_time = st.session_state.get("birth_time", "")
    birth_city = st.session_state.get("birth_city", "")
    if password_hash:
        cur.execute("""INSERT INTO users (username, name, summary, memory, password_hash, birth_date, birth_time, birth_city)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (username) DO UPDATE SET
                name = EXCLUDED.name, summary = EXCLUDED.summary,
                memory = EXCLUDED.memory, password_hash = EXCLUDED.password_hash,
                birth_date = EXCLUDED.birth_date, birth_time = EXCLUDED.birth_time,
                birth_city = EXCLUDED.birth_city""",
            (username, st.session_state.name, st.session_state.summary,
             st.session_state.memory, password_hash, birth_date, birth_time, birth_city))
    else:
        cur.execute("""INSERT INTO users (username, name, summary, memory, birth_date, birth_time, birth_city)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (username) DO UPDATE SET
                name = EXCLUDED.name, summary = EXCLUDED.summary, memory = EXCLUDED.memory,
                birth_date = EXCLUDED.birth_date, birth_time = EXCLUDED.birth_time,
                birth_city = EXCLUDED.birth_city""",
            (username, st.session_state.name, st.session_state.summary, st.session_state.memory,
             birth_date, birth_time, birth_city))
    con.commit()
    con.close()


@st.dialog("Save your chart")
def signup_dialog():
    st.write("Save your chart so your astrologer remembers you.")
    u = st.text_input("Choose a username").strip()
    p = st.text_input("Choose a password (8+ characters)", type="password")
    if st.button("Save my chart"):
        if not u or len(p) < 8:
            st.warning("Username required, password must be 8+ characters.")
        elif load_user(u):
            st.error("That username is taken.")
        else:
            st.session_state.username = u
            save_user(u, hash_password(p))
            st.rerun()


@st.dialog("Welcome back")
def login_dialog():
    u = st.text_input("Username").strip()
    p = st.text_input("Password", type="password")
    if st.button("Open my chart"):
        row = load_user(u)
        if not row or not check_password(p, row[3]):
            st.error("Wrong username or password.")
        else:
            saved_name, summary, memory, _, birth_date, birth_time, birth_city = row
            st.session_state.username = u
            st.session_state.name = saved_name
            st.session_state.summary = summary
            st.session_state.memory = memory or ""
            st.session_state.birth_date = birth_date or ""
            st.session_state.birth_time = birth_time or ""
            st.session_state.birth_city = birth_city or ""
            st.session_state.messages = [{"role": "assistant",
                "content": f"Welcome back, {saved_name}. What's on your mind today?"}]
            st.rerun()


init_db()


# ---------- CHART HELPERS ----------
SIGN_NUM = {"Aries": 1, "Taurus": 2, "Gemini": 3, "Cancer": 4, "Leo": 5, "Virgo": 6,
            "Libra": 7, "Scorpio": 8, "Sagittarius": 9, "Capricorn": 10,
            "Aquarius": 11, "Pisces": 12}

ABBR = {"Sun": "Su", "Moon": "Mo", "Mars": "Ma", "Mercury": "Me", "Jupiter": "Ju",
        "Venus": "Ve", "Saturn": "Sa", "Rahu": "Ra", "Ketu": "Ke"}

# Where each house's text sits inside the 400x400 grid
HOUSE_POS = {1: (200, 70), 2: (100, 32), 3: (32, 100), 4: (72, 200),
             5: (32, 300), 6: (100, 368), 7: (200, 330), 8: (300, 368),
             9: (368, 300), 10: (328, 200), 11: (368, 100), 12: (300, 32)}


def render_chart_svg(chart):
    """Draw a North Indian (diamond) birth chart as SVG."""
    parts = []
    for h in chart.d1_chart.houses:
        x, y = HOUSE_POS[h.number]

        # Sign number — small, faint, top of the cell
        parts.append(
            f'<text x="{x}" y="{y}" fill="#8a7a5c" font-size="13" '
            f'text-anchor="middle" font-family="serif">{SIGN_NUM.get(h.sign, "")}</text>')

        # Planets in this house, stacked below the sign number
        names = []
        for occ in h.occupants:
            raw = occ if isinstance(occ, str) else getattr(occ, "celestial_body", str(occ))
            names.append(ABBR.get(raw, raw[:2]))

        for i, nm in enumerate(names):
            parts.append(
                f'<text x="{x}" y="{y + 17 + i * 15}" fill="#efe7d6" font-size="13" '
                f'text-anchor="middle" font-family="sans-serif">{nm}</text>')

    return f'''<svg viewBox="0 0 400 400" width="100%" style="max-width:420px"
      xmlns="http://www.w3.org/2000/svg">
      <rect x="0" y="0" width="400" height="400" fill="none" stroke="#8a7a5c" stroke-width="1.5"/>
      <line x1="0" y1="0" x2="400" y2="400" stroke="#8a7a5c" stroke-width="1"/>
      <line x1="400" y1="0" x2="0" y2="400" stroke="#8a7a5c" stroke-width="1"/>
      <polygon points="200,0 400,200 200,400 0,200" fill="none" stroke="#8a7a5c" stroke-width="1"/>
      {"".join(parts)}
    </svg>'''


def city_to_coords(city_name):
    """City name -> (lat, lon, timezone_name). None if not found."""
    if not city_name:
        return None

    query = city_name.split(",")[0].strip().lower()
    for city in _cities.values():
        if city.get("name", "").lower() == query:
            return city.get("latitude"), city.get("longitude"), city.get("timezone")

    if "," in city_name:
        name, country_code = [part.strip() for part in city_name.split(",", 1)]
        for city in _cities.values():
            if (city.get("name", "").lower() == name.lower() and
                    city.get("countrycode", "").lower() == country_code.lower()):
                return city.get("latitude"), city.get("longitude"), city.get("timezone")

    return None


def tz_offset(tzname, birth_dt):
    """Hours offset from UTC for this timezone on the birth date (handles DST)."""
    try:
        return birth_dt.replace(tzinfo=ZoneInfo(tzname)).utcoffset().total_seconds() / 3600
    except Exception:
        return 5.5  # Fallback to IST


def current_dasha(chart):
    """Read the already-filtered 'current' branch: Maha -> Antar -> Pratyantar."""
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
    except Exception as e:
        return f"Current period: unavailable ({e})"


def chart_intro_message(name, chart):
    try:
        lagna = chart.d1_chart.houses[0].sign
        planet = chart.d1_chart.planets[0]
        return (f"Namaste {name}. With {lagna} rising, I already see a strong {planet.sign} "
                f"imprint shaping the way you move through the world. What is asking for your attention today?")
    except Exception:
        return f"Namaste {name}. I’ve read your chart. What is asking for your attention today?"


def build_placement_rows(chart):
    rows = []
    for i, planet in enumerate(PLANETS):
        try:
            p = chart.d1_chart.planets[i]
            rows.append({
                "planet": planet,
                "sign": p.sign,
                "house": p.house,
                "dignity": p.dignities.dignity,
                "motion": p.motion_type,
                "rules": p.has_lordship_houses,
            })
        except Exception:
            pass
    return rows


def div_summary(chart, key, label):
    """Return a compact divisional chart summary for the astrologer prompt."""
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


def chart_summary(chart):
    """Build the compact chart text fed to the AI."""
    lines = [f"Ascendant (Lagna): {chart.d1_chart.houses[0].sign}"]
    for i, planet in enumerate(PLANETS):
        try:
            p = chart.d1_chart.planets[i]
            extra = ""
            if getattr(p, "conjuncts", None):
                extra += f", with {'+'.join(p.conjuncts)}"
            gives = (getattr(p, "aspects", {}) or {}).get("gives", [])
            if gives:
                houses = ",".join(str(a["to_house"]) for a in gives)
                extra += f", aspects houses {houses}"
            lines.append(f"{planet}: {p.sign} (House {p.house}), {p.dignities.dignity}, "
                         f"{p.motion_type}, rules {p.has_lordship_houses}{extra}")
        except Exception:
            pass
    lines.append(f"Moon Nakshatra: {chart.panchanga.nakshatra}")
    lines.append(current_dasha(chart))
    return "\n".join(lines)


# ---------- AI ----------
def update_memory():
    """Update the durable memory note from the user's recent messages."""
    recent = "\n".join(m["content"] for m in st.session_state.messages[-6:]
                       if m["role"] == "user")
    prompt = f"""You maintain a factual memory note about an astrology app user.

Current note:
{st.session_state.memory or "(empty)"}

New messages:
{recent}

Update the note using ONLY facts the user explicitly stated in their own words.
- Do NOT infer, guess, or embellish.
- If they asked about a topic but stated no fact, record the topic, not a conclusion
  (e.g. "Asked about marriage timing", NOT "Single, seeking love").
- If nothing durable was stated, return the current note unchanged.
- Keep under 120 words. Return ONLY the note."""
    try:
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}])
        st.session_state.memory = resp.choices[0].message.content.strip()
        save_user(st.session_state.username)
    except Exception:
        return


def ask_astrologer(user_text):
    today = datetime.now().strftime("%d %B %Y")   # e.g. "14 July 2026"
    st.session_state.messages.append({"role": "user", "content": user_text})
    with st.chat_message("user"):
        st.write(user_text)

    text_lower = user_text.lower()
    report_instruction = ""
    if "personality report" in text_lower:
        report_instruction = "\nFor reports, use one bold takeaway sentence, then 3 short sections with bold labels and a short closing line."
    elif "career report" in text_lower:
        report_instruction = "\nFor reports, use one bold takeaway sentence, then 3 short sections with bold labels and a short closing line."
    elif "relationship report" in text_lower:
        report_instruction = "\nFor reports, use one bold takeaway sentence, then 3 short sections with bold labels and a short closing line."
    if any(word in text_lower for word in ["marriage", "marry", "spouse", "wife", "husband", "partner", "love", "relationship", "shaadi"]):
        topic_summary = st.session_state.get("d9", "")
        topic_label = "SPECIALISED CHART FOR MARRIAGE / RELATIONSHIPS"
    elif any(word in text_lower for word in ["career", "job", "work", "business", "profession", "promotion", "salary"]):
        topic_summary = st.session_state.get("d10", "")
        topic_label = "SPECIALISED CHART FOR CAREER / WORK"
    else:
        topic_summary = ""
        topic_label = ""

    chart_block = f"""THEIR CHART (FACTS — never change, rename, or invent placements):
{st.session_state.summary}"""
    if topic_summary:
        chart_block += f"\n\n{topic_label}:\n{topic_summary}"

    system_prompt = f"""You are a warm, wise Vedic astrologer speaking with {st.session_state.name}.

TODAY'S DATE: {today}

{chart_block}

WHAT YOU REMEMBER ABOUT THEM:
{st.session_state.memory or "(nothing yet — first conversation)"}

RULES:
- Only use placements listed above. Never invent a sign, house, or placement.
- Only reference past topics in the memory note. If empty, say so — don't invent a backstory.
- If you don't know something, say so plainly.
- No "astrology is just a guide" endings. Be confident and warm, never fatalistic.
- You HAVE house positions, dignities, and current dasha above — use them fully and confidently.
- Answer from the chart with specifics. Don't refuse or claim you lack data that's listed above.
- Your ONLY source of truth is the Vedic chart data above. Base every claim on it.
- If something cannot be derived from that chart data, do not assert it. This includes
  outside systems (numerology, tarot, palmistry) and specifics a chart can't know
  (another person's identity/traits, exact dates of future events).
- When asked something the chart can't answer, say so warmly, then share what the chart
  DOES suggest. Never manufacture a connection or fake confidence to please the user.
- Planets listed "with X" are conjunct — read them as a combination (yoga), not separately.
FORMAT:
{report_instruction}
- Normal answers: 150-200 words. Lead with the direct answer, then 2-3 short bullets.
- No padding or essays.
- Full reports (Personality/Career/Relationship) may be longer, but keep clear sections."""

    messages = [{"role": "system", "content": system_prompt}] + st.session_state.messages
    with st.chat_message("assistant"):
        try:
            stream = client.chat.completions.create(
                model="llama-3.3-70b-versatile", messages=messages, stream=True)
            reply = st.write_stream(
                chunk.choices[0].delta.content or "" for chunk in stream)
        except Exception:
            reply = "The stars seem cloudy right now. Please try again in a moment."
            st.write(reply)
    st.session_state.messages.append({"role": "assistant", "content": reply})
    update_memory()


# ---------- UI ----------
st.title(" Your AI Astrologer")

with st.sidebar:
    if st.session_state.get("username"):
        st.write(f"Signed in as **{st.session_state.username}**")
        if st.button("Log out"):
            for key in list(st.session_state.keys()):
                st.session_state.pop(key, None)
            st.rerun()
    else:
        st.write("Already have an account?")
        if st.button("Log in"):
            login_dialog()


# ---------- MAIN ----------
if "summary" not in st.session_state:
    st.subheader("An AI astrologer that actually remembers you")
    st.markdown("<p class='hero-line'>Your birth chart, read by an astrologer who remembers you.</p>", unsafe_allow_html=True)
    st.write("")

    cards = [
        ("Real chart", "A Vedic reading rooted in your exact birth moment."),
        ("Timing", "The current dasha, clearly shown."),
        ("Memory", "What you asked before, remembered quietly."),
    ]
    for col, (title, body) in zip(st.columns(3), cards):
        col.markdown(f'<div class="card"><h4>{title}</h4><p>{body}</p></div>',
                     unsafe_allow_html=True)
    st.write("")
    st.write("")
    name = st.text_input("Your name", "")
    c1, c2 = st.columns(2)
    dob = c1.date_input("Date of birth", value=datetime(2000, 1, 1),
                        min_value=datetime(1940, 1, 1), max_value=datetime.now())
    tob = c2.time_input("Time of birth", value=datetime(2000, 1, 1, 12, 0).time())
    city_index = _city_options.index("Lucknow, IN") if "Lucknow, IN" in _city_options else 0
    city = st.selectbox("Birth city", options=_city_options, index=city_index)
    st.caption("Even an approximate time works — closer is more accurate.")

    if st.button("Reveal my chart", type="primary"):
        coords = city_to_coords(city)
        if not name:
            st.warning("Please enter your name.")
        elif coords is None:
            st.error("Couldn't find that city. Try just the city name, e.g. 'Lucknow'")
        else:
            reveal_placeholder = st.empty()
            reveal_placeholder.markdown("<div class='hero-line' style='text-align:center; margin-top:1rem;'>Reading the sky at the moment you were born…</div>", unsafe_allow_html=True)
            lat, lon, tzname = coords
            birth_dt = datetime(dob.year, dob.month, dob.day, tob.hour, tob.minute, 0)
            chart = calculate_birth_chart(birth_date=birth_dt, latitude=lat, longitude=lon,
                                          timezone_offset=tz_offset(tzname, birth_dt), name=name)
            time.sleep(1.4)
            reveal_placeholder.empty()
            st.session_state.name = name
            st.session_state.summary = chart_summary(chart)
            st.session_state.chart_svg = render_chart_svg(chart)
            st.session_state.d9 = div_summary(chart, "d9", "D9 / Navamsa")
            st.session_state.d10 = div_summary(chart, "d10", "D10 / Dashamsa")
            st.session_state.birth_date = dob.strftime("%Y-%m-%d")
            st.session_state.birth_time = tob.strftime("%H:%M")
            st.session_state.birth_city = city
            st.session_state.dasha_line = current_dasha(chart)
            st.session_state.placements = build_placement_rows(chart)
            st.session_state.memory = ""
            st.session_state.messages = [{"role": "assistant",
                "content": chart_intro_message(name, chart)}]
            if st.session_state.get("username"):
                save_user(st.session_state.username)
            st.rerun()
else:
    if not st.session_state.get("username"):
        st.warning("Your chart isn't saved yet.")
        if st.button("Save my chart"):
            signup_dialog()

    read_tab, chart_tab = st.tabs(["Reading", "Chart"])

    with read_tab:
        if st.session_state.get("memory"):
            st.markdown(f"<div class='soft-note'>Where we left off: {st.session_state.memory}</div>", unsafe_allow_html=True)

        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.write(msg["content"])

        st.caption("Explore")
        c1, c2, c3 = st.columns(3)
        if c1.button("Personality", use_container_width=False):
            ask_astrologer("Give me a detailed personality report — how I think, my strengths, and my blind spots.")
        if c2.button("Career", use_container_width=False):
            ask_astrologer("Give me a detailed career report — archetype, best paths, work style, challenges, and growth periods ahead.")
        if c3.button("Relationship", use_container_width=False):
            ask_astrologer("Give me a detailed relationship report — my style, ideal partner, challenges, marriage outlook, and key lessons.")

    with chart_tab:
        if st.session_state.get("chart_svg"):
            st.markdown(f"<div style='display:flex; justify-content:center;'>{st.session_state.chart_svg}</div>", unsafe_allow_html=True)

        if st.session_state.get("dasha_line"):
            dasha_parts = st.session_state.dasha_line.split(":", 1)[1].split("->", 1)[0].strip()
            st.markdown(f"<div class='hero-line'><span class='mini-pill'>Dasha</span> You are living your {dasha_parts} period.</div>", unsafe_allow_html=True)

        if st.session_state.get("placements"):
            cols = st.columns(2)
            for idx, item in enumerate(st.session_state.placements):
                with cols[idx % 2]:
                    st.markdown(f"""
                    <div class='placement-card'>
                      <div class='placement-name'>{item['planet']}</div>
                      <div>{item['sign']} · House {item['house']}</div>
                      <div class='placement-meta'>{item['dignity']} · {item['motion']} · rules {item['rules']}</div>
                    </div>
                    """, unsafe_allow_html=True)

        with st.expander("Chart text summary", expanded=False):
            st.text(st.session_state.summary)

    user_text = st.chat_input("Ask your astrologer...")
    if user_text:
        ask_astrologer(user_text)

st.divider()
st.caption("For guidance and reflection. Not a substitute for professional advice.")
