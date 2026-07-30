# -*- coding: utf-8 -*-
"""
Brain Blueprints Instagram Bot v1.0
- High-retention Psychology & Behavioral Science content via Gemini 2.0 Flash
- Rotating Viral Frameworks: Listicle, If/Then, Infinite Loop
- Cinematic English Voiceover via ElevenLabs API (Marcus)
- Dynamic Background Engine (Pexels Video / Unsplash Photo)
- Pillow ANTIALIAS monkeypatch for MoviePy compatibility
"""

# ============================================================
# PILLOW MONKEYPATCH (Fixes MoviePy 'Image has no attribute ANTIALIAS')
# ============================================================
import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = getattr(PIL.Image, 'Resampling', PIL.Image).LANCZOS

import google.generativeai as genai
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
# CONFIGURATION & CONSTANTS
# ============================================================
GEMINI_API_KEY         = os.environ.get("GEMINI_API_KEY", "")
INSTAGRAM_ACCESS_TOKEN = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
INSTAGRAM_USER_ID      = os.environ.get("INSTAGRAM_USER_ID", "")
PEXELS_API_KEY         = os.environ.get("PEXELS_API_KEY", "")
UNSPLASH_ACCESS_KEY    = os.environ.get("UNSPLASH_ACCESS_KEY", "")
ELEVENLABS_API_KEY     = os.environ.get("ELEVENLABS_API_KEY", "")
MEDIA_HOST             = os.environ.get("MEDIA_HOST", "tempfile").lower()
CLOUDINARY_URL         = os.environ.get("CLOUDINARY_URL", "")
POST_TYPE              = os.environ.get("POST_TYPE", "reel").lower()

IG_HANDLE              = "@brain.blueprints"
ELEVENLABS_VOICE_ID    = "bVMeCyTHy58xNoL34h3p"  # Marcus (Authoritative Deep English)

REQUIRED_ENV_VARS = ["GEMINI_API_KEY", "INSTAGRAM_ACCESS_TOKEN", "INSTAGRAM_USER_ID"]

def validate_environment():
    missing = [name for name in REQUIRED_ENV_VARS if not os.environ.get(name)]
    if missing:
        print(f"❌ FATAL: Missing required secret(s): {', '.join(missing)}")
        sys.exit(1)

FONT_SERIF  = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
FONT_ITALIC = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf"
FONT_SANS   = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

# ============================================================
# STEP 1: Gemini AI Content Generator (Rotating Frameworks)
# ============================================================
def generate_content() -> dict:
    """Generates viral high-retention psychology content using 3 rotating frameworks."""
    print(f"🧠 Querying Gemini AI for @brain.blueprints content...")
    genai.configure(api_key=GEMINI_API_KEY)
    
    frameworks = [
        {
            "type": "listicle",
            "system_prompt": """Act as an expert behavioral psychologist. 
Write a high-retention 3-part micro-listicle about dark psychology, body language, or social dynamics.
Rules:
1. The hook MUST promise that the 3rd point is the most important, dangerous, or shocking.
2. Keep each point under 12 words so it reads fast on mobile screens.
3. Total audio length must be under 12 seconds.

Return strictly valid JSON:
{
  "hook": "3 body language signs someone is lying. Number 3 is almost impossible to fake...",
  "script_english": "1. They stop making eye contact when answering.\\n2. Their speech speed suddenly changes.\\n3. They touch their neck to unconsciously soothe anxiety.",
  "search_query": "dark moody city night street lights rain",
  "caption": "Which of these have you noticed before? 🧠\\n\\nFollow @brain.blueprints for daily psychological insights."
}"""
        },
        {
            "type": "if_then",
            "system_prompt": """Act as a psychoanalyst. 
Write a deeply relatable 2-part 'If / Then' statement about human insecurity, habit, or social instinct.
Rules:
1. The 'If' statement must describe a very specific human behavior viewers thought only they did.
2. The 'Then' statement must provide a mind-blowing psychological root cause.
3. Total script must be under 15 seconds.

Return strictly valid JSON:
{
  "hook": "If you do this, read carefully...",
  "script_english": "If you randomly lose feelings for someone the moment they show interest in you...\\n\\nThen you don't fear commitment. You fear vulnerability because you believe your true self is unlovable.",
  "search_query": "foggy forest moody dark landscape shadow",
  "caption": "Save this for when you need a reality check. 🧠\\n\\nFollow @brain.blueprints for daily psychological insights."
}"""
        },
        {
            "type": "infinite_loop",
            "system_prompt": """Act as a social tactics expert. 
Write a punchy, 3-sentence psychological tip for commanding respect or detecting deception.
Rules:
1. CRITICAL: The very last sentence MUST end mid-thought or grammatically flow directly into the first word of the hook to create an unnoticeable 100% audio loop!
2. Keep it under 10 seconds total.

Return strictly valid JSON:
{
  "hook": "2 tricks to instantly command a room...",
  "script_english": "First, lower your tone at the end of sentences instead of raising it. Second, never break eye contact first during silence... which is why you need these...",
  "search_query": "chess board dark lighting luxury minimal",
  "caption": "Let the video loop twice to get it. 🧠\\n\\nFollow @brain.blueprints for daily psychological insights."
}"""
        }
    ]

    selected = random.choice(frameworks)
    print(f"🎯 Selected Strategy: [{selected['type'].upper()}]")

    
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content(selected["system_prompt"])
    
    raw = response.text.strip().replace("```json", "").replace("```", "").strip()
    data = json.loads(raw)
    print(f"✅ Content generated successfully: '{data.get('hook', '')}'")
    return data

# ============================================================
# STEP 2: Dual Media Engine (Unsplash + Pexels Cross-Fallback)
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
    os.makedirs("output", exist_ok=True)
    providers = [fetch_unsplash_photo, fetch_pexels_photo]
    random.shuffle(providers)

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
    os.makedirs("output", exist_ok=True)
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
def create_photo_image(data: dict) -> str:
    print("🎨 Rendering 1080x1080 Photo Image...")
    W, H = 1080, 1080

    bg_photo_path = get_photo_background(data.get("search_query", "dark moody city"))

    if bg_photo_path and os.path.exists(bg_photo_path):
        base_img = Image.open(bg_photo_path).convert("RGBA")
        base_img = base_img.resize((W, H), Image.Resampling.LANCZOS)
        dark_overlay = Image.new("RGBA", (W, H), (10, 10, 20, 180))
        img = Image.alpha_composite(base_img, dark_overlay).convert("RGB")
    else:
        img = Image.new("RGB", (W, H), color="#0a0a14")

    draw = ImageDraw.Draw(img)

    try:
        font_hook  = ImageFont.truetype(FONT_ITALIC, 32)
        font_body  = ImageFont.truetype(FONT_SERIF, 40)
        font_brand = ImageFont.truetype(FONT_SANS, 22)
    except:
        font_hook = font_body = font_brand = ImageFont.load_default()

    def center(text, y, font, color):
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        draw.text(((W - tw) / 2, y), text, font=font, fill=color)

    center(data.get("hook", ""), 150, font_hook, "#C0A060")
    
    lines = data["script_english"].strip().split("\n")
    y_pos = 360
    for line in lines:
        for wline in textwrap.wrap(line, width=32):
            center(wline, y_pos, font_body, "#FFFFFF")
            y_pos += 55

    center(IG_HANDLE, 960, font_brand, "#888888")

    fname = f"output/photo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    img.save(fname, "JPEG", quality=95)
    print(f"✅ Photo rendered at: {fname}")
    return fname

# ============================================================
# STEP 4: Audio Engine (ElevenLabs English Voice)
# ============================================================
def generate_tts(data: dict) -> list:
    """Generates continuous TTS audio for the script using ElevenLabs."""
    print(f"🎙️ Attempting Cinematic ElevenLabs Audio (Voice ID: {ELEVENLABS_VOICE_ID})...")
    os.makedirs("output", exist_ok=True)
    
    full_text = f"{data['hook']}... {data['script_english']}"
    out_path = f"output/tts_full_{int(time.time())}.mp3"
    
    if ELEVENLABS_API_KEY:
        try:
            from elevenlabs.client import ElevenLabs
            
            client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
            audio_stream = client.text_to_speech.convert(
                text=full_text,
                voice_id=ELEVENLABS_VOICE_ID,
                model_id="eleven_multilingual_v2",
                output_format="mp3_44100_128"
            )
            
            with open(out_path, "wb") as f:
                for chunk in audio_stream:
                    if chunk:
                        f.write(chunk)
                        
            print(f"✅ ElevenLabs Audio generated successfully: {out_path}")
            return [out_path]
            
        except Exception as e:
            print(f"❌ ElevenLabs Failed ({e}).")
            
    return []

# ============================================================
# STEP 5: Reel Video Studio
# ============================================================
def create_reel_video(data: dict, tts_paths: list) -> str:
    print("🎬 Compositing 1080x1920 Reel Video with MoviePy...")
    try:
        from moviepy.editor import VideoFileClip, AudioFileClip, CompositeVideoClip, ImageClip, CompositeAudioClip
        import numpy as np

        # 1. Load TTS Audio
        tts_audio = AudioFileClip(tts_paths[0])
        duration = min(tts_audio.duration + 2, 30)

        # 2. Background Setup
        bg_path, is_video = get_reel_background(data.get("search_query", "dark moody city"))
        
        if bg_path and is_video:
            bg_clip = VideoFileClip(bg_path).subclip(0, duration).resize(height=1920)
            if bg_clip.w < 1080: bg_clip = bg_clip.resize(width=1080)
            bg_clip = bg_clip.crop(x_center=bg_clip.w/2, y_center=bg_clip.h/2, width=1080, height=1920)
            bg_clip = bg_clip.fl_image(lambda image: (image * 0.35).astype(np.uint8))
        elif bg_path and not is_video:
            bg_img = Image.open(bg_path).convert("RGBA").resize((1080, 1920), Image.Resampling.LANCZOS)
            dark_overlay = Image.new("RGBA", (1080, 1920), (10, 10, 20, 180))
            bg_img = Image.alpha_composite(bg_img, dark_overlay).convert("RGB")
            bg_img_path = f"output/reel_bg_img_{int(time.time())}.jpg"
            bg_img.save(bg_img_path)
            bg_clip = ImageClip(bg_img_path, duration=duration)
        else:
            clean_bg = Image.new("RGB", (1080, 1920), color="#0a0a14")
            clean_bg_path = f"output/clean_bg_{int(time.time())}.jpg"
            clean_bg.save(clean_bg_path)
            bg_clip = ImageClip(clean_bg_path, duration=duration)

        # 3. Audio Layering (Voice + Background Music)
        music_dir = "music"
        final_audio = tts_audio
        if os.path.exists(music_dir):
            tracks = [os.path.join(music_dir, f) for f in os.listdir(music_dir) if f.endswith(".mp3")]
            if tracks:
                music = AudioFileClip(random.choice(tracks)).subclip(0, duration).volumex(0.12)
                final_audio = CompositeAudioClip([tts_audio.volumex(1.0), music])

        # 4. Transparent Text Overlay Layer
        overlay_img = Image.new("RGBA", (1080, 1920), (0,0,0,0))
        draw = ImageDraw.Draw(overlay_img)
        
        try:
            font_hook  = ImageFont.truetype(FONT_ITALIC, 34)
            font_body  = ImageFont.truetype(FONT_SERIF, 44)
            font_brand = ImageFont.truetype(FONT_SANS, 28)
        except:
            font_hook = font_body = font_brand = ImageFont.load_default()

        # Draw Hook
        hook_text = textwrap.fill(data.get("hook", ""), width=30)
        draw.text((540, 360), hook_text, font=font_hook, fill="#E0C080", anchor="mm", align="center")

        # Draw Main Script (Text wrapped for mobile boundaries)
        body_lines = data["script_english"].strip().split("\n")
        wrapped_lines = []
        for line in body_lines:
            if line.strip():
                wrapped_lines.extend(textwrap.wrap(line, width=28))
            else:
                wrapped_lines.append("")
        
        final_body_text = "\n".join(wrapped_lines)
        draw.text((540, 960), final_body_text, font=font_body, fill="#FFFFFF", anchor="mm", align="center", spacing=22)

        # Draw Brand Handle
        draw.text((540, 1720), IG_HANDLE, font=font_brand, fill="#888888", anchor="mm")

        overlay_fname = f"output/overlay_{int(time.time())}.png"
        overlay_img.save(overlay_fname)

        txt_clip = ImageClip(overlay_fname, duration=duration)

        # 5. Composite Final Video
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
            res = requests.post(endpoint, files={"file": f}, data={"folder": "brain_blueprints"}, auth=(parsed.username, parsed.password)).json()
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
        else:
            print("⏳ Waiting 15 seconds for Instagram to process photo...")
            time.sleep(15)

        print("📤 Publishing to Instagram...")
        p_res = requests.post(f"https://graph.instagram.com/v21.0/{INSTAGRAM_USER_ID}/media_publish", data={"creation_id": container_id, "access_token": INSTAGRAM_ACCESS_TOKEN}).json()
        if "id" in p_res:
            print(f"🎉 Published Successfully! Instagram Post ID: {p_res['id']}")
            return True
        else:
            print(f"❌ Instagram Publish Error: {p_res}")
            return False

    except Exception as e:
        print(f"❌ Instagram API Failure: {e}")
        return False

# ============================================================
# STATE TRACKING
# ============================================================
def load_progress() -> dict:
    if os.path.exists("progress.json"):
        with open("progress.json") as f: return json.load(f)
    return {"total_posts": 0}

def save_progress(p: dict):
    with open("progress.json", "w") as f: json.dump(p, f, indent=2)

# ============================================================
# MAIN EXECUTION
# ============================================================
def run():
    validate_environment()
    p = load_progress()

    print(f"\n=======================================================")
    print(f"🚀 STARTING WORKFLOW: [{POST_TYPE.upper()}] for {IG_HANDLE}")
    print(f"=======================================================\n")

    data = generate_content()
    caption = f"{data.get('caption', '')}\n\n#psychology #humanbehavior #mindset #darkpsychology #brainblueprints #relatable"

    success = False

    if POST_TYPE == "photo":
        img_path = create_photo_image(data)
        success = post_to_instagram(img_path, caption, is_video=False)

    elif POST_TYPE == "reel":
        os.makedirs("output", exist_ok=True)
        tts_paths = generate_tts(data)
        
        if not tts_paths:
            print("❌ FATAL: TTS audio failed. Exiting.")
            sys.exit(1)

        reel_path = create_reel_video(data, tts_paths)
        
        if reel_path:
            success = post_to_instagram(reel_path, caption, is_video=True)
        else:
            print("❌ FATAL: Reel video rendering failed.")
            sys.exit(1)

    if success:
        p["total_posts"] += 1
        save_progress(p)
        print("\n✅ WORKFLOW COMPLETED SUCCESSFULLY!")
    else:
        print("\n❌ WORKFLOW FAILED TO POST TO INSTAGRAM.")
        sys.exit(1)

if __name__ == "__main__":
    run()