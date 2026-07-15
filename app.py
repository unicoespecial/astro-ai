import streamlit as st
import psycopg2
from datetime import datetime
from jyotishganit import calculate_birth_chart
from groq import Groq
import geonamescache

st.set_page_config(page_title="AI Astrologer", page_icon="🔮", layout="centered")

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
_cities = geonamescache.GeonamesCache().get_cities()


# ---------- DATABASE ----------
def get_connection():
    return psycopg2.connect(st.secrets["DB_URL"])


def init_db():
    con = get_connection()
    con.cursor().execute("""CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY, name TEXT, summary TEXT, memory TEXT)""")
    con.commit()
    con.close()


def load_user(username):
    con = get_connection()
    cur = con.cursor()
    cur.execute("SELECT name, summary, memory FROM users WHERE username = %s", (username,))
    row = cur.fetchone()
    con.close()
    return row  # None if new, else (name, summary, memory)


def save_user(username):
    con = get_connection()
    con.cursor().execute("""INSERT INTO users (username, name, summary, memory)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (username) DO UPDATE SET
            name = EXCLUDED.name, summary = EXCLUDED.summary, memory = EXCLUDED.memory""",
        (username, st.session_state.name, st.session_state.summary, st.session_state.memory))
    con.commit()
    con.close()


init_db()


# ---------- CHART HELPERS ----------
def city_to_coords(city_name):
    """City name -> (lat, lon) from an offline list. None if not found."""
    query = city_name.split(",")[0].strip().lower()
    for city in _cities.values():
        if city["name"].lower() == query:
            return city["latitude"], city["longitude"]
    return None


def current_dasha(chart):
    """Return the planetary period active today, e.g. 'Rahu -> Venus'."""
    now = datetime.now()

    def active(periods):
        for planet, data in periods.items():
            if data["start"] <= now <= data["end"]:
                return planet, data
        return None, None

    try:
        maha, maha_data = active(chart.dashas)
        if not maha:
            return "Current period: unknown"
        line = f"Current Mahadasha: {maha}"
        if "antardashas" in maha_data:
            antar, _ = active(maha_data["antardashas"])
            if antar:
                line += f" -> Antardasha: {antar}"
        return line
    except Exception:
        return "Current period: unavailable"


def chart_summary(chart):
    """Build the compact chart text fed to the AI."""
    lines = [f"Ascendant (Lagna): {chart.d1_chart.houses[0].sign}"]
    for i, planet in enumerate(PLANETS):
        try:
            p = chart.d1_chart.planets[i]
            lines.append(f"{planet}: {p.sign} (House {p.house}), {p.dignities.dignity}, {p.motion_type}")
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
    resp = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}])
    st.session_state.memory = resp.choices[0].message.content.strip()
    save_user(st.session_state.username)


def ask_astrologer(user_text):
    today = datetime.now().strftime("%d %B %Y")   # e.g. "14 July 2026"
    st.session_state.messages.append({"role": "user", "content": user_text})
    with st.chat_message("user"):
        st.write(user_text)
    
    system_prompt = f"""You are a warm, wise Vedic astrologer speaking with {st.session_state.name}.

TODAY'S DATE: {today}

THEIR CHART (FACTS — never change, rename, or invent placements):
{st.session_state.summary}

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
FORMAT:
- Normal answers: 150-200 words. Lead with the direct answer, then 2-3 short bullets.
- No padding or essays.
- Full reports (Personality/Career/Relationship) may be longer, but keep clear sections."""

    messages = [{"role": "system", "content": system_prompt}] + st.session_state.messages
    with st.chat_message("assistant"):
        with st.spinner("Reading the stars..."):
            reply = client.chat.completions.create(
                model="llama-3.3-70b-versatile", messages=messages
            ).choices[0].message.content
            st.write(reply)
    st.session_state.messages.append({"role": "assistant", "content": reply})
    update_memory()


# ---------- UI ----------
st.title("🔮 Your AI Astrologer")

with st.sidebar:
    st.header("Sign in")
    username = st.text_input("Username", "", help="Your unique ID — use the same one to return").strip()

    # Only show birth details if they're likely new
    with st.expander("New here? Add your birth details", expanded=False):
        name = st.text_input("Your name", "")
        dob = st.date_input("Date of birth", value=datetime(2000, 1, 1),
                            min_value=datetime(1940, 1, 1), max_value=datetime.now())
        tob = st.time_input("Time of birth", value=datetime(2000, 1, 1, 12, 0).time())
        city = st.text_input("Birth city", "Lucknow, India")
        st.caption("Exact birth time gives the most accurate reading.")

    if st.button("Start / Continue", type="primary", use_container_width=True):
        if username == "":
            st.warning("Please enter a username.")
        else:
            row = load_user(username)
            if row:  # returning user
                _old, summary, memory = row
                st.session_state.username = username
                st.session_state.name = name if name else _old
                st.session_state.summary = summary
                st.session_state.memory = memory or ""
                st.session_state.messages = [{"role": "assistant",
                    "content": f"Welcome back, {st.session_state.name} 🙏 What's on your mind today?"}]
            else:  # new user
                if not name:
                    st.warning("Please add your birth details above.")
                else:
                    coords = city_to_coords(city)
                    if coords is None:
                        st.error("Couldn't find that city 😕 Try just the city name, e.g. 'Lucknow'")
                    else:
                        lat, lon = coords
                        birth_dt = datetime(dob.year, dob.month, dob.day, tob.hour, tob.minute, 0)
                        chart = calculate_birth_chart(birth_date=birth_dt, latitude=lat,
                                                      longitude=lon, timezone_offset=5.5, name=name)
                        st.session_state.username = username
                        st.session_state.name = name
                        st.session_state.summary = chart_summary(chart)
                        st.session_state.memory = ""
                        st.session_state.messages = [{"role": "assistant",
                            "content": f"Namaste {name} 🙏 I've read your chart. Ask me anything."}]
                        save_user(username)


# ---------- MAIN ----------
if "summary" not in st.session_state:
    # LANDING SCREEN for new visitors
    st.subheader("An AI astrologer that actually remembers you")
    st.write("""
    Enter your birth details once. Your real Vedic chart is calculated, and you can
    ask anything — career, love, timing, what to focus on right now.
    """)
    col1, col2, col3 = st.columns(3)
    col1.info("🪐 **Real chart**\n\nSidereal Vedic calculations, not generic horoscopes.")
    col2.info("⏳ **Timing**\n\nKnows your current planetary period (dasha).")
    col3.info("🧠 **Memory**\n\nRemembers your goals and worries between visits.")
    st.info("👈 Enter a username and your birth details to begin.")
else:
    # Show their chart — the "wow" moment
    with st.expander("🪐 Your birth chart"):
        st.code(st.session_state.summary)

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    c1, c2, c3 = st.columns(3)
    if c1.button("🧠 Personality", use_container_width=True):
        ask_astrologer("Give me a detailed personality report — how I think, my strengths, and my blind spots.")
    if c2.button("💼 Career", use_container_width=True):
        ask_astrologer("Give me a detailed career report — archetype, best paths, work style, challenges, and growth periods ahead.")
    if c3.button("❤️ Relationship", use_container_width=True):
        ask_astrologer("Give me a detailed relationship report — my style, ideal partner, challenges, marriage outlook, and key lessons.")

    user_text = st.chat_input("Ask your astrologer...")
    if user_text:
        ask_astrologer(user_text)

st.divider()
st.caption("For guidance and reflection. Not a substitute for professional advice.")
