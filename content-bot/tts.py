import os
import asyncio
import edge_tts
from gtts import gTTS

DEFAULT_VOICE = "en-US-AriaNeural"

async def generate_speech(text: str, output_path: str, voice: str = DEFAULT_VOICE):
    """
    Generates an MP3 file for a given text block.
    Attempts edge-tts first (high-quality neural voice), and falls back
    to gTTS (standard Google Translate TTS) on any network or websocket errors.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    try:
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)
        return output_path
    except Exception as e:
        print(f"⚠️ edge-tts failed ({e}). Falling back to gTTS (standard HTTP-based)...")
        
        # Offload synchronous gTTS file saving to a thread pool to avoid blocking the event loop
        loop = asyncio.get_running_loop()
        def _save_gtts():
            tts_obj = gTTS(text=text, lang="en", slow=False)
            tts_obj.save(output_path)
            
        await loop.run_in_executor(None, _save_gtts)
        return output_path
