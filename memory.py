import streamlit as st

from database import save_user


def update_memory(client):
    recent = "\n".join(
        message["content"]
        for message in st.session_state.messages[-6:]
        if message["role"] == "user"
    )
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
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
        )
        st.session_state.memory = response.choices[0].message.content.strip()
        save_user(st.session_state.username)
    except Exception:
        return
