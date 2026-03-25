import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

def get_groq_client():
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise ValueError("GROQ_API_KEY not found. Check your .env file")

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
        max_tokens=500
    )

    return response.choices[0].message.content