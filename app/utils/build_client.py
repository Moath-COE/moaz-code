import os

from openai import OpenAI


def build_client():
    API_KEY = os.getenv("API_KEY") or os.getenv("OPENROUTER_API_KEY")
    BASE_URL = os.getenv("BASE_URL", default="https://openrouter.ai/api/v1")
    if not API_KEY:
        raise RuntimeError("API_KEY is not set")

    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    return client
