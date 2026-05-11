import os

import streamlit as st
from dotenv import load_dotenv
from google import genai


def generate_with_gemini(prompt):
    load_dotenv()

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        st.error("GEMINI_API_KEY not found. Check your .env file.")
        return None

    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    return response.text