"""
Run this once, before Phase 2, to confirm your API key and model name work:

    python test_api_connection.py

It does NOT use LangChain — deliberately a raw provider call, so a failure
here means "your key/model is wrong," not "something in our agent code is
wrong." Isolate that variable before we build on top of it.
"""

from config import settings


def test_groq() -> None:
    from groq import Groq

    client = Groq(api_key=settings.require_api_key())
    resp = client.chat.completions.create(
        model=settings.llm_model,
        messages=[{"role": "user", "content": "Reply with exactly: pong"}],
        max_tokens=10,
    )
    print("Response:", resp.choices[0].message.content)


def test_openai() -> None:
    from openai import OpenAI

    client = OpenAI(api_key=settings.require_api_key())
    resp = client.chat.completions.create(
        model=settings.llm_model,
        messages=[{"role": "user", "content": "Reply with exactly: pong"}],
        max_tokens=10,
    )
    print("Response:", resp.choices[0].message.content)


def test_anthropic() -> None:
    from anthropic import Anthropic

    client = Anthropic(api_key=settings.require_api_key())
    resp = client.messages.create(
        model=settings.llm_model,
        max_tokens=10,
        messages=[{"role": "user", "content": "Reply with exactly: pong"}],
    )
    print("Response:", resp.content[0].text)


def test_ollama() -> None:
    import requests

    resp = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": settings.llm_model, "prompt": "Reply with exactly: pong", "stream": False},
        timeout=30,
    )
    resp.raise_for_status()
    print("Response:", resp.json()["response"])


if __name__ == "__main__":
    print(f"Provider: {settings.llm_provider} | Model: {settings.llm_model}")
    dispatch = {
        "groq": test_groq,
        "openai": test_openai,
        "anthropic": test_anthropic,
        "ollama": test_ollama,
    }
    dispatch[settings.llm_provider]()
    print("✅ Connection OK — safe to proceed.")
