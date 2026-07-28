# -*- coding: utf-8 -*-
"""
Shayari Instagram Bot v5.5 (Unsplash + Pexels Cross-Fallback Dual Engine)
- Real authentic Shayari via Gemini 2.5 Flash
- Dynamic cross-fallback media engine for both Photos & Reels (Unsplash <-> Pexels)
- Pillow ANTIALIAS monkeypatch for MoviePy compatibility
- Unbuffered execution for transparent GitHub Actions logging
"""

# ============================================================
# PILLOW MONKEYPATCH (Fixes MoviePy 'Image has no attribute ANTIALIAS')
# ============================================================
import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = getattr(PIL.Image, 'Resampling', PIL.Image).LANCZOS

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
from urllib.parse import urlparse

# Ensure unbuffered stdout for GitHub Actions logs
sys.stdout.reconfigure(line_buffering=True)

# ============================================================
# CONFIGURATION
# ============================================================
GEMINI_API_KEY         = os.environ.get("GEMINI_API_KEY", "")
INSTAGRAM_ACCESS_TOKEN = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
INSTAGRAM_USER_ID      = os.environ.get("INSTAGRAM_USER_ID", "")
PEXELS_API_KEY         = os.environ.get("PEXELS_API_KEY", "")
UNSPLASH_ACCESS_KEY    = os.environ.get("UNSPLASH_ACCESS_KEY", "")
MEDIA_HOST             = os.environ.get("MEDIA_HOST", "tempfile").lower()
CLOUDINARY_URL         = os.environ.get("CLOUDINARY_URL", "")
POST_TYPE              = os.environ.get("POST_TYPE", "photo").lower()
IG_HANDLE              = "@ak_apak"

REQUIRED_ENV_VARS = ["GEMINI_API_KEY", "INSTAGRAM_ACCESS_TOKEN", "INSTAGRAM_USER_ID"]

def validate_environment():
    missing = [name for name in REQUIRED_ENV_VARS if not os.environ.get(name)]
    if missing:
        print(f"❌ FATAL: Missing required secret(s): {', '.join(missing)}")
        sys.exit(1)

FONT_SERIF  = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
FONT_ITALIC = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf"
FONT_SANS   = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

POET_SCHEDULE = [
    {"name": "Mirza Ghalib", "era": "1797-1869"},
    {"name": "Mir Taqi Mir", "era": "1723-1810"},
    {"name": "Jaun Elia", "era": "1931-2002"},
    {"name": "Faiz Ahmed Faiz", "era": "1911-1984"},
    {"name": "Ahmad Faraz", "era": "1931-2008"},
    {"name": "Parveen Shakir", "era": "1952-1994"},
    {"name": "Rahat Indori", "era": "1950-2020"},
    {"name": "Gulzar", "era": "1934-"}
]

EMOTION_PALETTES = {
    "ishq":     {"bg":"#1a0010","text":"#f5c6d0","accent":"#e8587a","sub":"#b03060"},
    "dard":     {"bg":"#0a0a1a","text":"#c8d4e8","accent":"#7090d0","sub":"#405080"},
    "tanhai":   {"bg":"#060d0d","text":"#b8d8d8","accent":"#40a0a0","sub":"#206060"}
}
DEFAULT_PALETTE = EMOTION_PALETTES["dard"]

VIRAL_HOOKS = [
    "Read this twice if you're missing someone silently...",
    "When {poet_name} said this, it hit differently...",
    "For the nights when words fail you...",
    "Send this to someone you can't text anymore."
]

# ============================================================
# STEP 1: Gemini AI Content Generator
# ============================================================
def generate_content(poet: dict) -> dict:
    print(f"🧠 Querying Gemini AI for poet: {poet['name']}...")
    client = genai.Client(api_key=GEMINI_API_KEY)
    hook = random.choice(VIRAL_HOOKS).format(poet_name=poet['name'])

    prompt = (
        f"You run a high-engagement Instagram Shayari page.\n"
        f"Poet: {poet['name']} ({poet['era']})\n\n"
        "RULES:\n"
        f"1. Give ONE famous 2-line couplet (sher) strictly by {poet['name']}.\n"
        "2. Roman Urdu transliteration (sher_roman) - MAX 2 lines.\n"
        "3. Exact Urdu script (sher_urdu) for audio synthesis.\n"
        "4. Poetic English translation (english_translation) - MAX 1 line.\n"
        "5. Search query (search_query) for dark aesthetic background imagery (e.g., 'dark rain night', 'misty road', 'coffee shadow', 'vintage book').\n"
        "6. Short caption story.\n\n"
        "Return ONLY valid JSON:\n"
        "{\n"
        f'  "hook": "{hook}",\n'
        '  "sher_roman": "Line 1\\nLine 2",\n'
        '  "sher_urdu": "...",\n'
        '  "english_translation": "...",\n'
        '  "emotion": "dard",\n'
        '  "search_query": "dark rain night",\n'
        '  "caption": "..."\n'
        "}"
    )

    response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    raw = response.text.strip().replace("```json","").replace("```","").strip()
    data = json.loads(raw)
    print(f"✅ Generated Sher successfully: {data.get('sher_roman', '')[:40]}...")
    return data

# ============================================================
# STEP 2: Dual Media Engine (Unsplash + Pexels with Cross-Fallback)
# ============================================================
def fetch_unsplash_photo(query: str) -> str:
    if not UNSPLASH_ACCESS_KEY:
        return None
    try:
        print(f"📷 Fetching photo from Unsplash: '{query}'...")
        headers = {"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"}
        url = f"https://api.unsplash.com/photos/random?query={query}&orientation=squarish"
        res = requests.get(url, headers=headers, timeout=10)
        if res.ok:
            img_url = res.json().get("urls", {}).get("regular")
            if img_url:
                p_path = f"output/unsplash_{int(time.time())}.jpg"
                with open(p_path, "wb") as f:
                    f.write(requests.get(img_url, timeout=30).content)
                print(f"✅ Downloaded Unsplash Photo: {p_path}")
                return p_path
    except Exception as e:
        print(f"⚠️ Unsplash photo fetch error: {e}")
    return None

def fetch_pexels_photo(query: str) -> str:
    if not PEXELS_API_KEY:
        return None
    try:
        print(f"📷 Fetching photo from Pexels: '{query}'...")
        headers = {"Authorization": PEXELS_API_KEY}
        url = f"https://api.pexels.com/v1/search?query={query}&orientation=square&per_page=5"
        res = requests.get(url, headers=headers, timeout=10)
        if res.ok:
            photos = res.json().get("photos", [])
            if photos:
                img_url = random.choice(photos).get("src", {}).get("large2x")
                if img_url:
                    p_path = f"output/pexels_img_{int(time.time())}.jpg"
                    with open(p_path, "wb") as f:
                        f.write(requests.get(img_url, timeout=30).content)
                    print(f"✅ Downloaded Pexels Photo: {p_path}")
                    return p_path
    except Exception as e:
        print(f"⚠️ Pexels photo fetch error: {e}")
    return None

def get_photo_background(query: str) -> str:
    """Randomly chooses Unsplash or Pexels as primary, using the other as fallback."""
    os.makedirs("output", exist_ok=True)
    providers = [fetch_unsplash_photo, fetch_pexels_photo]
    random.shuffle(providers) # Randomize primary provider

    for fetch_func in providers:
        img_path = fetch_func(query)
        if img_path and os.path.exists(img_path):
            return img_path

    print("ℹ️ Both Unsplash and Pexels failed for photo. Using dark solid background fallback.")
    return None

def fetch_pexels_video(query: str) -> str:
    if not PEXELS_API_KEY:
        return None
    try:
        print(f"🎬 Fetching video from Pexels: '{query}'...")
        headers = {"Authorization": PEXELS_API_KEY}
        url = f"https://api.pexels.com/videos/search?query={query}&orientation=portrait&per_page=5"
        res = requests.get(url, headers=headers, timeout=10)
        if res.ok:
            videos = res.json().get("videos", [])
            if videos:
                video = random.choice(videos)
                for vf in video.get("video_files", []):
                    if vf.get("file_type") == "video/mp4" and vf.get("width", 0) >= 720:
                        v_path = f"output/pexels_vid_{int(time.time())}.mp4"
                        with open(v_path, "wb") as f:
                            f.write(requests.get(vf["link"], timeout=30).content)
                        print(f"✅ Downloaded Pexels Video: {v_path}")
                        return v_path
    except Exception as e:
        print(f"⚠️ Pexels video fetch error: {e}")
    return None

def fetch_unsplash_video_equivalent(query: str) -> str:
    """
    Unsplash does not provide videos, so it converts a high-res portrait photo
    from Unsplash into a background image for video compositing.
    """
    if not UNSPLASH_ACCESS_KEY:
        return None
    try:
        print(f"🎬 Fetching vertical image from Unsplash for Reel: '{query}'...")
        headers = {"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"}
        url = f"https://api.unsplash.com/photos/random?query={query}&orientation=portrait"
        res = requests.get(url, headers=headers, timeout=10)
        if res.ok:
            img_url = res.json().get("urls", {}).get("regular")
            if img_url:
                p_path = f"output/unsplash_portrait_{int(time.time())}.jpg"
                with open(p_path, "wb") as f:
                    f.write(requests.get(img_url, timeout=30).content)
                print(f"✅ Downloaded Unsplash Portrait Image for Reel: {p_path}")
                return p_path
    except Exception as e:
        print(f"⚠️ Unsplash vertical image fetch error: {e}")
    return None

def get_reel_background(query: str) -> tuple:
    """
    Returns (path, is_video_file).
    Randomly attempts Pexels Video or Unsplash Portrait Image with cross-fallback.
    """
    os.makedirs("output", exist_ok=True)
    
    # Try Video First (Pexels) 50% of the time, or Vertical Unsplash Image 50% of the time
    choice = random.choice(["pexels", "unsplash"])

    if choice == "pexels":
        v_path = fetch_pexels_video(query)
        if v_path: return (v_path, True)
        u_path = fetch_unsplash_video_equivalent(query)
        if u_path: return (u_path, False)
    else:
        u_path = fetch_unsplash_video_equivalent(query)
        if u_path: return (u_path, False)
        v_path = fetch_pexels_video(query)
        if v_path: return (v_path, True)

    print("ℹ️ Both video sources failed. Using clean dark canvas fallback.")
    return (None, False)

# ============================================================
# STEP 3: Photo Renderer (1080x1080)
# ============================================================
def create_photo_image(data: dict, poet: dict) -> str:
    print("🎨 Rendering 1080x1080 Photo Image...")
    W, H = 1080, 1080
    palette = EMOTION_PALETTES.get(data.get("emotion","dard"), DEFAULT_PALETTE)

    bg_photo_path = get_photo_background(data.get("search_query", "dark rain"))

    if bg_photo_path and os.path.exists(bg_photo_path):
        base_img = Image.open(bg_photo_path).convert("RGBA")
        base_img = base_img.resize((W, H), Image.Resampling.LANCZOS)
        dark_overlay = Image.new("RGBA", (W, H), (10, 10, 20, 160)) # Translucent dark overlay
        img = Image.alpha_composite(base_img, dark_overlay).convert("RGB")
    else:
        img = Image.new("RGB", (W, H), color=palette["bg"])

    draw = ImageDraw.Draw(img)

    try:
        font_poet  = ImageFont.truetype(FONT_SERIF, 32)
        font_sher  = ImageFont.truetype(FONT_SERIF, 44)
        font_trans = ImageFont.truetype(FONT_ITALIC, 22)
        font_brand = ImageFont.truetype(FONT_SANS, 18)
    except:
        font_poet = font_sher = font_trans = font_brand = ImageFont.load_default()

    def center(text, y, font, color):
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        draw.text(((W - tw) / 2, y), text, font=font, fill=color)

    center(f"-- {poet['name']} --", 120, font_poet, "#E0C080")
    
    lines = data["sher_roman"].strip().split("\n")
    y_pos = 380
    for line in lines:
        for wline in textwrap.wrap(line, width=32):
            center(wline, y_pos, font_sher, "#FFFFFF")
            y_pos += 65

    y_pos += 50
    for tline in textwrap.wrap(f'"{data["english_translation"]}"', width=48):
        center(tline, y_pos, font_trans, "#D0D0D0")
        y_pos += 35

    center(IG_HANDLE, 960, font_brand, "#AAAAAA")

    fname = f"output/photo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    img.save(fname, "JPEG", quality=95)
    print(f"✅ Photo rendered at: {fname}")
    return fname

# ============================================================
# STEP 4: Edge TTS Audio Generator
# ============================================================
def generate_tts(text: str, output_path: str) -> bool:
    print("🎙️ Generating Urdu Edge-TTS audio...")
    try:
        import asyncio
        import edge_tts

        async def _speak():
            communicate = edge_tts.Communicate(text, "ur-PK-AsadNeural", rate="-10%", pitch="-4Hz")
            await communicate.save(output_path)

        asyncio.run(_speak())
        print(f"✅ Audio generated at: {output_path}")
        return True
    except Exception as e:
        print(f"❌ Edge-TTS Audio Generation Failed: {e}")
        return False

# ============================================================
# STEP 5: Reel Video Studio
# ============================================================
def create_reel_video(data: dict, poet: dict, tts_path: str) -> str:
    print("🎬 Compositing 1080x1920 Reel Video with MoviePy...")
    try:
        from moviepy.editor import VideoFileClip, AudioFileClip, CompositeVideoClip, ImageClip, CompositeAudioClip
        import numpy as np

        tts_audio = AudioFileClip(tts_path)
        duration = min(tts_audio.duration + 3, 30)

        # 1. Background Media Setup
        bg_path, is_video = get_reel_background(data.get("search_query", "dark rain"))
        
        if bg_path and is_video:
            bg_clip = VideoFileClip(bg_path).subclip(0, duration).resize(height=1920)
            if bg_clip.w < 1080: bg_clip = bg_clip.resize(width=1080)
            bg_clip = bg_clip.crop(x_center=bg_clip.w/2, y_center=bg_clip.h/2, width=1080, height=1920)
            bg_clip = bg_clip.fl_image(lambda image: (image * 0.4).astype(np.uint8))
        elif bg_path and not is_video:
            bg_img = Image.open(bg_path).convert("RGBA").resize((1080, 1920), Image.Resampling.LANCZOS)
            dark_overlay = Image.new("RGBA", (1080, 1920), (10, 10, 20, 160))
            bg_img = Image.alpha_composite(bg_img, dark_overlay).convert("RGB")
            bg_img_path = "output/reel_bg_img.jpg"
            bg_img.save(bg_img_path)
            bg_clip = ImageClip(bg_img_path, duration=duration)
        else:
            clean_bg = Image.new("RGB", (1080, 1920), color="#0a0a14")
            clean_bg_path = "output/clean_bg.jpg"
            clean_bg.save(clean_bg_path)
            bg_clip = ImageClip(clean_bg_path, duration=duration)

        # 2. Audio Layering
        music_dir = "music"
        final_audio = tts_audio
        if os.path.exists(music_dir):
            tracks = [os.path.join(music_dir, f) for f in os.listdir(music_dir) if f.endswith(".mp3")]
            if tracks:
                music = AudioFileClip(random.choice(tracks)).subclip(0, duration).volumex(0.15)
                final_audio = CompositeAudioClip([tts_audio.volumex(1.0), music])

        # 3. Transparent Text Overlay Layer
        overlay_img = Image.new("RGBA", (1080, 1920), (0,0,0,0))
        draw = ImageDraw.Draw(overlay_img)
        
        try:
            font_hook = ImageFont.truetype(FONT_ITALIC, 32)
            font_sher = ImageFont.truetype(FONT_SERIF, 48)
            font_poet = ImageFont.truetype(FONT_SERIF, 32)
        except:
            font_hook = font_sher = font_poet = ImageFont.load_default()

        # Draw Hook
        hook_text = textwrap.fill(data.get("hook", ""), width=32)
        draw.text((540, 380), hook_text, font=font_hook, fill="#E0E0E0", anchor="mm", align="center")

        # Draw Sher
        sher_text = data["sher_roman"]
        draw.text((540, 960), sher_text, font=font_sher, fill="#FFFFFF", anchor="mm", align="center")

        # Draw Poet & Brand
        draw.text((540, 1400), f"-- {poet['name']} --", font=font_poet, fill="#C0A060", anchor="mm")
        draw.text((540, 1750), IG_HANDLE, font=font_poet, fill="#888888", anchor="mm")

        overlay_fname = f"output/overlay_{int(time.time())}.png"
        overlay_img.save(overlay_fname)

        txt_clip = ImageClip(overlay_fname, duration=duration)

        # 4. Composite Video
        final_video = CompositeVideoClip([bg_clip, txt_clip]).set_audio(final_audio)
        reel_path = f"output/reel_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        
        final_video.write_videofile(reel_path, fps=24, codec="libx264", audio_codec="aac", verbose=False, logger=None)
        print(f"✅ Reel video created: {reel_path}")
        return reel_path

    except Exception as e:
        print(f"❌ Video render failure: {e}")
        return None

# ============================================================
# STEP 6: Media Hosting & Instagram Publishing
# ============================================================
def upload_public_media(path: str) -> str:
    print(f"☁️ Hosting public media file: {path}...")
    if MEDIA_HOST == "cloudinary" and CLOUDINARY_URL:
        parsed = urlparse(CLOUDINARY_URL)
        endpoint = f"https://api.cloudinary.com/v1_1/{parsed.hostname}/auto/upload"
        with open(path, "rb") as f:
            res = requests.post(endpoint, files={"file": f}, data={"folder": "shayari"}, auth=(parsed.username, parsed.password)).json()
            url = res.get("secure_url")
            print(f"✅ Uploaded to Cloudinary: {url}")
            return url
    else:
        with open(path, "rb") as f:
            res = requests.post("https://tempfile.org/api/upload/local", files={"files": (os.path.basename(path), f)}).json()
            if res.get("success"):
                url = f"{res['files'][0]['url'].rstrip('/')}/download"
                print(f"✅ Uploaded to TempFile: {url}")
                return url
    raise RuntimeError("Public media upload failed.")

def post_to_instagram(media_path: str, caption: str, is_video: bool = False) -> bool:
    try:
        media_url = upload_public_media(media_path)

        payload = {
            "access_token": INSTAGRAM_ACCESS_TOKEN,
            "caption": caption
        }
        if is_video:
            payload["media_type"] = "REELS"
            payload["video_url"] = media_url
        else:
            payload["image_url"] = media_url

        print("📡 Creating Instagram Media Container...")
        c_res = requests.post(f"https://graph.instagram.com/v21.0/{INSTAGRAM_USER_ID}/media", data=payload).json()
        container_id = c_res.get("id")
        
        if not container_id:
            print(f"❌ Instagram Container Error: {c_res}")
            return False

        if is_video:
            print("⏳ Polling Instagram Reels processing status...")
            for attempt in range(1, 21):
                time.sleep(10)
                status = requests.get(f"https://graph.instagram.com/v21.0/{container_id}?fields=status_code&access_token={INSTAGRAM_ACCESS_TOKEN}").json()
                code = status.get("status_code")
                print(f"   [{attempt}/20] Status: {code}")
                if code == "FINISHED":
                    break
                elif code == "ERROR":
                    print("❌ Instagram Video Processing Failed.")
                    return False

        print("📤 Publishing to Instagram...")
        p_res = requests.post(f"https://graph.instagram.com/v21.0/{INSTAGRAM_USER_ID}/media_publish", data={"creation_id": container_id, "access_token": INSTAGRAM_ACCESS_TOKEN}).json()
        if "id" in p_res:
            print(f"🎉 
