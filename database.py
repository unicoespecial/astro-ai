import psycopg2
import streamlit as st


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


def load_user(username):
    con = get_connection()
    cur = con.cursor()
    cur.execute(
        "SELECT name, summary, memory, password_hash, birth_date, birth_time, birth_city FROM users WHERE username = %s",
        (username,),
    )
    row = cur.fetchone()
    con.close()
    return row


def save_user(username, password_hash=None):
    con = get_connection()
    cur = con.cursor()
    birth_date = st.session_state.get("birth_date", "")
    birth_time = st.session_state.get("birth_time", "")
    birth_city = st.session_state.get("birth_city", "")
    if password_hash:
        cur.execute(
            """INSERT INTO users (username, name, summary, memory, password_hash, birth_date, birth_time, birth_city)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (username) DO UPDATE SET
                name = EXCLUDED.name, summary = EXCLUDED.summary,
                memory = EXCLUDED.memory, password_hash = EXCLUDED.password_hash,
                birth_date = EXCLUDED.birth_date, birth_time = EXCLUDED.birth_time,
                birth_city = EXCLUDED.birth_city""",
            (
                username,
                st.session_state.name,
                st.session_state.summary,
                st.session_state.memory,
                password_hash,
                birth_date,
                birth_time,
                birth_city,
            ),
        )
    else:
        cur.execute(
            """INSERT INTO users (username, name, summary, memory, birth_date, birth_time, birth_city)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (username) DO UPDATE SET
                name = EXCLUDED.name, summary = EXCLUDED.summary, memory = EXCLUDED.memory,
                birth_date = EXCLUDED.birth_date, birth_time = EXCLUDED.birth_time,
                birth_city = EXCLUDED.birth_city""",
            (
                username,
                st.session_state.name,
                st.session_state.summary,
                st.session_state.memory,
                birth_date,
                birth_time,
                birth_city,
            ),
        )
    con.commit()
    con.close()
