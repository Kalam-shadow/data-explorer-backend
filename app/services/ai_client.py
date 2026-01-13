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
# from google import genai
import os
import requests
import json
import logging

load_dotenv()
logger = logging.getLogger(__name__)


# New: OpenRouter configuration (uses GEMINI_KEY from .env per your request)
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "qwen/qwen3-coder:free")

def generate_sql(prompt: str) -> str:
    """
    Select provider by env AI_PROVIDER (OPENROUTER or GEMINI).
    OPENROUTER uses the GEMINI_KEY env var as the bearer token per your request.
    """ 
    # provider = os.getenv("AI_PROVIDER", "GEMINI").upper()

    api_key = os.getenv("OPENROUTER_KEY")
    if not api_key:
        raise ValueError("OPENROUTER key not set in env var")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        # Optional headers for openrouter rankings/metadata can be set via env if needed
    }
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
    try:
        resp = requests.post(
            OPENROUTER_URL,
            headers=headers,
            data=json.dumps(payload),
            timeout=60
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.Timeout: 
        raise RuntimeError("OpenRouter request timed out after 60s") 
    except requests.exceptions.RequestException as e: 
        raise RuntimeError(f"OpenRouter request failed: {e}")
    
    # logger.info("OpenRouter response data: %s", data)

    # Robust extraction for various possible response shapes
    text = None
    choices = data.get("choices") if isinstance(data, dict) else None
    if choices and len(choices) > 0:
        first = choices[0]
        # OpenRouter/OpenAI style: choice.message.content
        if isinstance(first.get("message"), dict):
            text = first["message"].get("content")
        # Some responses use 'text' or 'content' fields
        text = text or first.get("text") or first.get("content")

    # fallbacks
    text = text or data.get("response") or data.get("output") or data.get("text")
    if not text:
        raise ValueError(f"Empty response from OpenRouter: {data}")
    return text.strip()
    
    # Default to Gemini client behavior (existing code)
    # client = genai.Client(api_key=os.getenv("GEMINI_KEY"))

    # response = client.models.generate_content(
    #     model="gemini-2.5-flash",
    #     contents=prompt
    # )

    # # Gemini returns text directly
    # if not response.text:
    #     raise ValueError("Empty response from Gemini")

    # return response.text.strip()
