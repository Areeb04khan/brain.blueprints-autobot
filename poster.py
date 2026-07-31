# -*- coding: utf-8 -*-
"""
Brain Blueprints Bot v6.0 (Multi-Tier AI & TTS Failover Engine)
- AI Chain: Gemini -> OpenRouter -> Groq -> NVIDIA NIM
- TTS Chain: ElevenLabs -> Groq TTS -> OpenRouter TTS -> Edge-TTS
- Fully automated psychology & behavioral reels
"""

import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = getattr(PIL.Image, 'Resampling', PIL.Image).LANCZOS

from google import genai
from openai import OpenAI
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

sys.stdout.reconfigure(line_buffering=True)

# ============================================================
# CONFIGURATION & ENVIRONMENT
# ============================================================
GEMINI_API_KEY         = os.environ.get("GEMINI_API_KEY", "")
OPENROUTER_API_KEY     = os.environ.get("OPENROUTER_API_KEY", "")
GROQ_API_KEY           = os.environ.get("GROQ_API_KEY", "")
NVIDIA_API_KEY         = os.environ.get("NVIDIA_API_KEY", "")
ELEVENLABS_API_KEY     = os.environ.get("ELEVENLABS_API_KEY", "")

INSTAGRAM_ACCESS_TOKEN = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
INSTAGRAM_USER_ID      = os.environ.get("INSTAGRAM_USER_ID", "")
PEXELS_API_KEY         = os.environ.get("PEXELS_API_KEY", "")
UNSPLASH_ACCESS_KEY    = os.environ.get("UNSPLASH_ACCESS_KEY", "")
MEDIA_HOST             = os.environ.get("MEDIA_HOST", "tempfile").lower()
POST_TYPE              = os.environ.get("POST_TYPE", "reel").lower()
IG_HANDLE              = "@brain.blueprints"
ELEVENLABS_VOICE_ID    = "pNInz6obpgDQGcFmaJgB"  # Default stable voice

REQUIRED_ENV_VARS = ["INSTAGRAM_ACCESS_TOKEN", "INSTAGRAM_USER_ID"]

def validate_environment():
    missing = [name for name in REQUIRED_ENV_VARS if not os.environ.get(name)]
    if missing:
        print(f"❌ FATAL: Missing required secret(s): {', '.join(missing)}")
        sys.exit(1)
    if not any([GEMINI_API_KEY, OPENROUTER_API_KEY, GROQ_API_KEY, NVIDIA_API_KEY]):
        print("❌ FATAL: At least one AI API key must be provided!")
        sys.exit(1)

FONT_SERIF  = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
FONT_ITALIC = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf"
FONT_SANS   = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

# ============================================================
# MULTI-TIER AI CONTENT GENERATOR (Failover Chain for Psychology)
# ============================================================
def generate_content() -> dict:
    print(f"🧠 Querying AI Chain for @brain.blueprints content...")
    
    prompt = """Act as a social tactics expert and psychological strategist. 
Write a punchy, 3-sentence psychological tip for commanding respect, reading body language, or detecting dark manipulation.
Rules:
1. CRITICAL: The very last sentence MUST end mid-thought or grammatically flow directly into the first word of the hook to create an unnoticeable 100% audio loop!
2. Keep it under 10 seconds total spoken length.

Return strictly valid JSON:
{
  "hook": "2 tricks to instantly command a room...",
  "script_english": "First, lower your tone at the end of sentences instead of raising it. Second, never break eye contact first during silence... which is why you need these...",
  "search_query": "chess board dark lighting luxury minimal",
  "caption": "Let the video loop twice to get it. 🧠\\n\\nFollow @brain.blueprints for daily psychological insights."
}"""

    # Tier 1: Gemini
    if GEMINI_API_KEY:
        try:
            print(f"🧠 [1/4] Querying Gemini AI...")
            client = genai.Client(api_key=GEMINI_API_KEY)
            response = client.models.generate_content(model="gemini-3.5-flash", contents=prompt)
            raw = response.text.strip().replace("```json","").replace("```","").strip()
            data = json.loads(raw)
            print("✅ Generated content successfully via Gemini!")
            return data
        except Exception as e:
            print(f"⚠️ Gemini failed ({e}). Moving to Fallback Chain...")

    # Fallback Providers
    fallbacks = [
        {
            "name": "OpenRouter",
            "api_key": OPENROUTER_API_KEY,
            "base_url": "https://openrouter.ai/api/v1",
            "model": "openrouter/free"
        },
        {
            "name": "Groq",
            "api_key": GROQ_API_KEY,
            "base_url": "https://api.groq.com/openai/v1",
            "model": "llama-3.3-70b-versatile"
        },
        {
            "name": "NVIDIA NIM",
            "api_key": NVIDIA_API_KEY,
            "base_url": "https://integrate.api.nvidia.com/v1",
            "model": "meta/llama-3.1-70b-instruct"
        }
    ]

    for index, provider in enumerate(fallbacks, start=2):
        if not provider["api_key"]:
            continue
        try:
            print(f"🔄 [{index}/4] Trying {provider['name']} Fallback...")
            client = OpenAI(base_url=provider["base_url"], api_key=provider["api_key"])
            response = client.chat.completions.create(
                model=provider["model"],
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            raw = response.choices[0].message.content.strip().replace("```json","").replace("```","").strip()
            data = json.loads(raw)
            print(f"✅ Generated content successfully via {provider['name']}!")
            return data
        except Exception as err:
            print(f"⚠️ {provider['name']} failed: {err}")

    print("❌ FATAL: All AI providers failed.")
    sys.exit(1)

# ============================================================
# MEDIA ENGINE (Pexels + Unsplash)
# ============================================================
def fetch_pexels_video(query: str) -> str:
    if not PEXELS_API_KEY: return None
    try:
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
                        return v_path
    except Exception:
        pass
    return None

def fetch_unsplash_video_equivalent(query: str) -> str:
    if not UNSPLASH_ACCESS_KEY: return None
    try:
        headers = {"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"}
        url = f"https://api.unsplash.com/photos/random?query={query}&orientation=portrait"
        res = requests.get(url, headers=headers, timeout=10)
        if res.ok:
            img_url = res.json().get("urls", {}).get("regular")
            if img_url:
                p_path = f"output/unsplash_portrait_{int(time.time())}.jpg"
                with open(p_path, "wb") as f:
                    f.write(requests.get(img_url, timeout=30).content)
                return p_path
    except Exception:
        pass
    return None

def get_reel_background(query: str) -> tuple:
    os.makedirs("output", exist_ok=True)
    v_path = fetch_pexels_video(query)
    if v_path: return (v_path, True)
    u_path = fetch_unsplash_video_equivalent(query)
    if u_path: return (u_path, False)
    return (None, False)

# ============================================================
# MULTI-TIER TTS FAILOVER ENGINE (English)
# ============================================================
def generate_tts(data: dict) -> list:
    full_text = f"{data['hook']}... {data['script_english']}"
    out_path = f"output/tts_full_{int(time.time())}.mp3"

    # Tier 1: ElevenLabs
    if ELEVENLABS_API_KEY:
        try:
            print("🎙️ [TTS 1/4] Trying ElevenLabs...")
            from elevenlabs.client import ElevenLabs
            client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
            audio_stream = client.text_to_speech.convert(
                text=full_text, voice_id=ELEVENLABS_VOICE_ID,
                model_id="eleven_multilingual_v2", output_format="mp3_44100_128"
            )
            with open(out_path, "wb") as f:
                for chunk in audio_stream:
                    if chunk: f.write(chunk)
            print("✅ ElevenLabs Audio generated successfully!")
            return [out_path]
        except Exception as e:
            print(f"⚠️ ElevenLabs failed ({e}). Moving to Groq TTS...")

    # Tier 2: Groq TTS
    if GROQ_API_KEY:
        try:
            print("🎙️ [TTS 2/4] Trying Groq TTS...")
            client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=GROQ_API_KEY)
            response = client.audio.speech.create(
                model="canopylabs/orpheus-v1-english",
                voice="hannah",
                input=full_text
            )
            response.stream_to_file(out_path)
            print("✅ Groq TTS Audio generated successfully!")
            return [out_path]
        except Exception as e:
            print(f"⚠️ Groq TTS failed ({e}). Moving to Edge-TTS...")

    # Tier 3: Edge-TTS (Bulletproof local safety net)
    try:
        print("🎙️ [TTS 3/4] Generating fallback via Edge-TTS...")
        import asyncio
        import edge_tts
        async def _speak():
            communicate = edge_tts.Communicate(full_text, "en-US-ChristopherNeural")
            await communicate.save(out_path)
        asyncio.run(_speak())
        print("✅ Edge-TTS Audio generated successfully!")
        return [out_path]
    except Exception as e:
        print(f"❌ FATAL: All TTS providers failed: {e}")
        return []

# ============================================================
# REEL COMPOSITOR
# ============================================================
def create_reel_video(data: dict, tts_paths: list) -> str:
    print("🎬 Compositing 1080x1920 Reel Video with MoviePy...")
    try:
        from moviepy.editor import VideoFileClip, AudioFileClip, CompositeVideoClip, ImageClip
        import numpy as np

        tts_audio = AudioFileClip(tts_paths[0])
        duration = min(tts_audio.duration + 2, 30)

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

        overlay_img = Image.new("RGBA", (1080, 1920), (0,0,0,0))
        draw = ImageDraw.Draw(overlay_img)
        try:
            font_hook  = ImageFont.truetype(FONT_ITALIC, 34)
            font_body  = ImageFont.truetype(FONT_SERIF, 44)
            font_brand = ImageFont.truetype(FONT_SANS, 28)
        except:
            font_hook = font_body = font_brand = ImageFont.load_default()

        hook_text = textwrap.fill(data.get("hook", ""), width=30)
        draw.text((540, 360), hook_text, font=font_hook, fill="#E0C080", anchor="mm", align="center")

        body_lines = data["script_english"].strip().split("\n")
        wrapped_lines = []
        for line in body_lines:
            if line.strip(): wrapped_lines.extend(textwrap.wrap(line, width=28))
            else: wrapped_lines.append("")
        
        final_body_text = "\n".join(wrapped_lines)
        draw.text((540, 960), final_body_text, font=font_body, fill="#FFFFFF", anchor="mm", align="center", spacing=22)
        draw.text((540, 1720), IG_HANDLE, font=font_brand, fill="#888888", anchor="mm")

        overlay_fname = f"output/overlay_{int(time.time())}.png"
        overlay_img.save(overlay_fname)
        txt_clip = ImageClip(overlay_fname, duration=duration)

        final_video = CompositeVideoClip([bg_clip, txt_clip]).set_audio(tts_audio)
        reel_path = f"output/reel_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        final_video.write_videofile(reel_path, fps=24, codec="libx264", audio_codec="aac", verbose=False, logger=None)
        return reel_path
    except Exception as e:
        print(f"❌ Video render failure: {e}")
        return None

# ============================================================
# INSTAGRAM PUBLISHER
# ============================================================
def upload_public_media(path: str) -> str:
    with open(path, "rb") as f:
        res = requests.post("https://tempfile.org/api/upload/local", files={"files": (os.path.basename(path), f)}).json()
        if res.get("success"):
            return f"{res['files'][0]['url'].rstrip('/')}/download"
    raise RuntimeError("Public media upload failed.")

def post_to_instagram(media_path: str, caption: str) -> bool:
    try:
        media_url = upload_public_media(media_path)
        payload = {"access_token": INSTAGRAM_ACCESS_TOKEN, "caption": caption, "media_type": "REELS", "video_url": media_url}

        c_res = requests.post(f"https://graph.instagram.com/v21.0/{INSTAGRAM_USER_ID}/media", data=payload).json()
        container_id = c_res.get("id")
        if not container_id: return False

        for attempt in range(1, 21):
            time.sleep(10)
            status = requests.get(f"https://graph.instagram.com/v21.0/{container_id}?fields=status_code&access_token={INSTAGRAM_ACCESS_TOKEN}").json()
            code = status.get("status_code")
            if code == "FINISHED": break
            elif code == "ERROR": return False

        p_res = requests.post(f"https://graph.instagram.com/v21.0/{INSTAGRAM_USER_ID}/media_publish", data={"creation_id": container_id, "access_token": INSTAGRAM_ACCESS_TOKEN}).json()
        return "id" in p_res
    except Exception as e:
        print(f"❌ Instagram API Failure: {e}")
        return False

# ============================================================
# MAIN
# ============================================================
def run():
    validate_environment()
    print(f"\n🚀 STARTING WORKFLOW: [REEL] for {IG_HANDLE}\n")
    data = generate_content()
    caption = f"{data.get('caption', '')}\n\n#psychology #humanbehavior #mindset #darkpsychology #brainblueprints #relatable"

    os.makedirs("output", exist_ok=True)
    tts_paths = generate_tts(data)
    if not tts_paths: sys.exit(1)

    reel_path = create_reel_video(data, tts_paths)
    if reel_path:
        success = post_to_instagram(reel_path, caption)
        if success:
            print("\n✅ WORKFLOW COMPLETED SUCCESSFULLY!")
        else:
            sys.exit(1)
    else:
        sys.exit(1)

if __name__ == "__main__":
    run()
