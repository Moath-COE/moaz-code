import os

from openai import OpenAI


def build_client():
    DEV_API_KEY = os.getenv("API_KEY")
    DEV_BASE_URL = os.getenv("BASE_URL", default="https://api.openai.com/v1")
    API_KEY = os.getenv("OPENROUTER_API_KEY", default=DEV_API_KEY)
    BASE_URL = os.getenv("OPENROUTER_BASE_URL", default=DEV_BASE_URL)
    if not API_KEY:
        raise RuntimeError("API_KEY is not set")

    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    return client
