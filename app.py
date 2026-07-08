import streamlit as st
import psycopg2
from datetime import datetime
from jyotishganit import calculate_birth_chart
from groq import Groq
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderUnavailable, GeocoderTimedOut

# ---- PASTE YOUR NEW KEY ----
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

PLANETS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]


# ========== DATABASE: the permanent notebook ==========
def get_connection():
    return psycopg2.connect(st.secrets["DB_URL"])


def init_db():
    con = get_connection()
    cur = con.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        name     TEXT,
        summary  TEXT,
        memory   TEXT
    )""")
    con.commit()
    cur.close()
    con.close()

def load_user(username):
    con = get_connection()
    cur = con.cursor()
    cur.execute(
        "SELECT name, summary, memory FROM users WHERE username = %s",
        (username,))
    row = cur.fetchone()
    cur.close()
    con.close()
    return row  # None if new, else (name, summary, memory)

def save_user(username):
    con = get_connection()
    cur = con.cursor()
    cur.execute("""INSERT INTO users (username, name, summary, memory)
                   VALUES (%s, %s, %s, %s)
                   ON CONFLICT (username) DO UPDATE SET
                       name    = EXCLUDED.name,
                       summary = EXCLUDED.summary,
                       memory  = EXCLUDED.memory""",
                (username, st.session_state.name,
                 st.session_state.summary, st.session_state.memory))
    con.commit()
    cur.close()
    con.close()

init_db()


def chart_summary(chart):
    lines = [f"Ascendant (Lagna): {chart.d1_chart.houses[0].sign}"]
    for i, planet in enumerate(PLANETS):
        try:
            lines.append(f"{planet}: {chart.d1_chart.planets[i].sign}")
        except Exception:
            pass
    lines.append(f"Moon Nakshatra: {chart.panchanga.nakshatra}")
    return "\n".join(lines)


geolocator = Nominatim(user_agent="astro-ai")


def city_to_coords(city_name):
    """Turn a city name into (latitude, longitude). Returns None if not found or lookup fails."""
    try:
        location = geolocator.geocode(city_name, timeout=10)
    except (GeocoderUnavailable, GeocoderTimedOut):
        return "unavailable"        # the lookup service itself failed
    if location is None:
        return None                 # city genuinely not found / typo
    return location.latitude, location.longitude


def update_memory():
    recent_text = "\n".join(
        msg["content"] for msg in st.session_state.messages[-6:]
        if msg["role"] == "user")
    prompt = f"""You maintain a factual memory note about an astrology app user.

Current note:
{st.session_state.memory or "(empty)"}

New messages:
{recent_text}

Update the note using ONLY facts the user explicitly stated in their own words.

STRICT RULES:
- Do NOT infer, guess, assume, or embellish. No flattering additions.
- If they asked about a topic but stated no fact, record the topic, not a conclusion.
  (e.g. they asked about marriage timing → "Asked about marriage timing",
   NOT "Single, seeking love".)
- Do not invent life events, feelings, or status. No empty slots to fill.
- If nothing durable was stated, return the current note unchanged.
- Keep under 120 words. Return ONLY the note."""
    resp = client.chat.completions.create(
        model="llama-3.1-8b-instant",                  # cheap fast model for the note
        messages=[{"role": "user", "content": prompt}])
    st.session_state.memory = resp.choices[0].message.content.strip()
    save_user(st.session_state.username)               # write it to the drawer


def ask_astrologer(user_text):
    st.session_state.messages.append({"role": "user", "content": user_text})
    with st.chat_message("user"):
        st.write(user_text)

    system_prompt = f"""You are a warm, wise Vedic astrologer speaking with {st.session_state.name}.

THE USER'S ACTUAL CHART (these are FACTS — never change, rename, or invent placements):
{st.session_state.summary}

WHAT YOU ACTUALLY REMEMBER ABOUT THEM:
{st.session_state.memory or "(nothing yet — this is your first real conversation)"}

STRICT RULES:
- Only refer to placements listed in the chart above. If a planet isn't listed, do NOT mention it.
- Never invent a sign, house, or placement. Accuracy matters more than sounding poetic.
- Only reference past topics that appear in your memory note above. If the memory is empty,
  honestly say you don't have much history yet — do NOT make up a backstory.
- If you don't know something, say so plainly. Never fill gaps with invented details.
-No repetitive "astrology is just a guide" endings.
Confident and warm, but not fatalistic (no doom-predicting)
Speak in simple, warm, encouraging language. Explain what placements mean. Be human, never robotic."""

    full_messages = [{"role": "system", "content": system_prompt}] + st.session_state.messages
    with st.chat_message("assistant"):
        with st.spinner("Reading the stars..."):
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile", messages=full_messages)
            reply = response.choices[0].message.content
            st.write(reply)
    st.session_state.messages.append({"role": "assistant", "content": reply})
    update_memory()                                    # remember this for next time


st.title("🔮 Your AI Astrologer")

# ========== SIDEBAR: login or sign up ==========
with st.sidebar:
    st.header("Login")
    username = st.text_input("Your username", "")

    if st.button("Login / Continue"):
        if username.strip() == "":
            st.warning("Please type a username.")
        else:
            row = load_user(username)
            if row:                                    # ---- returning user ----
                name, summary, memory = row
                st.session_state.username = username
                st.session_state.name = name
                st.session_state.summary = summary
                st.session_state.memory = memory or ""
                st.session_state.messages = [
                    {"role": "assistant",
                     "content": f"Welcome back, {name} 🙏 I remember our past chats. What's on your mind today?"}]
                st.session_state.new_user = False
            else:                                      # ---- new user ----
                st.session_state.new_user = True
                st.session_state.pending_username = username

    # New user fills birth details once
    if st.session_state.get("new_user"):
        st.divider()
        st.subheader("New here — your birth details")
        name = st.text_input("Name", "Yash")
        dob  = st.date_input("Date of birth", value=datetime(2000, 1, 1),
                             min_value=datetime(1940, 1, 1), max_value=datetime.now())
        tob  = st.time_input("Time of birth", value=datetime(2000, 1, 1, 12, 0).time())
        city = st.text_input("Birth city", "Lucknow, India")

        if st.button("Create my chart"):
            coords = city_to_coords(city)          # look up the city → coordinates

            if coords is None:                     # city not found → stop & tell them
                st.error("Couldn't find that city 😕 Try adding the country, e.g. 'Lucknow, India'")
            else:
                lat, lon = coords                  # unpack the pair into two variables
                birth_dt = datetime(dob.year, dob.month, dob.day, tob.hour, tob.minute, 0)
                chart = calculate_birth_chart(
                    birth_date=birth_dt, latitude=lat, longitude=lon,
                    timezone_offset=5.5, name=name)
                st.session_state.username = st.session_state.pending_username
                st.session_state.name = name
                st.session_state.summary = chart_summary(chart)
                st.session_state.memory = ""
                st.session_state.messages = [
                    {"role": "assistant",
                     "content": f"Namaste {name} 🙏 I've read your chart. Ask me anything."}]
                st.session_state.new_user = False
                save_user(st.session_state.username)      # create them in the database


# ========== MAIN AREA: the chat ==========
if "summary" not in st.session_state:
    st.info("👈 Type a username and click **Login / Continue** to begin.")
else:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    col1, col2, col3 = st.columns(3)
    if col1.button("🧠 Personality"):
        ask_astrologer("Give me a detailed personality report based on my chart — how I think, my strengths, and my blind spots.")
    if col2.button("💼 Career"):
        ask_astrologer("Give me a detailed career report based on my chart. Cover my career archetype, best career paths, work style, biggest career challenges, and any strong growth periods ahead.")
    if col3.button("❤️ Relationship"):
        ask_astrologer("Give me a detailed relationship report based on my chart. Cover my relationship style, what partner suits me, my relationship challenges, marriage outlook, and key love lessons.")

    user_text = st.chat_input("Ask your astrologer...")
    if user_text:
        ask_astrologer(user_text)
