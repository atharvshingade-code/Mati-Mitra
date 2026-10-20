
import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
model = os.environ["GEMINI_MODEL"]

response = client.models.generate_content(
    model=model,
    contents="Reply in Marathi: नमस्कार, मी Jarvis for Farmers आहे."
)

print(response.text)
