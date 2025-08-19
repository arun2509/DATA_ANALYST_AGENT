# openai_llm.py
import os
from openai import OpenAI
from dotenv import load_dotenv

# Load API key and base URL from .env
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("OPENAI_BASE_URL")  # optional

# Initialize OpenAI client
client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)

def query_openai(prompt: str, model: str = "gpt-4o-mini") -> str:
    """
    Query OpenAI and return generated Python code or text.
    """
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a helpful Python data analysis assistant."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content
