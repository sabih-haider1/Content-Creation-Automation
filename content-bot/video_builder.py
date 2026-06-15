import os
import shutil
from PIL import Image, ImageDraw, ImageFont
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips
from config import ENVIRONMENT

# Gradient color pairs for up to 6 scenes
GRADIENTS = [
    ((20, 30, 85), (0, 128, 255)),      # Scene 1: Deep Blue to Neon Blue
    ((45, 0, 90), (160, 20, 80)),       # Scene 2: Royal Violet to Magenta
    ((10, 80, 80), (20, 180, 100)),     # Scene 3: Deep Teal to Emerald
    ((30, 30, 30), (200, 80, 20)),      # Scene 4: Charcoal to Warm Orange
    ((15, 25, 60), (100, 30, 100)),     # Scene 5: Deep Navy to Velvet Plum
    ((10, 50, 30), (180, 140, 20))      # Scene 6: Forest Green to Bright Gold
]

def get_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    """
    Attempts to load a standard sans-serif system font (Arial/Helvetica/DejaVu).
    Falls back gracefully to Pillow's default font.
    """
    font_paths = []
    if bold:
        font_paths = [
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/System/Library/Fonts/Helvetica-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
            "C:\\Windows\\Fonts\\arialbd.ttf",
            "arialbd.ttf"
        ]
    else:
        font_paths = [
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
            "C:\\Windows\\Fonts\\arial.ttf",
            "arial.ttf"
        ]
        
    for path in font_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    try:
        return ImageFont.load_default()
    except Exception:
        return None

def create_gradient_image(color1, color2, width=1080, height=1920) -> Image.Image:
    """
    Generates a smooth linear gradient image between two RGB colors.
    """
    base = Image.new("RGB", (width, height), color1)
    draw = ImageDraw.Draw(base)
    for y in range(height):
        ratio = y / height
        r = int(color1[0] + (color2[0] - color1[0]) * ratio)
        g = int(color1[1] + (color2[1] - color1[1]) * ratio)
        b = int(color1[2] + (color2[2] - color1[2]) * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    return base

def wrap_text(text: str, font: ImageFont.ImageFont, max_width: int) -> list:
    """
    Splits text into lines that fit within max_width pixels.
    """
    words = text.split()
    lines = []
    current_line = []
    
    for word in words:
        test_line = " ".join(current_line + [word])
        # Measure text width in Pillow
        try:
            bbox = font.getbbox(test_line)
            width = bbox[2] - bbox[0]
        except Exception:
            try:
                width = font.getsize(test_line)[0]
            except Exception:
                # Naive length estimate if font measure fails
                width = len(test_line) * (font.size * 0.5)
                
        if width <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
                current_line = [word]
            else:
                lines.append(word)
                
    if current_line:
        lines.append(" ".join(current_line))
    return lines

def draw_semi_transparent_box_and_text(
    image: Image.Image,
    text: str,
    font: ImageFont.ImageFont,
    x_center: int,
    y_center: int,
    text_color: tuple,
    box_fill_rgba: tuple,
    max_width: int
) -> Image.Image:
    """
    Draws a wrapped text block surrounded by a semi-transparent rounded background rectangle.
    Returns a new RGBA composited image.
    """
    lines = wrap_text(text, font, max_width)
    if not lines:
        return image
        
    line_heights = []
    line_widths = []
    
    # Measure line sizes
    for line in lines:
        try:
            bbox = font.getbbox(line)
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
        except Exception:
            try:
                w, h = font.getsize(line)
            except Exception:
                w = len(line) * (font.size * 0.5)
                h = font.size
        line_widths.append(w)
        line_heights.append(max(h, font.size))
        
    line_spacing = 15
    total_height = sum(line_heights) + line_spacing * (len(lines) - 1)
    max_line_width = max(line_widths) if line_widths else 0
    
    box_w = min(max_line_width + 60, max_width + 80)
    box_h = total_height + 40
    
    box_x1 = x_center - box_w // 2
    box_y1 = y_center - box_h // 2
    box_x2 = x_center + box_w // 2
    box_y2 = y_center + box_h // 2
    
    # Create overlay for alpha transparency
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    
    # Draw background box
    try:
        overlay_draw.rounded_rectangle([box_x1, box_y1, box_x2, box_y2], radius=15, fill=box_fill_rgba)
    except Exception:
        overlay_draw.rectangle([box_x1, box_y1, box_x2, box_y2], fill=box_fill_rgba)
        
    # Draw text lines
    current_y = box_y1 + 20
    for i, line in enumerate(lines):
        line_w = line_widths[i]
        line_x = x_center - line_w // 2
        overlay_draw.text((line_x, current_y), line, fill=text_color, font=font)
        current_y += line_heights[i] + line_spacing
        
    # Combine original image with transparent overlay
    return Image.alpha_composite(image.convert("RGBA"), overlay)

def generate_scene_image(
    scene_index: int,
    title: str,
    text: str,
    output_path: str
) -> str:
    """
    Assembles a gorgeous, styled vertical frame for a scene and saves it to output_path.
    """
    # Pick gradient
    color_pair = GRADIENTS[scene_index % len(GRADIENTS)]
    img = create_gradient_image(color_pair[0], color_pair[1], 1080, 1920)
    
    # Get fonts
    title_font = get_font(52, bold=True)
    text_font = get_font(42, bold=False)
    
    # 1. Draw Title at top center
    # Darker translucent top panel for title
    img = draw_semi_transparent_box_and_text(
        image=img,
        text=title.upper(),
        font=title_font,
        x_center=540,
        y_center=240,
        text_color=(255, 255, 255, 255),
        box_fill_rgba=(0, 0, 0, 180),
        max_width=800
    )
    
    # 2. Draw spoken subtitle in the lower half
    img = draw_semi_transparent_box_and_text(
        image=img,
        text=text,
        font=text_font,
        x_center=540,
        y_center=1350,
        text_color=(255, 255, 255, 255),
        box_fill_rgba=(0, 0, 0, 140),
        max_width=850
    )
    
    # Convert back to RGB and save
    final_img = img.convert("RGB")
    final_img.save(output_path, "JPEG", quality=95)
    return output_path

def build_video_from_scenes(scenes_data: list, job_id: str, output_path: str) -> str:
    """
    Existing static image builder (kept for compatibility).
    """
    clips = []
    
    try:
        for scene in scenes_data:
            audio_clip = AudioFileClip(scene["audio_path"])
            duration = audio_clip.duration
            video_clip = ImageClip(scene["image_path"]).with_duration(duration)
            video_clip = video_clip.with_audio(audio_clip)
            clips.append(video_clip)
            
        final_clip = concatenate_videoclips(clips, method="compose")
        temp_audio = f"output/{job_id}_temp_audio.m4a"
        
        final_clip.write_videofile(
            output_path,
            fps=24,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile=temp_audio,
            remove_temp=True,
            logger=None
        )
    finally:
        for clip in clips:
            try: clip.close()
            except Exception: pass
        try: final_clip.close()
        except Exception: pass
            
    return output_path

def build_video_from_veo_scenes(scenes_data: list, job_id: str, output_path: str) -> str:
    """
    Merges dynamic video clips from Veo 2 with TTS audio and subtitles.
    """
    from moviepy import VideoFileClip, TextClip, CompositeVideoClip
    
    final_clips = []
    
    try:
        for scene in scenes_data:
            # Load the Veo 2 video clip
            video_clip = VideoFileClip(scene["video_path"])
            
            # Load the TTS audio
            audio_clip = AudioFileClip(scene["audio_path"])
            
            # Ensure video duration matches audio duration (loop or trim video if necessary)
            if video_clip.duration < audio_clip.duration:
                # Loop video to match audio
                video_clip = video_clip.with_duration(audio_clip.duration).loop()
            else:
                # Trim video to match audio
                video_clip = video_clip.with_duration(audio_clip.duration)
                
            video_clip = video_clip.with_audio(audio_clip)
            
            # Optional: Add subtitles overlay here if desired
            # For now, we'll keep it simple and just merge the clips
            
            final_clips.append(video_clip)
            
        # Concatenate all scenes
        final_production = concatenate_videoclips(final_clips, method="compose")
        
        temp_audio = f"output/{job_id}_final_temp.m4a"
        
        final_production.write_videofile(
            output_path,
            fps=24,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile=temp_audio,
            remove_temp=True,
            logger=None
        )
        
    finally:
        for clip in final_clips:
            try: clip.close()
            except Exception: pass
        try: final_production.close()
        except Exception: pass
            
    return output_path
