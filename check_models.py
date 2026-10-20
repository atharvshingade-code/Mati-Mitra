
import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("GEMINI_API_KEY not found. Check your .env file.")
else:
    try:
        client = genai.Client(api_key=api_key)

        print("Available Gemini models:\n")

        for model in client.models.list():
            name = model.name or ""
            if "gemini" in name.lower():
                print(name)

    except Exception as error:
        print("Could not retrieve models.")
        print("Check your API key, API access, and network connection.")
        print(type(error).__name__, str(error))
