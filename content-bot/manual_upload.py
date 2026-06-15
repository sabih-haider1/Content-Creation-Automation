import db
import youtube_uploader
import asyncio
import json
import os

async def manual_upload(job_id):
    try:
        await db.init_db()
        job = await db.get_job(job_id)
        if not job:
            print(f"Job {job_id} not found.")
            return
            
        print(f"Uploading Job: {job_id}")
        print(f"Title: {job.get('title')}")
        
        video_path = job.get('video_path')
        if not os.path.exists(video_path):
            # Try prepending content-bot/ if needed, though db should have relative path
            if os.path.exists(os.path.join("content-bot", video_path)):
                 video_path = os.path.join("content-bot", video_path)
        
        hashtags = job.get('hashtags')
        if hashtags:
            hashtags = json.loads(hashtags)
        else:
            hashtags = []
            
        url = await asyncio.to_thread(
            youtube_uploader.upload_video, 
            video_path, 
            job.get('title', 'No Title'), 
            job.get('description', ''), 
            hashtags
        )
        
        print(f"Success! YouTube URL: {url}")
        await db.update_job(job_id, youtube_url=url)
        
    except Exception as e:
        print(f"Upload failed: {e}")

if __name__ == "__main__":
    import sys
    job_id = sys.argv[1] if len(sys.argv) > 1 else 'e820e642-c950-4c48-b55a-7f6d24ed8895'
    asyncio.run(manual_upload(job_id))
