import time
import asyncio
import json
from google import genai
from google.genai import types
from config import GEMINI_API_KEY

# Initialize the client
client = genai.Client(api_key=GEMINI_API_KEY)

async def generate_scene_video(prompt: str, output_path: str, aspect_ratio: str = "9:16", duration: int = 5):
    """
    Generates a single video clip using Gemini Veo 2 for a given prompt.
    """
    try:
        print(f"🚀 Requesting Veo 2 video for prompt: '{prompt[:50]}...'")
        
        operation = await asyncio.to_thread(
            client.models.generate_videos,
            model="veo-2.0-generate-001",
            prompt=prompt,
            config=types.GenerateVideosConfig(
                number_of_videos=1,
                aspect_ratio=aspect_ratio,
                duration_seconds=duration,
                enhance_prompt=True,
                person_generation="allow_adult"
            ),
        )
        
        print(f"🎬 Veo 2 operation created: {operation.name}")
        
        # Poll for completion
        start_time = time.time()
        while not operation.done:
            elapsed = int(time.time() - start_time)
            print(f"⏳ Veo 2 processing... ({elapsed}s elapsed)")
            await asyncio.sleep(15)
            operation = await asyncio.to_thread(client.operations.get, operation)
            
        print(f"✅ Veo 2 operation {operation.name} finished.")
        
        if operation.response:
            print(f"📦 Full response metadata: {operation.response}")
            if operation.response.generated_videos:
                generated_video = operation.response.generated_videos[0]
                print(f"📥 Downloading video file...")
                await asyncio.to_thread(client.files.download, file=generated_video.video)
                await asyncio.to_thread(generated_video.video.save, output_path)
                print(f"💾 Video saved to: {output_path}")
                return output_path
            else:
                # Check for filtering or other indicators
                error_info = getattr(operation.response, 'error', 'No specific error info')
                raise Exception(f"Veo 2 returned no videos. Response metadata: {operation.response}. Info: {error_info}")
        else:
            raise Exception(f"Veo 2 operation failed or returned empty response. Operation: {operation}")
            
    except Exception as e:
        print(f"❌ Veo 2 API Error: {str(e)}")
        raise e
