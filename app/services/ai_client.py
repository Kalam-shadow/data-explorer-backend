# import requests

# OLLAMA_URL = "http://localhost:11434/api/generate"
# MODEL = "llama3"  # change if needed

# def generate_sql(prompt: str) -> str:
#     response = requests.post(
#         OLLAMA_URL,
#         json={
#             "model": MODEL,
#             "prompt": prompt,
#             "stream": False
#         },
#         timeout=30
#     )
#     response.raise_for_status()
#     return response.json()["response"].strip()

from dotenv import load_dotenv
from google import genai
import os

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_KEY"))

def generate_sql(prompt: str) -> str:
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    # Gemini returns text directly
    if not response.text:
        raise ValueError("Empty response from Gemini")

    return response.text.strip()
