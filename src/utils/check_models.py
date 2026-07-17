from google import genai
import os
from dotenv import load_dotenv

load_dotenv()  # Loads your .env file

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

print("Available Models for Text Generation:")
for model in client.models.list():
    # We only want to see models that support generating text
    if "generateContent" in model.supported_actions:
        print(f"- {model.name}")

# not relly sure about the effectivity of this module, but it should show the models available for your api key
# and not sure, because it show models, which gave me errors when I tried to use them via API, like gemini-2.5-flash for example
