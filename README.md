# AI Astrologer

A Streamlit-based AI astrologer app that reads a Vedic birth chart from birth details and offers a conversational reading experience.

## Run locally

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Deploy to Streamlit Cloud

1. Create a GitHub repository and push this project.
2. In Streamlit Cloud, create a new app from that repository.
3. Set the main file to `app.py`.
4. Add these secrets in Streamlit Cloud:
   - `GROQ_API_KEY`
   - `DB_URL`

Do not commit secrets to GitHub. The local `.streamlit/secrets.toml` file is ignored by Git.
