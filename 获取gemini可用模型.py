import google.generativeai as genai
import config

genai.configure(api_key=config.GOOGLE_API_KEY)
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(m.name)