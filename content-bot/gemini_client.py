import json
import re
import google.generativeai as genai
from config import GEMINI_API_KEY

# Configure Gemini
try:
    genai.configure(api_key=GEMINI_API_KEY)
except Exception as e:
    print(f"Warning: Failed to configure Gemini API client: {e}")

MODEL_NAME = "gemini-1.5-flash"

def clean_json_response(text: str) -> str:
    """
    Cleans up markdown code blocks if Gemini returns them.
    """
    cleaned = text.strip()
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.DOTALL)
    if match:
        return match.group(1).strip()
    return cleaned

async def classify_prompt(user_prompt: str) -> dict:
    """
    Classifies the user's content request into niche and content_type.
    """
    prompt = f"""
    You are an expert content strategist. Analyze the following request or text content and classify it.
    Return ONLY JSON.
    
    Expected format:
    {{"niche": "educational|motivational|entertainment|kids|news", "content_type": "informative|storytelling|listicle|tutorial"}}
    
    Request Content:
    {user_prompt}
    """
    
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        cleaned_text = clean_json_response(response.text)
        return json.loads(cleaned_text)
    except Exception as e:
        print(f"⚠️ Gemini classify_prompt API error ({e}). Falling back to local default.")
        return {"niche": "educational", "content_type": "informative"}

async def generate_script(user_prompt: str, niche: str, content_type: str) -> dict:
    """
    Generates a YouTube Short script based on the prompt/content.
    """
    prompt = f"""
    You are an expert scriptwriter for YouTube Shorts. 
    Create a highly engaging script based on the provided topic or context.
    The script should be concise (around 15-30 seconds).
    
    Return ONLY JSON.
    
    Format:
    {{
      "title": "Catchy Title",
      "scenes": [
        {{
          "scene": 1, 
          "duration": 5, 
          "text": "The exact words to be spoken by the narrator", 
          "visual_prompt": "Detailed description of what should be shown on screen"
        }}
      ],
      "hashtags": ["tag1", "tag2"],
      "description": "Engaging video description"
    }}
    
    Topic/Context:
    {user_prompt}
    
    Niche: {niche}
    Content Type: {content_type}
    """
    
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        cleaned_text = clean_json_response(response.text)
        return json.loads(cleaned_text)
    except Exception as e:
        print(f"⚠️ Gemini generate_script API error ({e}). Falling back to test template.")
        return {
            "title": "AI Insight",
            "scenes": [
                {
                    "scene": 1, "duration": 5, "text": "Analyzing the data for your request.", 
                    "visual_prompt": "Cinematic digital interface showing data streams."
                },
                {
                    "scene": 2, "duration": 5, "text": "Creating your custom content now.", 
                    "visual_prompt": "Beautiful light particles forming a sphere."
                }
            ],
            "hashtags": ["ai", "automation"],
            "description": "Custom AI-generated content."
        }
