import logging

import psycopg2
import streamlit as st


logger = logging.getLogger(__name__)


def is_configured():
    """Return whether a database URL has been configured in Streamlit secrets."""
    return bool(st.secrets.get("DB_URL", ""))


def get_connection():
    database_url = st.secrets.get("DB_URL")
    if not database_url:
        raise RuntimeError("Database is not configured. Add DB_URL to Streamlit secrets.")
    return psycopg2.connect(database_url, connect_timeout=5)


def _close_connection(connection):
    if connection is not None:
        try:
            connection.close()
        except Exception:
            logger.debug("Unable to close database connection", exc_info=True)


def init_db() -> bool:
    connection = None
    try:
        connection = get_connection()
        with connection.cursor() as cur:
            cur.execute("""CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY, name TEXT, summary TEXT, memory TEXT,
                password_hash TEXT)""")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash TEXT")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS birth_date TEXT")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS birth_time TEXT")
            cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS birth_city TEXT")
        connection.commit()
        return True
    except Exception:
        logger.exception("Unable to initialize the database")
        if connection is not None:
            try:
                connection.rollback()
            except Exception:
                pass
        return False
    finally:
        _close_connection(connection)


def load_user(username):
    connection = None
    try:
        connection = get_connection()
        with connection.cursor() as cur:
            cur.execute(
                "SELECT name, summary, memory, password_hash, birth_date, birth_time, birth_city FROM users WHERE username = %s",
                (username,),
            )
            return cur.fetchone()
    except Exception:
        logger.exception("Unable to load user %r", username)
        return None
    finally:
        _close_connection(connection)


def save_user(username, password_hash=None):
    connection = None
    birth_date = st.session_state.get("birth_date", "")
    birth_time = st.session_state.get("birth_time", "")
    birth_city = st.session_state.get("birth_city", "")
    name = st.session_state.get("name", "")
    summary = st.session_state.get("summary", "")
    memory = st.session_state.get("memory", "")
    try:
        connection = get_connection()
        with connection.cursor() as cur:
            if password_hash:
                # Password creation must never overwrite an existing account.
                cur.execute(
                    """INSERT INTO users (username, name, summary, memory, password_hash, birth_date, birth_time, birth_city)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (username) DO NOTHING""",
                    (
                        username,
                        name,
                        summary,
                        memory,
                        password_hash,
                        birth_date,
                        birth_time,
                        birth_city,
                    ),
                )
                if cur.rowcount == 0:
                    connection.rollback()
                    return False
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
                        name,
                        summary,
                        memory,
                        birth_date,
                        birth_time,
                        birth_city,
                    ),
                )
        connection.commit()
        return True
    except Exception:
        logger.exception("Unable to save user %r", username)
        if connection is not None:
            try:
                connection.rollback()
            except Exception:
                pass
        return False
    finally:
        _close_connection(connection)
