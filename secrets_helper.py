import os
from dotenv import load_dotenv

load_dotenv()


def get_secret(key):
    """Reads a secret from Streamlit Cloud's st.secrets if available,
    otherwise falls back to a local .env file via os.getenv.
    This lets the same code run unchanged both locally and on
    Streamlit Community Cloud, where .env files don't exist."""
    try:
        import streamlit as st
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.getenv(key)