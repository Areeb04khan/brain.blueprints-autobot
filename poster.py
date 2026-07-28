# -*- coding: utf-8 -*-
"""
Shayari Instagram Bot v5.0 (Viral & High Retention Edition)
- Real authentic Shayari via Gemini AI
- Free Pexels Video API integration for cinematic Reel backgrounds
- Dynamic text overlays timed with Urdu Edge-TTS voiceover
- Retention-focused hooks to drive Shares & Saves
- Fully automated with GitHub Actions & progress.json engine
"""

from google import genai
import requests
import json
import os
import sys
import time
import textwrap
import random
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import base64
from urllib.parse import urlparse

# ============================================================
# CONFIGURATION
# ============================================================
GEMINI_API_KEY         = os.environ.get("GEMINI_API_KEY", "")
INSTAGRAM_ACCESS_TOKEN = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
INSTAGRAM_USER_ID      = os.environ.get("INSTAGRAM_USER_ID", "")
PEXELS_API_KEY         = os.environ.get("PEXELS_API_KEY", "") # Free from pexels.com/api
CATBOX_USERHASH        = os.environ.get("CATBOX_USERHASH", "")
MEDIA_HOST             = os.environ.get("MEDIA_HOST", "tempfile").lower()
CLOUDINARY_URL         = os.environ.get("CLOUDINARY_URL", "")
POST_TYPE              = os.environ.get("POST_TYPE", "photo") # "photo" or "reel"
IG_HANDLE              = "@ak_apak"

MAX_RETRIES = int(os.environ.get("MAX_RETRIES", "2"))
RETRY_DELAY = int(os.environ.get("RETRY_DELAY_SECONDS", "60"))

REQUIRED_ENV_VARS = ["GEMINI_API_KEY", "INSTAGRAM_ACCESS_TOKEN", "INSTAGRAM_USER_ID"]

def validate_environment():
    missing = [name for name in REQUIRED_ENV_VARS if not os.environ.get(name)]
    if missing:
        raise RuntimeError(f"Missing required secret(s): {', '.join(missing)}")

def is_retryable_error(e):
    msg = str(e).lower()
    return any(k in msg for k in ["503", "unavailable", "timeout", "connection", "rate limit"])

# Font Paths (Installed via apt-get in workflow)
FONT_SERIF  = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
FONT_ITALIC = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf"
FONT_SANS   = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

# ============================================================
# POET SCHEDULE
# ============================================================
POET_SCHEDULE = [
    {"name": "Mirza Ghalib", "era": "1797-1869"},
    {"name": "Mir Taqi Mir", "era": "1723-1810"},
    {"name": "Jaun Elia", "era": "1931-2002"},
    {"name": "Faiz Ahmed Faiz", "era": "1911-1984"},
    {"name": "Allama Iqbal", "era": "1877-1938"},
    {"name": "Ahmad Faraz", "era": "1931-2008"},
    {"name": "Parveen Shakir", "era": "1952-1994"},
    {"name": "Rahat Indori", "era": "1950-2020"},
    {"name": "Gulzar", "era": "1934-"},
    {"name": "Sahir Ludhianvi", "era": "1921-1980"},
    {"name": "Bashir Badr", "era": "1935-"},
    {"name": "Tehzeeb Hafi", "era": "Contemporary"},
    {"name": "Munawwar Rana", "era": "1952-2024"},
    {"name": "Dushyant Kumar", "era": "1933-1975"}
]

# Color Palettes for Static Photos
EMOTION_PALETTES = {
    "ishq":     {"bg":"#1a0010","text":"#f5c6d0","accent":"#e8587a","sub":"#b03060","border":"#8b1a3a"},
    "dard":     {"bg":"#0a0a1a","text":"#c8d4e8","accent":"#7090d0","sub":"#405080","border":"#2a3a6a"},
    "tanhai":   {"bg":"#060d0d","text":"#b8d8d8","accent":"#40a0a0","sub":"#206060","border":"#104040"},
    "intezaar": {"bg":"#0f0f0f","text":"#e0d8c8","accent":"#c8a860","sub":"#806030","border":"#503810"},
    "falsafa":  {"bg":"#080818","text":"#d0c8e8","accent":"#9070c0","sub":"#504080","border":"#302060"}
}
DEFAULT_PALETTE = EMOTION_PALETTES["dard"]

# Hook Triggers for Instagram Engagement (Virality)
VIRAL_HOOKS = [
    "Read this twice if you're missing someone silently...",
    "When {poet_name} said this, it hit differently...",
    "For the nights when words fail you...",
    "Send this to someone you can't text anymore.",
    "A line that will stay with you forever...",
    "Save this before you forget how deep poetry can go."
]

# ============================================================
# STEP 1: Gemini AI Content Generator
# ============================================================
def generate_content(poet: dict) -> dict:
    client = genai.Client(api_key=GEMINI_API_KEY)
    hook_template = random.choice(VIRAL_HOOKS)
    hook = hook_template.format(poet_name=poet['name'])

    prompt = (
        f"You curate a viral Instagram Shayari account dedicating posts to legendary poets.\n"
        f"Today's poet: {poet['name']} ({poet['era']})\n\n"
        "RULES:\n"
        f"1. Quote a REAL, iconic 2-line couplet (sher) by {poet['name']}.\n"
        "2. Transliterate it in Roman Urdu (sher_roman).\n"
        "3. Provide exact Urdu script (sher_urdu) for TTS narration.\n"
        "4. English translation (MAX 1 LINE, poetic & deep).\n"
        "5. Provide 2 pexels search keywords for dark cinematic background videos (e.g., 'dark rain', 'night walk', 'coffee cup', 'lonely street').\n\n"
        "Return ONLY valid JSON:\n"
        "{\n"
        f'  "hook": "{hook}",\n'
        '  "sher_roman": "Line 1\\nLine 2",\n'
        '  "sher_urdu": "Urdu text here",\n'
        '  "english_translation": "...",\n'
        '  "source": "...",\n'
        '  "emotion": "dard",\n'
        '  "pexels_query": "dark rain",\n'
        '  "caption": "Mid-thought story about this poet and why this sher resonates..."\n'
        "}"
    )

    response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    raw = response.text.strip().replace("```json","").replace("```","").strip()
    return json.loads(raw)

# ============================================================
# STEP 2: Stock Video Retriever (Pexels Free API)
# ============================================================
def fetch_pexels_background_video(query: str, target_dir: str = "output") -> str:
    """Fetch a free vertical cinematic background video from Pexels API."""
    if not PEXELS_API_KEY:
        print("ℹ️ No PEXELS_API_KEY provided. Will fallback to dynamic static background.")
        return None

    try:
        headers = {"Authorization": PEXELS_API_KEY}
        url = f"https://api.pexels.com/videos/search?query={query}&orientation=portrait&per_page=5"
        res = requests.get(url, headers=headers, timeout=10)
        
        if not res.ok:
            return None
            
        data = res.json()
        videos = data.get("videos", [])
        if not videos:
            return None

        video = random.choice(videos)
        # Select HD vertical MP4 link
        video_files = video.get("video_files", [])
        selected_file = None
        for vf in video_files:
            if vf.get("file_type") == "video/mp4" and vf.get("width", 0) >= 720:
                selected_file = vf["link"]
                break
        
        if not selected_file and video_files:
            selected_file = video_files[0]["link"]

        if selected_file:
            os.makedirs(target_dir, exist_ok=True)
            v_path = os.path.join(target_dir, f"bg_{int(time.time())}.mp4")
            v_data = requests.get(selected_file, timeout=30).content
            with open(v_path, "wb") as f:
                f.write(v_data)
            print(f"✅ Downloaded Pexels video background: {v_path}")
            return v_path

    except Exception as e:
        print(f"⚠️ Pexels Video fetch failed: {e}")
    return None

# ============================================================
# STEP 3: Photo Renderer (1080x1080)
# ============================================================
def create_photo_image(data: dict, poet: dict) -> str:
    W, H = 1080, 1080
    palette = EMOTION_PALETTES.get(data.get("emotion","dard"), DEFAULT_PALETTE)

    img = Image.new("RGB", (W, H), color=palette["bg"])
    draw = ImageDraw.Draw(img, "RGBA")

    # Fonts
    try:
        font_poet  = ImageFont.truetype(FONT_SERIF, 28)
        font_sher  = ImageFont.truetype(FONT_SERIF, 42)
        font_trans = ImageFont.truetype(FONT_ITALIC, 20)
        font_brand = ImageFont.truetype(FONT_SANS, 16)
    except:
        font_poet = font_sher = font_trans = font_brand = ImageFont.load_default()

    def center(text, y, font, color):
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        draw.text(((W - tw) / 2, y), text, font=font, fill=color)

    # Content
    center(f"-- {poet['name']} --", 100, font_poet, palette["accent"])
    
    lines = data["sher_roman"].strip().split("\n")
    y_pos = 380
    for line in lines:
        for wline in textwrap.wrap(line, width=32):
            center(wline, y_pos, font_sher, palette["text"])
            y_pos += 60

    y_pos += 40
    for tline in textwrap.wrap(f'"{data["english_translation"]}"', width=50):
        center(tline, y_pos, font_trans, palette["accent"])
        y_pos += 30

    center(IG_HANDLE, 980, font_brand, palette["sub"])

    os.makedirs("output", exist_ok=True)
    fname = f"output/photo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    img.save(fname, "JPEG", quality=95)
    return fname

# ============================================================
# STEP 4: Edge TTS Audio Generator
# ============================================================
def generate_tts(text: str, output_path: str) -> bool:
    try:
        import asyncio
        import edge_tts
        VOICE = "ur-PK-AsadNeural"

        async def _speak():
            communicate = edge_tts.Communicate(text, VOICE, rate="-10%", pitch="-4Hz")
            await communicate.save(output_path)

        asyncio.run(_speak())
        return True
    except Exception as e:
        print(f"⚠️ TTS error: {e}")
        return False

# ============================================================
# STEP 5: Reel Video Studio (Pexels + Audio + MoviePy)
# ============================================================
def create_reel_video(data: dict, poet: dict, tts_path: str) -> str:
    try:
        from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip, ImageClip, CompositeAudioClip
        import numpy as np

        # 1. Prepare Audio
        tts_audio = AudioFileClip(tts_path)
        duration = min(tts_audio.duration + 3, 30)

        # 2. Fetch Pexels Background or fallback to static color
        bg_video_path = fetch_pexels_background_video(data.get("pexels_query", "dark rain"))
        
        if bg_video_path:
            bg_clip = VideoFileClip(bg_video_path).subclip(0, duration)
            bg_clip = bg_clip.resize(height=1920)
            if bg_clip.w < 1080:
                bg_clip = bg_clip.resize(width=1080)
            bg_clip = bg_clip.crop(x_center=bg_clip.w/2, y_center=bg_clip.h/2, width=1080, height=1920)
            # Apply slight dark overlay for text readability
            bg_clip = bg_clip.fl_image(lambda image: (image * 0.5).astype(np.uint8))
        else:
            # Fallback static image reel clip
            fallback_img = create_photo_image(data, poet)
            bg_clip = ImageClip(fallback_img, duration=duration)

        # 3. Add Background Music (if available in music/)
        music_dir = "music"
        final_audio = tts_audio
        if os.path.exists(music_dir):
            tracks = [os.path.join(music_dir, f) for f in os.listdir(music_dir) if f.endswith(".mp3")]
            if tracks:
                music = AudioFileClip(random.choice(tracks)).subclip(0, duration).volumex(0.15)
                final_audio = CompositeAudioClip([tts_audio.volumex(1.0), music])

        # 4. Render On-Screen Text (Viral Hook + Shayari)
        # Combine into center text overlay
        overlay_img = Image.new("RGBA", (1080, 1920), (0,0,0,0))
        draw = ImageDraw.Draw(overlay_img)
        font_hook = ImageFont.truetype(FONT_ITALIC, 32)
        font_sher = ImageFont.truetype(FONT_SERIF, 52)
        font_poet = ImageFont.truetype(FONT_SERIF, 30)

        # Draw Hook
        hook_text = textwrap.fill(data.get("hook", ""), width=30)
        draw.text((540, 400), hook_text, font=font_hook, fill="#E0E0E0", anchor="mm", align="center")

        # Draw Sher
        sher_text = data["sher_roman"]
        draw.text((540, 960), sher_text, font=font_sher, fill="#FFFFFF", anchor="mm", align="center")

        # Draw Poet Signature
        draw.text((540, 1400), f"- {poet['name']}", font=font_poet, fill="#C0A060", anchor="mm")
        draw.text((540, 1750), IG_HANDLE, font=font_poet, fill="#888888", anchor="mm")

        overlay_fname = f"output/overlay_{int(time.time())}.png"
        overlay_img.save(overlay_fname)

        txt_clip = ImageClip(overlay_fname, duration=duration)

        # 5. Composite Final Video
        final_video = CompositeVideoClip([bg_clip, txt_clip]).set_audio(final_audio)
        reel_path = f"output/reel_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        
        final_video.write_videofile(reel_path, fps=24, codec="libx264", audio_codec="aac", verbose=False, logger=None)
        return reel_path

    except Exception as e:
        print(f"❌ Video render error: {e}")
        return None

# ============================================================
# STEP 6: Media Hosting & Instagram Publishing
# ============================================================
def upload_public_media(path: str) -> str:
    """Uploads file to TempFile or Cloudinary for Instagram Graph API access."""
    if MEDIA_HOST == "cloudinary" and CLOUDINARY_URL:
        parsed = urlparse(CLOUDINARY_URL)
        endpoint = f"https://api.cloudinary.com/v1_1/{parsed.hostname}/auto/upload"
        with open(path, "rb") as f:
            res = requests.post(endpoint, files={"file": f}, data={"folder": "shayari"}, auth=(parsed.username, parsed.password)).json()
            return res.get("secure_url")
    else:
        # Default Tempfile hosting
        with open(path, "rb") as f:
            res = requests.post("https://tempfile.org/api/upload/local", files={"files": (os.path.basename(path), f)}).json()
            if res.get("success"):
                return f"{res['files'][0]['url'].rstrip('/')}/download"
    raise RuntimeError("Media host upload failed.")

def post_to_instagram(media_path: str, caption: str, is_video: bool = False) -> bool:
    media_url = upload_public_media(media_path)
    
    # 1. Create Container
    payload = {
        "access_token": INSTAGRAM_ACCESS_TOKEN,
        "caption": caption
    }
    if is_video:
        payload["media_type"] = "REELS"
        payload["video_url"] = media_url
    else:
        payload["image_url"] = media_url

    c_res = requests.post(f"https://graph.instagram.com/v21.0/{INSTAGRAM_USER_ID}/media", data=payload).json()
    container_id = c_res.get("id")
    if not container_id:
        print(f"❌ Container Error: {c_res}")
        return False

    # 2. Poll Processing for Reels
    if is_video:
        for _ in range(15):
            time.sleep(10)
            status = requests.get(f"https://graph.instagram.com/v21.0/{container_id}?fields=status_code&access_token={INSTAGRAM_ACCESS_TOKEN}").json()
            if status.get("status_code") == "FINISHED":
                break

    # 3. Publish
    p_res = requests.post(f"https://graph.instagram.com/v21.0/{INSTAGRAM_USER_ID}/media_publish", data={"creation_id": container_id, "access_token": INSTAGRAM_ACCESS_TOKEN}).json()
    if "id" in p_res:
        print(f"🎉 Published Successfully! Post ID: {p_res['id']}")
        return True
    return False

# ============================================================
# STATE TRACKING
# ============================================================
def load_progress() -> dict:
    if os.path.exists("progress.json"):
        with open("progress.json") as f: return json.load(f)
    return {"poet_index": 0, "total_posts": 0}

def save_progress(p: dict):
    with open("progress.json", "w") as f: json.dump(p, f, indent=2)

# ============================================================
# MAIN PIPELINE
# ============================================================
def run():
    p = load_progress()
    poet = POET_SCHEDULE[p["poet_index"] % len(POET_SCHEDULE)]

    # Reuse morning content for evening Reel if available
    if POST_TYPE == "reel" and p.get("today_content"):
        data = p["today_content"]
    else:
        data = generate_content(poet)

    # High-SEO & Share-Driven Caption
    caption = f"{data.get('hook')}\n\n{data['sher_roman']}\n\n-- {poet['name']}\n\n{data['caption']}\n\n#urdushayari #poetry #relatable #shayari"

    if POST_TYPE == "photo":
        img_path = create_photo_image(data, poet)
        success = post_to_instagram(img_path, caption, is_video=False)
        if success:
            p["today_content"] = data
            p["poet_index"] += 1

    elif POST_TYPE == "reel":
        tts_path = f"output/tts_{int(time.time())}.mp3"
        os.makedirs("output", exist_ok=True)
        generate_tts(data["sher_urdu"], tts_path)
        
        reel_path = create_reel_video(data, poet, tts_path)
        if reel_path:
            success = post_to_instagram(reel_path, caption, is_video=True)
            if success: p["today_content"] = None

    if success:
        p["total_posts"] += 1
        save_progress(p)

if __name__ == "__main__":
    validate_environment()
    run()
   
