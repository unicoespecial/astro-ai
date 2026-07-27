import time
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
from database import init_db, save_user
from renderer import render_chart_svg
from styles import STYLES
from ui import ask_astrologer, render_auth_prompt, render_chart_view, render_landing_page, render_reading_view, render_sidebar

st.set_page_config(page_title="AI Astrologer", page_icon="🔮", layout="centered")
st.markdown(STYLES, unsafe_allow_html=True)

client = Groq(api_key=st.secrets["GROQ_API_KEY"])
_cities = geonamescache.GeonamesCache().get_cities()
_city_options = build_city_options(_cities)

init_db()

st.title(" Your AI Astrologer")
render_sidebar()

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
            lat, lon, tzname = coords
            birth_dt = datetime(dob.year, dob.month, dob.day, tob.hour, tob.minute, 0)
            chart = build_birth_chart(
                birth_date=birth_dt,
                latitude=lat,
                longitude=lon,
                timezone_offset=tz_offset(tzname, birth_dt),
                name=name,
            )
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
            st.session_state.messages = [{"role": "assistant", "content": chart_intro_message(name, chart)}]
            if st.session_state.get("username"):
                save_user(st.session_state.username)
            st.rerun()
else:
    render_auth_prompt()
    read_tab, chart_tab = st.tabs(["Reading", "Chart"])

    with read_tab:
        render_reading_view(client)

    with chart_tab:
        render_chart_view()

    user_text = st.chat_input("Ask your astrologer...")
    if user_text:
        ask_astrologer(client, user_text)

st.divider()
st.caption("For guidance and reflection. Not a substitute for professional advice.")
