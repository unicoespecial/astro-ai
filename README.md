# AI Astrologer

A Streamlit-based AI astrologer app that reads a Vedic birth chart from birth details and offers a conversational reading experience.

## Run locally

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Deploy from GitHub

Pushing the code to GitHub stores it; to run the app, deploy it on [Streamlit Community Cloud](https://share.streamlit.io/):

1. Push this repository to GitHub.
2. In Streamlit Community Cloud, choose **Create app**, select this repository and branch, and set the main file to `app.py`.
3. Deploy. The chart calculator works without secrets.
4. To enable AI readings, open the app's **Settings → Secrets** and add:

   ```toml
   GROQ_API_KEY = "your-groq-api-key"
   ```

5. To enable saved accounts and chart memory, add a PostgreSQL connection URL too:

   ```toml
   DB_URL = "postgresql://user:password@host:5432/database?sslmode=require"
   ```

   Use a hosted PostgreSQL database and keep both values in Streamlit secrets. The app can run without `DB_URL`; account saving and login stay unavailable until it is set. Never commit real keys or database credentials to GitHub.

Do not commit secrets to GitHub. The local `.streamlit/secrets.toml` file is ignored by Git.
