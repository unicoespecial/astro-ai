from datetime import datetime

import geonamescache
import streamlit as st
from groq import Groq

from auth import login_dialog, signup_dialog
from chart import (
    build_birth_chart,
    build_city_options,
    build_placement_rows,
    chart_intro_message,
    chart_summary,
    city_to_coords,
    current_dasha,
    div_summary,
    tz_offset,
)
from database import init_db, is_configured, save_user
from renderer import render_chart_svg
from styles import STYLES
from ui import ask_astrologer, render_auth_prompt, render_chart_view, render_landing_page, render_reading_view, render_sidebar

st.set_page_config(page_title="AI Astrologer", page_icon="🔮", layout="centered")
st.markdown(STYLES, unsafe_allow_html=True)

groq_api_key = st.secrets.get("GROQ_API_KEY", "")
try:
    client = Groq(api_key=groq_api_key) if groq_api_key else None
except Exception:
    client = None
_cities = geonamescache.GeonamesCache().get_cities()
_city_options = build_city_options(_cities)

database_available = bool(is_configured() and init_db())
st.session_state.database_available = database_available

st.title(" Your AI Astrologer")
render_sidebar()
if is_configured() and not database_available:
    st.warning("Saved accounts are temporarily unavailable because the database connection failed. You can still create and view a chart.")

if "summary" not in st.session_state:
    render_landing_page()
    name = st.text_input("Your name", "")
    left_column, right_column = st.columns(2)
    dob = left_column.date_input(
        "Date of birth",
        value=datetime(2000, 1, 1),
        min_value=datetime(1940, 1, 1),
        max_value=datetime.now(),
    )
    tob = right_column.time_input("Time of birth", value=datetime(2000, 1, 1, 12, 0).time())
    city_index = _city_options.index("Lucknow, IN") if "Lucknow, IN" in _city_options else 0
    city = st.selectbox("Birth city", options=_city_options, index=city_index)
    st.caption("Even an approximate time works — closer is more accurate.")

    if st.button("Reveal my chart", type="primary"):
        coords = city_to_coords(city, _cities)
        if not name:
            st.warning("Please enter your name.")
        elif coords is None:
            st.error("Couldn't find that city. Try just the city name, e.g. 'Lucknow'")
        else:
            reveal_placeholder = st.empty()
            reveal_placeholder.markdown("<div class='hero-line' style='text-align:center; margin-top:1rem;'>Reading the sky at the moment you were born…</div>", unsafe_allow_html=True)
            try:
                lat, lon, tzname = coords
                birth_dt = datetime(dob.year, dob.month, dob.day, tob.hour, tob.minute, 0)
                chart = build_birth_chart(
                    birth_date=birth_dt,
                    latitude=lat,
                    longitude=lon,
                    timezone_offset=tz_offset(tzname, birth_dt),
                    name=name,
                )
                summary = chart_summary(chart)
                chart_svg = render_chart_svg(chart)
                d9 = div_summary(chart, "d9", "D9 / Navamsa")
                d10 = div_summary(chart, "d10", "D10 / Dashamsa")
                dasha_line = current_dasha(chart)
                placements = build_placement_rows(chart)
                intro_message = chart_intro_message(name, chart)
            except Exception:
                reveal_placeholder.empty()
                st.error("Chart generation is temporarily unavailable. Please try again.")
            else:
                reveal_placeholder.empty()
                st.session_state.name = name
                st.session_state.summary = summary
                st.session_state.chart_svg = chart_svg
                st.session_state.d9 = d9
                st.session_state.d10 = d10
                st.session_state.birth_date = dob.strftime("%Y-%m-%d")
                st.session_state.birth_time = tob.strftime("%H:%M")
                st.session_state.birth_city = city
                st.session_state.dasha_line = dasha_line
                st.session_state.placements = placements
                st.session_state.memory = ""
                st.session_state.messages = [{"role": "assistant", "content": intro_message}]
                if st.session_state.get("username") and not save_user(st.session_state.username):
                    st.warning("Your chart is ready, but it could not be saved right now.")
                st.rerun()
else:
    render_auth_prompt()
    read_tab, chart_tab = st.tabs(["Reading", "Chart"])

    with read_tab:
        if client is None:
            st.info("AI readings are off until you add GROQ_API_KEY to your app secrets.")
        render_reading_view(client)

    with chart_tab:
        render_chart_view()

    user_text = st.chat_input("Ask your astrologer...", disabled=client is None)
    if user_text:
        ask_astrologer(client, user_text)

st.divider()
st.caption("For guidance and reflection. Not a substitute for professional advice.")
