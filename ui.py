import streamlit as st

from auth import login_dialog, signup_dialog
from chart import chart_intro_message, chart_summary, build_placement_rows, current_dasha, div_summary
from database import save_user
from memory import update_memory
from prompts import build_chart_block, build_report_instruction, build_system_prompt, build_topic_context
from renderer import render_chart_svg


def render_sidebar():
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


def render_landing_page():
    st.subheader("An AI astrologer that actually remembers you")
    st.markdown("<p class='hero-line'>Your birth chart, read by an astrologer who remembers you.</p>", unsafe_allow_html=True)
    st.write("")

    cards = [
        ("Real chart", "A Vedic reading rooted in your exact birth moment."),
        ("Timing", "The current dasha, clearly shown."),
        ("Memory", "What you asked before, remembered quietly."),
    ]
    for column, (title, body) in zip(st.columns(3), cards):
        column.markdown(f'<div class="card"><h4>{title}</h4><p>{body}</p></div>', unsafe_allow_html=True)
    st.write("")
    st.write("")


def render_reading_view(client):
    if st.session_state.get("memory"):
        st.markdown(f"<div class='soft-note'>Where we left off: {st.session_state.memory}</div>", unsafe_allow_html=True)

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    st.caption("Explore")
    report_prompts = {
        "Personality": "Give me a detailed personality report — how I think, my strengths, and my blind spots.",
        "Career": "Give me a detailed career report — archetype, best paths, work style, challenges, and growth periods ahead.",
        "Relationship": "Give me a detailed relationship report — my style, ideal partner, challenges, marriage outlook, and key lessons.",
    }
    if "active_report" not in st.session_state:
        st.session_state.active_report = None

    selected_report = st.pills(
        "",
        options=list(report_prompts.keys()),
        selection_mode="single",
        default=None,
    )
    if selected_report and selected_report != st.session_state.active_report:
        st.session_state.active_report = selected_report
        ask_astrologer(client, report_prompts[selected_report])
    elif not selected_report:
        st.session_state.active_report = None


def render_chart_view():
    if st.session_state.get("chart_svg"):
        st.markdown(f"<div style='display:flex; justify-content:center;'>{st.session_state.chart_svg}</div>", unsafe_allow_html=True)

    if st.session_state.get("dasha_line"):
        dasha_parts = st.session_state.dasha_line.split(":", 1)[1].split("->", 1)[0].strip()
        st.markdown(f"<div class='hero-line'><span class='mini-pill'>Dasha</span> You are living your {dasha_parts} period.</div>", unsafe_allow_html=True)

    if st.session_state.get("placements"):
        cols = st.columns(2)
        for index, item in enumerate(st.session_state.placements):
            with cols[index % 2]:
                st.markdown(
                    f"""
                    <div class='placement-card'>
                      <div class='placement-name'>{item['planet']}</div>
                      <div>{item['sign']} · House {item['house']}</div>
                      <div class='placement-meta'>{item['dignity']} · {item['motion']} · rules {item['rules']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    with st.expander("Chart text summary", expanded=False):
        st.text(st.session_state.summary)


def ask_astrologer(client, user_text):
    today = st.session_state.get("today") or ""
    if not today:
        from datetime import datetime
        today = datetime.now().strftime("%d %B %Y")
        st.session_state.today = today

    st.session_state.messages.append({"role": "user", "content": user_text})
    with st.chat_message("user"):
        st.write(user_text)

    report_instruction = build_report_instruction(user_text)
    topic_summary, topic_label = build_topic_context(user_text, st.session_state.get("d9", ""), st.session_state.get("d10", ""))
    chart_block = build_chart_block(st.session_state.summary, topic_summary, topic_label)
    system_prompt = build_system_prompt(st.session_state.name, today, chart_block, st.session_state.memory, report_instruction)

    messages = [{"role": "system", "content": system_prompt}] + st.session_state.messages
    with st.chat_message("assistant"):
        try:
            stream = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                stream=True,
            )
            reply = st.write_stream(chunk.choices[0].delta.content or "" for chunk in stream)
        except Exception:
            reply = "The stars seem cloudy right now. Please try again in a moment."
            st.write(reply)
    st.session_state.messages.append({"role": "assistant", "content": reply})
    update_memory(client)


def render_auth_prompt():
    if not st.session_state.get("username"):
        st.warning("Your chart isn't saved yet.")
        if st.button("Save my chart"):
            signup_dialog()
