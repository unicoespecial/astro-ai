import bcrypt
import streamlit as st

from database import load_user, save_user


def hash_password(password):
    """Scramble a password for storage. One-way — cannot be unscrambled."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def check_password(password, stored_hash):
    """Does the typed password match the stored scramble?"""
    if not stored_hash:
        return False
    return bcrypt.checkpw(password.encode(), stored_hash.encode())


@st.dialog("Save your chart")
def signup_dialog():
    st.write("Save your chart so your astrologer remembers you.")
    username = st.text_input("Choose a username").strip()
    password = st.text_input("Choose a password (8+ characters)", type="password")
    if st.button("Save my chart"):
        if not username or len(password) < 8:
            st.warning("Username required, password must be 8+ characters.")
        elif load_user(username):
            st.error("That username is taken.")
        else:
            st.session_state.username = username
            save_user(username, hash_password(password))
            st.rerun()


@st.dialog("Welcome back")
def login_dialog():
    username = st.text_input("Username").strip()
    password = st.text_input("Password", type="password")
    if st.button("Open my chart"):
        row = load_user(username)
        if not row or not check_password(password, row[3]):
            st.error("Wrong username or password.")
        else:
            saved_name, summary, memory, _, birth_date, birth_time, birth_city = row
            st.session_state.username = username
            st.session_state.name = saved_name
            st.session_state.summary = summary
            st.session_state.memory = memory or ""
            st.session_state.birth_date = birth_date or ""
            st.session_state.birth_time = birth_time or ""
            st.session_state.birth_city = birth_city or ""
            st.session_state.messages = [
                {
                    "role": "assistant",
                    "content": f"Welcome back, {saved_name}. What's on your mind today?",
                }
            ]
            st.rerun()
