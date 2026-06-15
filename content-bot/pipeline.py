import os
import shutil
import json
import uuid
import asyncio
import db
import gemini_client
import veo_client
import tts
import video_builder
import utils

async def run_content_pipeline(user_prompt: str, user_id: int, job_id: str = None, personality: str = None, status_callback=None) -> dict:
    """
    Orchestrates the entire content bot pipeline using Gemini Veo 2.
    """
    if not job_id:
        job_id = str(uuid.uuid4())
        
    await db.init_db()
    await db.create_job(job_id, user_id, user_prompt)
    if personality:
        await db.update_job(job_id, personality=personality)
    
    temp_dir = f"output/{job_id}_temp"
    os.makedirs(temp_dir, exist_ok=True)
    final_video_path = f"output/{job_id}.mp4"
    
    async def update_status(status: str, **kwargs):
        await db.update_job(job_id, status=status, **kwargs)
        if status_callback:
            await status_callback(status, kwargs)
            
    try:
        # Step 1: Link Processing
        processed_prompt = user_prompt
        if utils.is_url(user_prompt):
            await update_status("analyzing_link")
            link_content = await asyncio.to_thread(utils.extract_content_from_url, user_prompt)
            if link_content:
                processed_prompt = f"Context from link: {link_content}\n\nTask: Create a video based on the information above. Original URL: {user_prompt}"
            else:
                print(f"Warning: Could not extract content from URL {user_prompt}")

        # Step 2: Classification
        await update_status("classifying")
        classification = await gemini_client.classify_prompt(processed_prompt)
        niche = classification.get("niche", "educational")
        content_type = classification.get("content_type", "informative")
        await db.update_job(job_id, niche=niche, content_type=content_type)
        
        # Step 3: Script Generation
        await update_status("scripting")
        script_data = await gemini_client.generate_script(processed_prompt, niche, content_type, personality=personality)
        
        title = script_data.get("title", f"The Secrets of {user_prompt}")
        scenes = script_data.get("scenes", [])
        hashtags = script_data.get("hashtags", ["trending", "learning"])
        description = script_data.get("description", "")
        
        await db.update_job(
            job_id,
            title=title,
            script=json.dumps(scenes),
            hashtags=json.dumps(hashtags),
            description=description
        )
        
        # Step 4: Asset Generation (Image + TTS per Scene)
        await update_status("assets")
        
        scenes_data = []
        for idx, scene in enumerate(scenes):
            scene_num = scene.get("scene", idx + 1)
            text = scene.get("text", "")
            
            audio_path = f"{temp_dir}/scene_{scene_num}.mp3"
            image_path = f"{temp_dir}/scene_{scene_num}.jpg"
            
            # Generate speech
            await tts.generate_speech(text, audio_path)
            
            # Generate styled scene image instead of Veo video
            await asyncio.to_thread(
                video_builder.generate_scene_image,
                scene_index=idx,
                title=title,
                text=text,
                output_path=image_path
            )
            
            scenes_data.append({
                "scene_num": scene_num,
                "image_path": image_path,
                "audio_path": audio_path,
                "text": text
            })
            
        # Step 5: Build Final Video (Merging Images with TTS)
        await update_status("rendering")
        await asyncio.to_thread(
            video_builder.build_video_from_scenes,
            scenes_data, 
            job_id, 
            final_video_path
        )
        
        await update_status("done", video_path=final_video_path)
        
        return {
            "job_id": job_id,
            "title": title,
            "scenes": scenes,
            "hashtags": hashtags,
            "description": description,
            "video_path": final_video_path
        }
        
    except Exception as e:
        error_msg = str(e)
        print(f"Pipeline error on job {job_id}: {error_msg}")
        await update_status("failed", error_message=error_msg)
        raise e
        
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
