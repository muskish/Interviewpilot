import os
from dotenv import load_dotenv
import httpx

load_dotenv()
api_key = os.getenv("GROQ_API_KEY")

response = httpx.post(
    "https://api.groq.com/openai/v1/chat/completions",
    headers={"Authorization": f"Bearer {api_key}"},
    json={
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 1,
    },
)

print("=== ALL GROQ RATE LIMIT HEADERS ===")
for k, v in response.headers.items():
    if k.lower().startswith("x-ratelimit"):
        print(f"{k:32s}: {v}")
