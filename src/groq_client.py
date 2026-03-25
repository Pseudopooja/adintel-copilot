import os
from groq import Groq


def get_groq_client():
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise ValueError("GROQ_API_KEY not found. Check your environment or Streamlit secrets.")

    return Groq(api_key=api_key)


def generate_response(prompt):
    client = get_groq_client()

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": "You are a marketing analytics copilot."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.4,
        max_completion_tokens=450
    )

    return response.choices[0].message.content
