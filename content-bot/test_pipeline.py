import asyncio
import traceback
from pipeline import run_content_pipeline

async def test_run():
    print("🚀 Starting end-to-end pipeline test run...")
    prompt = "explain how black holes work"
    
    async def status_cb(status, data):
        print(f"📊 [PROGRESS UPDATE] Status: {status} | Extra Data: {data}")
        
    try:
        result = await run_content_pipeline(prompt, status_callback=status_cb)
        print("\n✅ Pipeline test run completed successfully!")
        print(f"🎥 Generated Video Path: {result['video_path']}")
        print(f"📝 Generated Title: {result['title']}")
        print(f"📖 Generated Description: {result['description']}")
        print(f"🏷️ Generated Hashtags: {result['hashtags']}")
    except Exception as e:
        print("\n❌ Pipeline test run failed:")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_run())
