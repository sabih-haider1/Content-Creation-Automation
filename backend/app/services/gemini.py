import os
from google import genai
from google.genai import types
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

class Scene(BaseModel):
    scene_number: int
    narration: str
    visual_prompt: str
    duration_seconds: int

class VideoBlueprint(BaseModel):
    niche: str
    title: str
    scenes: list[Scene]

def generate_script(prompt: str) -> str:
    response = client.models.generate_content(
        model='gemini-2.5-pro',
        contents=["Analyze this request and generate a structured video script.", prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=VideoBlueprint,
            system_instruction="You are an expert short-form video producer."
        ),
    )
    return response.text
