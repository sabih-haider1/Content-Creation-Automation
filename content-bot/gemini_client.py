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
        print(f"[Warning] Gemini classify_prompt API error ({e}). Falling back to local default.")
        return {"niche": "educational", "content_type": "informative"}

async def generate_script(user_prompt: str, niche: str, content_type: str, personality: str = None) -> dict:
    """
    Generates a YouTube Short script based on the prompt/content and personality.
    """
    # Auto-detect personality if not provided
    if not personality:
        prompt_lower = user_prompt.lower()
        if any(word in prompt_lower for word in ["funny", "humor", "joke", "comedy", "laugh", "witty"]):
            personality = "Funny"
        elif any(word in prompt_lower for word in ["professional", "formal", "corporate", "academic", "business", "serious"]):
            personality = "Professional"
        elif any(word in prompt_lower for word in ["documentary", "history", "biography", "docu", "narrative", "epic"]):
            personality = "Documentary"
        else:
            # Map based on niche and content type
            if niche.lower() == "entertainment":
                personality = "Funny"
            elif content_type.lower() == "storytelling":
                personality = "Documentary"
            elif niche.lower() in ["educational", "news"]:
                personality = "Professional"
            else:
                personality = "Standard"

    # Define guidelines for each personality
    personality_guidelines = {
        "Funny": (
            "TONE: Witty, humorous, energetic, and highly entertaining. Use lighthearted jokes, "
            "clever puns, or comedic timing. The narrator should feel like a funny friend. "
            "VISUALS: High energy, exaggerated, funny, or unexpected visual setups that complement the jokes."
        ),
        "Professional": (
            "TONE: Authoritative, polished, clear, and formal. Avoid slang. Focus on precise facts, "
            "logical structuring, and educational value. "
            "VISUALS: Clean, professional, high-quality infographics, sleek transitions, and sophisticated imagery."
        ),
        "Documentary": (
            "TONE: Cinematic, epic, dramatic, and narrative-driven. Evoke curiosity, historical "
            "significance, or scientific wonder. Narrator style should be immersive and deep. "
            "VISUALS: High-contrast, cinematic lighting, epic landscapes, historical scenes, or majestic views."
        ),
        "Standard": (
            "TONE: Friendly, engaging, clear, and direct. Optimized for typical fast-paced short-form content. "
            "VISUALS: Colorful, modern, and highly visually engaging scenes to retain attention."
        )
    }

    guidelines = personality_guidelines.get(personality, personality_guidelines["Standard"])

    prompt = f"""
    You are an expert scriptwriter for YouTube Shorts. 
    Create a highly engaging script based on the provided topic or context.
    The script should be concise (around 15-30 seconds).
    
    CRITICAL - Style and Personality Guidelines to follow:
    Selected Personality: {personality}
    {guidelines}
    
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
        print(f"[Warning] Gemini generate_script API error ({e}). Falling back to test template.")
        return {
            "title": f"AI Insight ({personality})",
            "scenes": [
                {
                    "scene": 1, "duration": 5, "text": f"Welcome to this {personality} insight.", 
                    "visual_prompt": f"A beautiful cinematic scene matching a {personality} style."
                },
                {
                    "scene": 2, "duration": 5, "text": "Creating your custom content now.", 
                    "visual_prompt": "Beautiful light particles forming a sphere."
                }
            ],
            "hashtags": ["ai", "automation", personality.lower()],
            "description": f"Custom AI-generated content in a {personality} tone."
        }
