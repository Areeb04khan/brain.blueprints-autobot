# -*- coding: utf-8 -*-
"""
Brain Blueprints Bot v6.2 (Multi-Tier AI, TTS & Media-Host Failover Engine)
- AI Chain:    Gemini -> OpenRouter -> Groq -> NVIDIA NIM
- TTS Chain:   ElevenLabs -> Groq TTS -> Edge-TTS
- Media Host:  tempfile.org -> catbox.moe
- Fully automated psychology & behavioral reels

v6.2 CHANGELOG (hardening pass, Aug 2026) -- what changed and why:
  1. Every external HTTP/SDK call now has an explicit timeout, so one hung
     request can't silently eat the whole job's time budget and starve out
     the fallback chains sitting behind it.
  2. Every place that used to call .json() "blindly" (the exact bug that
     broke the Aug 1 run against tempfile.org) now checks the response
     first and logs the raw status/body on failure, so a future failure is
     diagnosable straight from the Actions log instead of a cryptic
     "Expecting value: line 1 column 1" message.
  3. Added a 2nd media host (catbox.moe) as an automatic fallback if
     tempfile.org fails twice.
  4. AI-generated content is validated (required fields present) right
     after parsing. An incomplete response is now treated as that
     provider's FAILURE (falls through to the next AI tier) instead of
     crashing later with a KeyError deep inside TTS or video rendering.
  5. TTS output and the rendered video are sanity-checked (non-trivial file
     size) before being trusted, so a truncated/corrupt file from a flaky
     provider doesn't silently get passed further down the pipeline.
  6. Background video clips shorter than the narration are now looped to
     fill the full duration instead of silently freezing on the last frame
     (moviepy's subclip() does NOT validate the source is long enough --
     verified this empirically; it just holds the last frame past the end).
  7. Instagram Graph API calls now retry transient (5xx/network) failures
     and log Meta's actual error payload on failure, instead of a bare
     `return False` that told you nothing.
  8. A cheap pre-flight check confirms the Instagram token is alive BEFORE
     spending ~1-2 minutes on content/audio/video generation.
  9. A top-level safety net in __main__ guarantees the log always ends with
     one clear line explaining what went wrong, even for a bug nobody
     anticipated.

  HONEST LIMITS -- nothing below can fix these, so they're designed to fail
  LOUD and FAST instead of being retried into a false sense of security:
    - An expired/revoked Instagram access token (long-lived tokens expire
      ~60 days after issue -- you must regenerate it by hand).
    - Every single AI provider AND every single TTS provider being down at
      the exact same time (vanishingly rare, but if it happens, that run
      just skips -- the next scheduled run 8 hours later will retry fresh).
"""

import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = getattr(PIL.Image, 'Resampling', PIL.Image).LANCZOS

from google import genai
from google.genai import types
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
MEDIA_HOST             = os.environ.get("MEDIA_HOST", "tempfile").lower()  # informational only -- see upload_public_media()
POST_TYPE              = os.environ.get("POST_TYPE", "reel").lower()
IG_HANDLE              = "@brain.blueprints"
ELEVENLABS_VOICE_ID    = "pNInz6obpgDQGcFmaJgB"  # Default stable voice

REQUIRED_ENV_VARS = ["INSTAGRAM_ACCESS_TOKEN", "INSTAGRAM_USER_ID"]

# ---- Resilience tuning ------------------------------------------------
# Every timeout/retry count used below lives here so it's easy to find and
# tune in one place later. None of these cost anything to change -- they
# only control how long we wait / how many times we retry before giving up
# and moving to the next fallback.
HTTP_TIMEOUT_SECONDS      = 30   # generic timeout (AI replies, IG container create/publish)
UPLOAD_TIMEOUT_SECONDS    = 45   # longer timeout for uploading the finished video file
IG_POLL_TIMEOUT_SECONDS   = 15   # timeout for each lightweight "is it ready yet" check
IG_POLL_MAX_ATTEMPTS      = 24   # x IG_POLL_INTERVAL_SECONDS = up to 4 min waiting for IG to process
IG_POLL_INTERVAL_SECONDS  = 10
RETRY_PAUSE_SECONDS       = 5    # brief pause between same-tier/same-call retry attempts

def validate_environment():
    missing = [name for name in REQUIRED_ENV_VARS if not os.environ.get(name)]
    if missing:
        print(f"❌ FATAL: Missing required secret(s): {', '.join(missing)}")
        sys.exit(1)
    if not any([GEMINI_API_KEY, OPENROUTER_API_KEY, GROQ_API_KEY, NVIDIA_API_KEY]):
        print("❌ FATAL: At least one AI API key must be provided!")
        sys.exit(1)

    # PRE-FLIGHT CHECK: confirm the Instagram token is alive BEFORE spending
    # 1-2 minutes generating content/audio/video. A dead token can't be
    # fixed by any fallback logic -- but catching it here means the job
    # fails in ~1 second with an unmistakable message instead of failing at
    # the very last step, after all the expensive work is already done.
    try:
        check = requests.get(
            "https://graph.instagram.com/v21.0/me",
            params={"fields": "id,username", "access_token": INSTAGRAM_ACCESS_TOKEN},
            timeout=15
        )
        if check.status_code in (400, 401, 403):
            print(f"❌ FATAL: Instagram access token looks invalid/expired (HTTP {check.status_code}): {check.text[:200]}")
            print("   -> Long-lived Instagram tokens expire ~60 days after issue and must be refreshed by hand.")
            print("   -> No amount of retrying fixes this -- regenerate the token in the Meta developer console.")
            sys.exit(1)
    except requests.exceptions.RequestException as e:
        # A flaky pre-check shouldn't block a run that might otherwise succeed --
        # just warn and let the real posting attempt later be the true test.
        print(f"⚠️ Could not pre-validate Instagram token (network hiccup, continuing anyway): {e}")

FONT_SERIF  = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
FONT_ITALIC = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf"
FONT_SANS   = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

# ============================================================
# MULTI-TIER AI CONTENT GENERATOR (Failover Chain)
# ============================================================
REQUIRED_CONTENT_KEYS = ["hook", "script_english", "search_query", "caption"]

def _validate_content_dict(data) -> bool:
    """
    Confirms the AI actually returned every field the rest of the pipeline
    needs. If a key is missing/empty, treat this as a FAILURE of that
    provider (fall through to the next AI tier) instead of crashing later,
    deep inside TTS or video generation, with a confusing KeyError.
    """
    return isinstance(data, dict) and all(data.get(k) for k in REQUIRED_CONTENT_KEYS)

def generate_content() -> dict:
    print(f"🧠 Querying AI Chain for {IG_HANDLE} content...")
    
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

    # Tier 1: Gemini (With Explicit Fail-Fast Configuration)
    if GEMINI_API_KEY:
        try:
            print(f"🧠 [1/4] Querying Gemini AI...")
            # Disable SDK automatic retries + cap the request at 30s so a
            # hang can't eat the fallback chain's time budget.
            client = genai.Client(
                api_key=GEMINI_API_KEY,
                http_options=types.HttpOptions(
                    timeout=HTTP_TIMEOUT_SECONDS * 1000,  # this SDK wants milliseconds
                    retry_options=types.HttpRetryOptions(attempts=1)
                )
            )
            response = client.models.generate_content(
                model="gemini-3.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(temperature=0.7)
            )
            raw = response.text.strip().replace("```json","").replace("```","").strip()
            data = json.loads(raw)
            if _validate_content_dict(data):
                print("✅ Generated content successfully via Gemini!")
                return data
            print(f"⚠️ Gemini response was missing required fields: {data}. Moving to Fallback Chain...")
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
            client = OpenAI(base_url=provider["base_url"], api_key=provider["api_key"], timeout=HTTP_TIMEOUT_SECONDS)
            response = client.chat.completions.create(
                model=provider["model"],
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            raw = response.choices[0].message.content.strip().replace("```json","").replace("```","").strip()
            data = json.loads(raw)
            if _validate_content_dict(data):
                print(f"✅ Generated content successfully via {provider['name']}!")
                return data
            print(f"⚠️ {provider['name']} response was missing required fields: {data}")
        except Exception as err:
            print(f"⚠️ {provider['name']} failed: {err}")

    print("❌ FATAL: All AI providers failed (or returned incomplete JSON).")
    sys.exit(1)

# ============================================================
# MEDIA ENGINE (Pexels + Unsplash)
# ============================================================
def fetch_pexels_video(query: str) -> str:
    if not PEXELS_API_KEY: return None
    try:
        headers = {"Authorization": PEXELS_API_KEY}
        url = f"https://api.pexels.com/videos/search?query={query}&orientation=portrait&per_page=5"
        res = requests.get(url, headers=headers, timeout=15)
        if res.ok:
            videos = res.json().get("videos", [])
            if videos:
                video = random.choice(videos)
                for vf in video.get("video_files", []):
                    if vf.get("file_type") == "video/mp4" and vf.get("width", 0) >= 720:
                        dl = requests.get(vf["link"], timeout=30)
                        # Validate the download actually succeeded before
                        # trusting it. Otherwise a failed/partial download
                        # gets treated as a good background and only
                        # surfaces as a confusing crash later inside video
                        # rendering, instead of falling through to Unsplash
                        # / the plain background like it should.
                        if not dl.ok or len(dl.content) < 10_000:
                            print(f"⚠️ Pexels video download looked invalid ({len(dl.content)} bytes) -- skipping.")
                            continue
                        v_path = f"output/pexels_vid_{int(time.time())}.mp4"
                        with open(v_path, "wb") as f:
                            f.write(dl.content)
                        return v_path
    except Exception as e:
        print(f"⚠️ Pexels fetch failed: {e}")
    return None

def fetch_unsplash_video_equivalent(query: str) -> str:
    if not UNSPLASH_ACCESS_KEY: return None
    try:
        headers = {"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"}
        url = f"https://api.unsplash.com/photos/random?query={query}&orientation=portrait"
        res = requests.get(url, headers=headers, timeout=15)
        if res.ok:
            img_url = res.json().get("urls", {}).get("regular")
            if img_url:
                dl = requests.get(img_url, timeout=30)
                if not dl.ok or len(dl.content) < 5_000:
                    print(f"⚠️ Unsplash image download looked invalid ({len(dl.content)} bytes).")
                    return None
                p_path = f"output/unsplash_portrait_{int(time.time())}.jpg"
                with open(p_path, "wb") as f:
                    f.write(dl.content)
                return p_path
    except Exception as e:
        print(f"⚠️ Unsplash fetch failed: {e}")
    return None

def get_reel_background(query: str) -> tuple:
    os.makedirs("output", exist_ok=True)
    v_path = fetch_pexels_video(query)
    if v_path: return (v_path, True)
    u_path = fetch_unsplash_video_equivalent(query)
    if u_path: return (u_path, False)
    print("⚠️ Both Pexels and Unsplash unavailable/failed -- falling back to a plain background.")
    return (None, False)

# ============================================================
# MULTI-TIER TTS FAILOVER ENGINE (English)
# ============================================================
def _valid_audio_file(path: str) -> bool:
    """A genuine few-to-tens-of-seconds mp3 is always well over 1KB. Catches
    truncated/empty files from a flaky provider before they reach moviepy."""
    return os.path.exists(path) and os.path.getsize(path) > 1000

def generate_tts(data: dict) -> list:
    # Defensive .get() -- even though generate_content() now validates these
    # keys upstream, this guards against a future edit reintroducing a
    # silent KeyError crash right here (this used to be `data['hook']` /
    # `data['script_english']` with no guard at all).
    full_text = f"{data.get('hook', '')}... {data.get('script_english', '')}".strip()
    if not full_text or full_text == "...":
        print("❌ FATAL: No script text available to speak (empty hook/script_english).")
        return []

    out_path = f"output/tts_full_{int(time.time())}.mp3"

    # Tier 1: ElevenLabs
    if ELEVENLABS_API_KEY:
        try:
            print("🎙️ [TTS 1/4] Trying ElevenLabs...")
            from elevenlabs.client import ElevenLabs
            # ElevenLabs' SDK default timeout is 240s -- far too long to
            # wait before failing over to Groq/Edge-TTS. Cap it explicitly.
            client = ElevenLabs(api_key=ELEVENLABS_API_KEY, timeout=60)
            audio_stream = client.text_to_speech.convert(
                text=full_text, voice_id=ELEVENLABS_VOICE_ID,
                model_id="eleven_multilingual_v2", output_format="mp3_44100_128"
            )
            with open(out_path, "wb") as f:
                for chunk in audio_stream:
                    if chunk: f.write(chunk)
            if _valid_audio_file(out_path):
                print("✅ ElevenLabs Audio generated successfully!")
                return [out_path]
            print("⚠️ ElevenLabs returned an empty/too-small file. Moving to Groq TTS...")
        except Exception as e:
            print(f"⚠️ ElevenLabs failed ({e}). Moving to Groq TTS...")

    # Tier 2: Groq TTS
    if GROQ_API_KEY:
        try:
            print("🎙️ [TTS 2/4] Trying Groq TTS...")
            client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=GROQ_API_KEY, timeout=HTTP_TIMEOUT_SECONDS)
            response = client.audio.speech.create(
                model="canopylabs/orpheus-v1-english",
                voice="hannah",
                input=full_text
            )
            response.stream_to_file(out_path)
            if _valid_audio_file(out_path):
                print("✅ Groq TTS Audio generated successfully!")
                return [out_path]
            print("⚠️ Groq TTS returned an empty/too-small file. Moving to Edge-TTS...")
        except Exception as e:
            print(f"⚠️ Groq TTS failed ({e}). Moving to Edge-TTS...")

    # Tier 3: Edge-TTS (Bulletproof local safety net -- free, no API key needed)
    try:
        print("🎙️ [TTS 3/4] Generating fallback via Edge-TTS...")
        import asyncio
        import edge_tts
        async def _speak():
            communicate = edge_tts.Communicate(full_text, "en-US-ChristopherNeural")
            await communicate.save(out_path)
        # edge-tts has no built-in timeout knob (it's a raw websocket call)
        # -- wrap it so a hung connection can't stall the whole job.
        asyncio.run(asyncio.wait_for(_speak(), timeout=60))
        if _valid_audio_file(out_path):
            print("✅ Edge-TTS Audio generated successfully!")
            return [out_path]
        print("❌ FATAL: Edge-TTS also returned an empty/too-small file.")
        return []
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
            raw_clip = VideoFileClip(bg_path)
            # FIX: stock clips from Pexels are sometimes shorter than the
            # narration. The old code did .subclip(0, duration) unconditionally
            # -- moviepy/ffmpeg does NOT validate the source is long enough;
            # it just freezes on the last decoded frame once you read past
            # the real end (verified this directly). That silently breaks
            # the "seamless loop" concept the whole reel is built around.
            # Loop short clips instead so the full duration is real motion.
            if raw_clip.duration < duration:
                bg_clip = raw_clip.loop(duration=duration)
            else:
                bg_clip = raw_clip.subclip(0, duration)
            bg_clip = bg_clip.resize(height=1920)
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

        body_lines = data.get("script_english", "").strip().split("\n")
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

        # Sanity check before handing this off to the upload/publish step --
        # a real 5-30s 1080x1920 reel is always well over 50KB. Catches a
        # truncated file from an ffmpeg hiccup that didn't raise an exception.
        if not os.path.exists(reel_path) or os.path.getsize(reel_path) < 50_000:
            print("❌ Rendered video file is missing or suspiciously small -- treating as a failed render.")
            return None

        return reel_path
    except Exception as e:
        print(f"❌ Video render failure: {e}")
        return None

# ============================================================
# INSTAGRAM PUBLISHER
# ============================================================
# WHAT WAS BROKEN (from the Aug 1 job log):
#   Content generation, TTS, and video compositing all succeeded. The run
#   then died with: ❌ Instagram API Failure: Expecting value: line 1 column 1 (char 0)
#   That exact message is Python's json module complaining it got NOTHING
#   (or non-JSON, like an HTML error/rate-limit page) back from tempfile.org,
#   because the old code called `.json()` immediately with no check first.
#   tempfile.org's own docs list a 200 requests/hour/IP limit -- GitHub
#   Actions shared runners rotate through a small pool of Azure IPs used by
#   thousands of unrelated workflows, so it's easy to land on one that's
#   already been rate-limited. We don't control that IP, so the fix is to
#   detect failures cleanly and have a backup host ready -- the same idea as
#   the Gemini -> OpenRouter -> Groq chain above, applied to file hosting,
#   PLUS the same hardening applied to every Instagram Graph API call below
#   (which had the exact same latent bug -- it just hadn't been hit yet).

def upload_to_tempfile(path: str):
    """
    Tier 1 media host. Free, no signup/API key required.
    Docs: https://tempfile.org/api  (POST /api/upload/local, multipart/form-data)
    Returns a direct download URL on success, or None on any failure -- this
    function never raises, so the chain below can just try the next tier.
    """
    try:
        with open(path, "rb") as f:
            res = requests.post(
                "https://tempfile.org/api/upload/local",
                files={"files": (os.path.basename(path), f)},
                data={"expiryHours": 1},  # only need the link for the ~minute IG takes to fetch it
                timeout=UPLOAD_TIMEOUT_SECONDS
            )
        # Check status + raw text BEFORE parsing JSON -- this is the actual
        # bug fix. If tempfile.org fails again, the log shows WHY (status
        # code + first 200 chars of the body) instead of a JSONDecodeError.
        if not res.ok:
            print(f"⚠️ tempfile.org HTTP {res.status_code}: {res.text[:200]!r}")
            return None
        try:
            data = res.json()
        except ValueError:
            print(f"⚠️ tempfile.org sent a non-JSON response: {res.text[:200]!r}")
            return None
        if data.get("success"):
            return f"{data['files'][0]['url'].rstrip('/')}/download"
        print(f"⚠️ tempfile.org reported failure: {data}")
        return None
    except Exception as e:
        print(f"⚠️ tempfile.org upload error: {e}")
        return None

def upload_to_catbox(path: str):
    """
    Tier 2 media host (fallback). Free, no signup/API key required.
    Docs: https://catbox.moe/tools.php  (POST /user/api.php, multipart/form-data)
    NOTE: catbox replies with PLAIN TEXT (just the URL), not JSON -- that's
    expected, not a bug. Files stay hosted (no auto-delete like
    tempfile.org), but that's harmless here since we only need the link for
    a few seconds while Instagram fetches it.
    """
    try:
        with open(path, "rb") as f:
            res = requests.post(
                "https://catbox.moe/user/api.php",
                data={"reqtype": "fileupload"},
                files={"fileToUpload": (os.path.basename(path), f)},
                timeout=UPLOAD_TIMEOUT_SECONDS
            )
        if res.ok and res.text.strip().startswith("http"):
            return res.text.strip()
        print(f"⚠️ catbox.moe HTTP {res.status_code}: {res.text[:200]!r}")
        return None
    except Exception as e:
        print(f"⚠️ catbox.moe upload error: {e}")
        return None

def upload_public_media(path: str) -> str:
    """
    Gets a PUBLIC url that Instagram's Graph API can fetch the finished reel
    from (Graph API needs a hosted URL -- it won't accept a raw file
    upload). Walks the tempfile.org -> catbox.moe chain, 2 attempts per
    host (these free hosts are usually just briefly flaky, not fully down).
    """
    chain = [("tempfile.org", upload_to_tempfile), ("catbox.moe", upload_to_catbox)]
    for tier_name, upload_fn in chain:
        for attempt in (1, 2):
            print(f"📤 [{tier_name}] Upload attempt {attempt}/2...")
            url = upload_fn(path)
            if url:
                print(f"✅ Public media URL obtained via {tier_name}")
                return url
            if attempt == 1:
                time.sleep(RETRY_PAUSE_SECONDS)
    raise RuntimeError("Public media upload failed on all hosts (tempfile.org + catbox.moe).")

def _instagram_api_call(method: str, url: str, retries: int = 2, **kwargs) -> dict:
    """
    Wrapper for every Instagram Graph API call. Applies the same fix as the
    upload chain above: a timeout so a hang can't eat the job's time
    budget, and a status/JSON check before trusting the response. Retries
    transient (5xx / network-level) failures; a 4xx (bad token, bad params)
    is deterministic and won't fix itself on retry, so we return Meta's
    error body immediately so the caller can log the real reason.
    Returns the parsed JSON dict, or {"_error": "..."} if nothing usable
    ever came back.
    """
    kwargs.setdefault("timeout", HTTP_TIMEOUT_SECONDS)
    last_err = "unknown error"
    for attempt in range(1, retries + 1):
        try:
            res = requests.request(method, url, **kwargs)
            if res.ok:
                try:
                    return res.json()
                except ValueError:
                    last_err = f"non-JSON response: {res.text[:200]!r}"
            elif 500 <= res.status_code < 600:
                last_err = f"HTTP {res.status_code}: {res.text[:200]}"  # server-side, worth retrying
            else:
                try:
                    return res.json()  # 4xx usually still carries Meta's real error message
                except ValueError:
                    return {"_error": f"HTTP {res.status_code}: {res.text[:200]}"}
        except requests.exceptions.RequestException as e:
            last_err = str(e)
        if attempt < retries:
            print(f"⚠️ Instagram API call attempt {attempt}/{retries} failed ({last_err}); retrying...")
            time.sleep(RETRY_PAUSE_SECONDS)
    return {"_error": last_err}

def post_to_instagram(media_path: str, caption: str) -> bool:
    try:
        media_url = upload_public_media(media_path)

        # Step 1: create the media container
        payload = {"access_token": INSTAGRAM_ACCESS_TOKEN, "caption": caption, "media_type": "REELS", "video_url": media_url}
        c_res = _instagram_api_call("POST", f"https://graph.instagram.com/v21.0/{INSTAGRAM_USER_ID}/media", data=payload)
        container_id = c_res.get("id")
        if not container_id:
            print(f"❌ IG media container creation failed: {c_res}")
            return False

        # Step 2: poll until Instagram finishes processing the video.
        # retries=1 here on purpose -- this loop already retries every
        # IG_POLL_INTERVAL_SECONDS, so an inner retry would just double up.
        finished = False
        for attempt in range(1, IG_POLL_MAX_ATTEMPTS + 1):
            time.sleep(IG_POLL_INTERVAL_SECONDS)
            status = _instagram_api_call(
                "GET", f"https://graph.instagram.com/v21.0/{container_id}",
                retries=1, timeout=IG_POLL_TIMEOUT_SECONDS,
                params={"fields": "status_code", "access_token": INSTAGRAM_ACCESS_TOKEN}
            )
            code = status.get("status_code")
            if code == "FINISHED":
                finished = True
                break
            elif code == "ERROR":
                print(f"❌ IG reported a processing error on the container: {status}")
                return False
            # else IN_PROGRESS / unknown / a transient polling hiccup -- keep polling
        if not finished:
            waited = IG_POLL_MAX_ATTEMPTS * IG_POLL_INTERVAL_SECONDS
            print(f"❌ IG container never reached FINISHED after {waited}s of polling.")
            return False

        # Step 3: publish
        p_res = _instagram_api_call(
            "POST", f"https://graph.instagram.com/v21.0/{INSTAGRAM_USER_ID}/media_publish",
            data={"creation_id": container_id, "access_token": INSTAGRAM_ACCESS_TOKEN}
        )
        if "id" in p_res:
            return True
        print(f"❌ IG publish failed: {p_res}")
        return False
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
    if not tts_paths:
        print("❌ FATAL: No usable audio was produced by any TTS provider.")
        sys.exit(1)

    reel_path = create_reel_video(data, tts_paths)
    if reel_path:
        success = post_to_instagram(reel_path, caption)
        if success:
            print("\n✅ WORKFLOW COMPLETED SUCCESSFULLY!")
        else:
            print("\n❌ WORKFLOW FAILED at the Instagram publish step -- see the ❌/⚠️ lines above for the exact reason.")
            sys.exit(1)
    else:
        print("\n❌ WORKFLOW FAILED at video rendering -- see the ❌/⚠️ lines above for the exact reason.")
        sys.exit(1)

if __name__ == "__main__":
    try:
        run()
    except SystemExit:
        raise  # the sys.exit() calls above are intentional -- let them propagate as-is
    except Exception as e:
        # Final safety net: catches anything genuinely unforeseen (a bug, an
        # edge case none of the tiers above anticipated) so the Actions log
        # always ends with one clear line instead of a raw traceback.
        print(f"❌ FATAL: Unhandled exception: {e}")
        sys.exit(1)
