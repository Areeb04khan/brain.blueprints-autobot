# -*- coding: utf-8 -*-
"""
Brain Blueprints Bot v6.3 (Multi-Tier AI, TTS & Media-Host Failover Engine
                            + 3-Column Grid Rotation System)
- AI Chain:    Gemini -> OpenRouter -> Groq -> NVIDIA NIM
- TTS Chain:   ElevenLabs -> Groq TTS -> Edge-TTS
- Media Host:  tempfile.org -> catbox.moe
- Fully automated psychology & behavioral reels

v6.3 CHANGELOG (grid-column rotation system, Aug 2026) -- what's new and why:
  Every post used to come from ONE fixed content prompt, which is why the
  Instagram grid looked visually uniform (every tile: chess pieces + dark
  psychology quote). v6.3 adds a 3-column rotation system so the grid
  itself becomes 3 recognizable series, matching a reference account
  Areeb provided (@houseofinvestors) where each grid column has its own
  consistent visual identity and voice.

  NEW FILES this depends on (all in the same directory as this script):
    - column_types.py      : defines the 3 columns x 3 sub-types each (9
                              total identities: colors, fonts, voice rules)
    - rotation_tracker.py   : reads/writes rotation_state.json so the
                              1,2,3,1,2,3... column sequence survives
                              across separate GitHub Actions runs
    - content_prompts.py    : builds a DIFFERENT AI prompt per sub-type
                              (previously: one hardcoded prompt for every post)
    - renderer.py            : draws the sub-type-specific static feed-post
                              image (previously: one generic text-overlay
                              layout for every post)

  WHAT STAYED THE SAME: the AI failover chain, TTS failover chain, media
  upload chain, and Instagram publish logic below are UNCHANGED from v6.2
  -- v6.3 only changes WHAT content/prompt/visual gets fed into those
  existing pipelines, not how the pipelines themselves work. This matters
  because it means the hardening from the v6.2 changelog below (timeouts,
  retries, validation) still applies exactly as before.

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


# ============================================================================
# GRID-COLUMN ROTATION SYSTEM (v6.3)
# ----------------------------------------------------------------------------
# Everything in this section used to be 4 separate files (column_types.py,
# rotation_tracker.py, content_prompts.py, renderer.py). Inlined into this
# single poster.py on request, to keep the repo at its original simple
# 5-file shape (main.yml, poster.py, requirements.txt, progress.json,
# README.md) rather than growing to 8 files. renderer.py itself was dropped
# entirely rather than inlined -- it built STATIC feed-post images, but
# every post here is a REEL (confirmed), and create_reel_video() below
# already has its own text-overlay logic for the video canvas. Keeping
# renderer.py would have been dead code with no caller.
# ============================================================================

# ---- COLUMN_TYPES: the 3 columns x 3 sub-types each (9 total identities) --
# Single source of truth for every column's colors/fonts/voice rules. Every
# other piece below (rotation tracker, prompt builder, reel compositor)
# reads FROM this dict, never redefines its own copy -- keeps all 9
# identities impossible to drift out of sync with each other.
#
# COLUMN_1 = "Command / Warn / Sit With"   (black imperative -> maroon alarm
#                                            -> cream reflective)
# COLUMN_2 = "Do / Notice / Become"        (navy actionable -> sage
#                                            observational -> charcoal/gold
#                                            identity-statement)
# COLUMN_3 = "Rule / Story / Truth"        (black/white numbered rule ->
#                                            photo-bg narrative scenario ->
#                                            gray italic universal truth)
#            REVISED: every sub-type now fetches a real Pexels/Unsplash
#            video/image background (reverting an earlier over-correction
#            where 8 of 9 sub-types used flat color only -- that made
#            reels visually flat/static, atypical for the Reels format,
#            and lost the real-footage feel of Areeb's original posts). A
#            random DIFFERENT clip per post would still break column
#            recognizability though, so identity is now carried by a
#            COLORED TINT overlay (subtype["bg_color"] at
#            subtype["overlay_opacity"]) on top of real video/image
#            content, not by removing video entirely. Bold/graphic
#            sub-types (command/warn/rule) use a strong tint so the brand
#            color still dominates at a glance; quieter/narrative
#            sub-types (sit_with/story) use a lighter tint so the actual
#            scene reads through more clearly.
COLUMNS = {
    1: [
        {
            "key": "command", "label": "Command",
            "bg_color": "#0A0A0A", "text_color": "#FFFFFF", "accent_color": "#FFFFFF",
            "font_style": "sans_bold", "voice_register": "imperative", "overlay_opacity": 0.72,
            "visual_mood_instruction": (
                "a short 2-4 word visual search query for stark, minimal, "
                "powerful imagery (e.g. 'empty modern architecture', 'single "
                "silhouette dark room', 'clean dark hallway')"
            ),
            "content_instruction": (
                "Write a short, DIRECT, second-person IMPERATIVE instruction "
                "about commanding respect or controlling a social interaction. "
                "Use command verbs (Speak less. Hold your ground. Never explain "
                "twice.). No metaphors, no story -- pure instruction, like a drill "
                "sergeant giving tactical advice. 1-2 sentences maximum."
            ),
        },
        {
            "key": "warn", "label": "Warn",
            "bg_color": "#3D0A0A", "text_color": "#FFFFFF", "accent_color": "#E8B4B4",
            "font_style": "sans_bold_condensed", "voice_register": "alarm", "overlay_opacity": 0.70,
            "visual_mood_instruction": (
                "a short 2-4 word visual search query for tense, alarming "
                "imagery (e.g. 'storm clouds dark', 'shadow closeup tension', "
                "'red warning light')"
            ),
            "content_instruction": (
                "Write a short WARNING that names a specific manipulation tactic "
                "someone might be using on the reader RIGHT NOW, in real time. "
                "Tone is urgent, like catching something before it lands. Use "
                "present tense ('They're testing...', 'Notice how they just...'). "
                "1-2 sentences, ALL CAPS acceptable for the hook line only."
            ),
        },
        {
            "key": "sit_with", "label": "Sit With",
            "bg_color": "#F2EEE6", "text_color": "#1A1A1A", "accent_color": "#8A8578",
            "font_style": "serif_italic", "voice_register": "aphoristic", "overlay_opacity": 0.55,
            "visual_mood_instruction": (
                "a short 2-4 word visual search query for calm, quiet imagery "
                "(e.g. 'empty park bench morning', 'still water soft light', "
                "'quiet room window light')"
            ),
            "content_instruction": (
                "Write ONE quiet, aphoristic closing thought -- NOT an instruction, "
                "NOT a warning. Something the reader sits with, not acts on. No "
                "second-person commands. Should feel like the last line of a "
                "chapter, not the first. 1 sentence, maximum 20 words."
            ),
        },
    ],
    2: [
        {
            "key": "do", "label": "Do",
            "bg_color": "#0B1A3D", "text_color": "#FFFFFF", "accent_color": "#4A9EFF",
            "font_style": "sans_bold", "voice_register": "actionable_steps", "overlay_opacity": 0.68,
            "visual_mood_instruction": (
                "a short 2-4 word visual search query for purposeful, active "
                "imagery (e.g. 'person walking confident city', 'hands writing "
                "notebook', 'city motion blur night')"
            ),
            "content_instruction": (
                "Write a NUMBERED action step (e.g. 'Step 2 of building presence:') "
                "about a concrete behavior change. Practical, procedural, like a "
                "how-to guide. Should feel useful and actionable -- something the "
                "reader could literally do in their next conversation. 1-2 sentences."
            ),
        },
        {
            "key": "notice", "label": "Notice",
            "bg_color": "#4A5240", "text_color": "#F2EEE6", "accent_color": "#B8C4A8",
            "font_style": "serif_thin", "voice_register": "observational", "overlay_opacity": 0.60,
            "visual_mood_instruction": (
                "a short 2-4 word visual search query for observational, subtle "
                "imagery (e.g. 'reflection window glass', 'crowd distance blur', "
                "'watching from shadow')"
            ),
            "content_instruction": (
                "Write an OBSERVATIONAL pattern-recognition statement -- something "
                "to watch FOR in other people's behavior, not something to do "
                "yourself. Third person framing ('People who X usually Y', "
                "'Notice how liars...'). Detached, analytical tone, like a "
                "field-guide entry. 1-2 sentences."
            ),
        },
        {
            "key": "become", "label": "Become",
            "bg_color": "#1C1C1C", "text_color": "#E0C080", "accent_color": "#E0C080",
            "font_style": "serif_italic_elegant", "voice_register": "identity_statement", "overlay_opacity": 0.62,
            "visual_mood_instruction": (
                "a short 2-4 word visual search query for elegant, aspirational "
                "imagery (e.g. 'golden hour silhouette', 'mirror reflection "
                "elegant', 'quiet confidence portrait')"
            ),
            "content_instruction": (
                "Write an ASPIRATIONAL IDENTITY statement -- about who the reader "
                "becomes, not what they do. Framed around character/identity, not "
                "action ('People who are hard to read are rarely hard to trust'). "
                "Elegant, slightly literary tone. 1 sentence, maximum 22 words."
            ),
        },
    ],
    3: [
        {
            "key": "rule", "label": "Rule",
            "bg_color": "#000000", "text_color": "#FFFFFF", "accent_color": "#FFFFFF",
            "font_style": "sans_bold", "voice_register": "numbered_rule", "overlay_opacity": 0.72,
            "visual_mood_instruction": (
                "a short 2-4 word visual search query for bold, structured "
                "imagery (e.g. 'geometric shadows architecture', 'grid pattern "
                "dark', 'staircase lines dark')"
            ),
            "content_instruction": (
                "Write ONE numbered RULE in the style 'Rule [N]: [short punchy "
                "statement]'. Pick any single-digit number. Blunt, absolute, "
                "no hedging language ('sometimes', 'usually', 'might'). Should "
                "read like a rule from an unwritten code. 1 sentence."
            ),
        },
        {
            "key": "story", "label": "Story",
            "bg_color": "#12100E", "text_color": "#FFFFFF", "accent_color": "#F4C542",
            "font_style": "serif_caption", "voice_register": "micro_scenario", "overlay_opacity": 0.35,
            "visual_mood_instruction": (
                "a short 2-4 word visual search query for a moody, cinematic "
                "scene that matches the story below (e.g. 'empty boardroom "
                "night', 'rain window silhouette')"
            ),
            "content_instruction": (
                "Write a TINY narrative micro-scenario -- a single moment, not "
                "a lesson stated outright. Third person or implied scene, past "
                "tense ('He didn't raise his voice. He just stopped agreeing.'). "
                "NO explicit advice or moral stated -- the reader infers it. "
                "1-2 short sentences, cinematic and specific."
            ),
        },
        {
            "key": "truth", "label": "Truth",
            "bg_color": "#D8D8D8", "text_color": "#2B2B2B", "accent_color": "#7A7A7A",
            "font_style": "serif_italic", "voice_register": "universal_truth", "overlay_opacity": 0.58,
            "visual_mood_instruction": (
                "a short 2-4 word visual search query for timeless, universal "
                "imagery (e.g. 'open sky clouds', 'empty road horizon', 'natural "
                "landscape calm')"
            ),
            "content_instruction": (
                "Write ONE universal truth statement -- applies to everyone, "
                "timeless phrasing, no second-person address. Should feel quotable "
                "on its own, detached from any specific scenario. 1 sentence, "
                "maximum 18 words."
            ),
        },
    ],
}


def get_subtype(column_num: int, subtype_index: int) -> dict:
    """Looks up one sub-type by column (1/2/3) and position (0/1/2) in its
    cycle. The ONLY function that should read COLUMNS directly, so every
    caller stays in sync if the definitions above ever change."""
    subtypes = COLUMNS[column_num]
    return subtypes[subtype_index % len(subtypes)]


def total_subtypes_in_column(column_num: int) -> int:
    return len(COLUMNS[column_num])


# ---- ROTATION TRACKER: which column/sub-type posts next, persisted -------
# GitHub Actions gives a fresh container every run -- nothing on disk
# survives between scheduled runs UNLESS committed back to the repo. This
# is why rotation_state.json (separate from your existing progress.json,
# which just counts total posts) gets written here AND needs one new step
# in main.yml (shown in the setup notes) to commit it back after each run.
ROTATION_STATE_PATH = "rotation_state.json"

DEFAULT_ROTATION_STATE = {
    "next_column": 1,
    "column_subtype_index": {"1": 0, "2": 0, "3": 0},
    "last_updated": None,
    "history": [],
}


def load_rotation_state(path: str = ROTATION_STATE_PATH) -> dict:
    """Reads rotation_state.json. Missing/corrupt file -> safe fresh start
    at Column 1, NOT a crash -- this is expected on the very first run."""
    if not os.path.exists(path):
        print(f"ℹ️ No {path} found -- starting fresh rotation at Column 1.")
        return dict(DEFAULT_ROTATION_STATE)
    try:
        with open(path, "r", encoding="utf-8") as f:
            state = json.load(f)
        merged = dict(DEFAULT_ROTATION_STATE)
        merged.update(state)
        if "column_subtype_index" not in state:
            merged["column_subtype_index"] = dict(DEFAULT_ROTATION_STATE["column_subtype_index"])
        return merged
    except (json.JSONDecodeError, OSError) as e:
        print(f"⚠️ {path} exists but couldn't be read ({e}). Falling back to fresh rotation state.")
        return dict(DEFAULT_ROTATION_STATE)


def save_rotation_state(state: dict, path: str = ROTATION_STATE_PATH) -> None:
    """Writes rotation_state.json. This alone does NOT persist across runs
    -- the new main.yml step (see setup notes) commits+pushes this file
    after a successful run. If that workflow step is ever removed, the
    rotation silently resets to Column 1 every run -- code stays correct,
    only the persistence breaks."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def pick_next_column_and_advance(state: dict) -> tuple:
    """Core rotation logic, called once per run. Returns (column_num,
    subtype_index, subtype_dict) for THIS run, and mutates `state` in place
    to reflect what comes NEXT run. Column advances 1->2->3->1..., and each
    column's own sub-type position (A->B->C->A...) advances independently
    of the other two columns, so uneven posting frequency across columns
    can never desync one column's internal cycle."""
    column_num = state["next_column"]
    subtype_idx = state["column_subtype_index"].get(str(column_num), 0)
    subtype = get_subtype(column_num, subtype_idx)

    total_subs = total_subtypes_in_column(column_num)
    state["column_subtype_index"][str(column_num)] = (subtype_idx + 1) % total_subs
    state["next_column"] = (column_num % 3) + 1

    state["last_updated"] = datetime.now().isoformat()
    state["history"].append({"column": column_num, "subtype": subtype["key"], "at": state["last_updated"]})
    state["history"] = state["history"][-12:]  # keep last 12 only, for debugging visibility

    return column_num, subtype_idx, subtype


# ---- CONTENT PROMPT BUILDER: different AI prompt per sub-type ------------
def build_prompt(subtype: dict) -> str:
    """Builds the AI content-generation prompt for whichever sub-type is
    active. Previously poster.py had exactly ONE hardcoded prompt used for
    every post -- which is why every post sounded/looked the same. This
    reads subtype['content_instruction'] so the prompt itself changes per
    column/sub-type, while the returned JSON schema stays identical across
    all 9 so nothing downstream needs to branch on which sub-type this is.

    Every subtype now supplies visual_mood_instruction (not just Column
    3's "story") so the AI generates a real, on-brand search_query for
    every post -- create_reel_video() uses this to fetch actual Pexels/
    Unsplash footage for all 9 subtypes, tinted with that subtype's brand
    color, rather than only "story" getting real video and the rest
    getting a flat color card."""
    return f"""Act as a social tactics expert and psychological strategist writing for an Instagram account.

CONTENT TYPE FOR THIS POST: "{subtype['label']}" ({subtype['voice_register']} register)

{subtype['content_instruction']}

IMPORTANT VOICE RULES:
- Stay STRICTLY within the voice register described above. Do not blend in
  instructional language if this is a reflective/observational type, and
  vice versa -- the whole point is that this voice register is DISTINCT
  from other post types on this account.
- CRITICAL: The very last sentence must end mid-thought or flow directly
  back into the first word of the hook, to create a seamless audio loop
  when the video repeats.
- Keep total spoken content under 10 seconds when read aloud at a natural,
  moderate pace with pauses (roughly 25-35 words total including the hook).

Return STRICTLY valid JSON, no markdown fences, no preamble:
{{
  "hook": "A short attention-grabbing first line (under 8 words)",
  "script_english": "The full body content in the voice register specified above",
  "search_query": "{subtype['visual_mood_instruction']}",
  "caption": "1-2 line Instagram caption matching this post's tone, ending with a call to follow @brain.blueprints"
}}"""



def build_tts_pacing(subtype: dict, full_text: str) -> tuple:
    """
    Returns (paced_text, rate) for Edge-TTS's Communicate(). Implements
    Areeb's "moderate speed with pauses and stops" request using ONLY what
    this library actually supports -- confirmed by reading edge-tts's
    installed source directly (communicate.py), not assumed:

    Communicate() escapes ALL text via xml.sax.saxutils.escape before
    sending to Microsoft's TTS service. That means raw SSML tags like
    `<break time="450ms"/>` embedded in the text arrive as the LITERAL
    string "&lt;break time=450ms/&gt;" and get READ ALOUD as garbled
    words -- not interpreted as a pause. An earlier draft of this function
    tried exactly that and would have shipped broken audio; caught by
    reading the library source before deploying, not left in.

    What actually works:
    1. `rate` -- a real Communicate() constructor parameter, controls
       overall speaking speed (e.g. "-8%" = 8% slower).
    2. Comma insertion at "..." pause markers -- edge-tts's underlying
       neural voice genuinely produces an audible micro-pause at commas as
       normal prosody (not a special API call, just how the voice reads
       punctuation), so converting "..." to "," gives a real, working
       pause where the script wants one.
    """
    paced_text = full_text.replace("...", ",")

    register = subtype.get("voice_register", "")
    if register in ("alarm", "actionable_steps"):
        rate = "+4%"   # urgent/actionable content reads slightly faster
    elif register in ("aphoristic", "universal_truth", "identity_statement"):
        rate = "-8%"   # reflective content reads slightly slower
    else:
        rate = "-2%"   # default: slightly slower than 0%, per "moderate pace" request

    return paced_text, rate


# ============================================================================
# END GRID-COLUMN ROTATION SYSTEM -- everything below this line is your
# original AI/TTS/media/Instagram pipeline, modified only to receive
# `subtype` as a parameter where needed (see inline comments at each spot).
# ============================================================================



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

def generate_content(subtype: dict) -> dict:
    """
    CHANGED IN v6.3: now takes `subtype` (one of the 9 dicts from
    column_types.py, chosen by the rotation tracker in run() below) instead
    of using one fixed prompt for every post. build_prompt() reads that
    sub-type's content_instruction/voice_register and constructs a prompt
    specific to it -- e.g. "command" gets an imperative-instruction prompt,
    "sit_with" gets a quiet-aphorism prompt. Everything below this line
    (the actual 4-tier AI failover chain) is UNCHANGED from v6.2.
    """
    print(f"🧠 Querying AI Chain for {IG_HANDLE} content [{subtype['label']} / {subtype['key']}]...")

    prompt = build_prompt(subtype)

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

def generate_tts(data: dict, subtype: dict) -> list:
    """
    CHANGED IN v6.3: now also takes `subtype`, used ONLY by the Edge-TTS
    tier (see note below on why the other two tiers are untouched) to
    apply per-sub-type pacing via build_tts_pacing() -- real rate control
    (slightly faster for urgent/alarm content, slower for reflective
    content) plus comma-based pauses at the natural "..." points already
    present in the AI-generated script. This directly implements Areeb's
    request: "adjust the tts pronunciation properly to a moderate speed
    with pauses and stops where required" -- previously full_text was
    passed to every TTS tier completely raw, with zero pacing/pause
    control. (See build_tts_pacing()'s own docstring above for why this
    uses comma insertion rather than SSML <break> tags -- that approach
    was tried first and confirmed broken by reading edge-tts's actual
    source before shipping it.)
    """
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
    # v6.3: this tier now uses build_tts_pacing() for per-sub-type rate +
    # comma-based pauses (see that function's docstring for why raw SSML
    # <break> tags do NOT work with this library -- verified by reading
    # edge-tts's source, not assumed). ElevenLabs/Groq tiers above take
    # plain text with no per-call pacing knob in this simple API path, so
    # they're left as raw full_text -- unchanged from v6.2.
    try:
        print("🎙️ [TTS 3/4] Generating fallback via Edge-TTS (with pacing)...")
        import asyncio
        import edge_tts
        paced_text, rate = build_tts_pacing(subtype, full_text)
        async def _speak():
            # `rate` is a real Communicate() parameter (confirmed in the
            # library's __init__ signature) -- controls overall speaking
            # speed. paced_text has "..." converted to "," which edge-tts's
            # neural voice genuinely pauses on as normal comma prosody.
            # This is what "moderate speed with pauses and stops where
            # required" actually looks like using only what this library
            # really supports.
            communicate = edge_tts.Communicate(paced_text, "en-US-ChristopherNeural", rate=rate)
            await communicate.save(out_path)
        # edge-tts has no built-in timeout knob (it's a raw websocket call)
        # -- wrap it so a hung connection can't stall the whole job.
        asyncio.run(asyncio.wait_for(_speak(), timeout=60))
        if _valid_audio_file(out_path):
            print(f"✅ Edge-TTS Audio generated successfully! (rate={rate}, comma pacing applied)")
            return [out_path]
        print("❌ FATAL: Edge-TTS also returned an empty/too-small file.")
        return []
    except Exception as e:
        print(f"❌ FATAL: All TTS providers failed: {e}")
        return []


# ============================================================
# REEL COMPOSITOR
# ============================================================
def create_reel_video(data: dict, tts_paths: list, subtype: dict) -> str:
    """
    CHANGED IN v6.3: now takes `subtype` and branches on two things that
    used to be fixed for every single post:

    1. BACKGROUND SOURCE + TREATMENT: every subtype now fetches a real
       Pexels/Unsplash video/image via get_reel_background(), using the
       on-brand search_query the AI generated from that subtype's
       visual_mood_instruction (see build_prompt/COLUMNS above). REVISED
       from an earlier version that gave only Column 3's "story" subtype
       real footage and used flat color for the other 8 -- that made most
       reels visually static, unusual for a format built around motion,
       and dropped the real-footage feel present in the original bot's
       posts. Column identity is now carried by a COLORED TINT
       (subtype["bg_color"] blended in at subtype["overlay_opacity"]) on
       top of the real footage, not by removing footage. Bold/graphic
       subtypes (command/warn/rule) use a strong tint (~0.70-0.72) so the
       brand color still reads instantly; quieter/narrative subtypes
       (sit_with/story) use a lighter tint (~0.35-0.55) so the actual
       scene stays visible, matching each subtype's own mood.
    2. TEXT STYLING: colors/fonts were hardcoded (#E0C080 gold hook,
       #FFFFFF white body, DejaVu Serif always) for every post regardless
       of type. Now pulled from the sub-type dict, so this reel's overlay
       matches whichever column/sub-type the rotation tracker picked.
    """
    print(f"🎬 Compositing 1080x1920 Reel Video with MoviePy [{subtype['label']} / {subtype['key']}]...")
    try:
        from moviepy.editor import VideoFileClip, AudioFileClip, CompositeVideoClip, ImageClip
        import numpy as np

        tts_audio = AudioFileClip(tts_paths[0])
        duration = min(tts_audio.duration + 2, 30)

        # Every subtype attempts a real background fetch now -- no more
        # needs_photo_bg gate. get_reel_background() already has its own
        # Pexels -> Unsplash -> (None, False) fallback chain (unchanged,
        # verified directly in that function above), so a failed fetch
        # here just falls through to the flat-color branch below exactly
        # as it always could.
        bg_path, is_video = get_reel_background(data.get("search_query", "dark moody cinematic scene"))

        # Pre-compute this subtype's tint color as an (R,G,B) tuple once,
        # reused by both the video and image branches below so the exact
        # same color logic applies regardless of which source succeeded.
        tint_hex = (subtype.get("bg_color") or "#12100E").lstrip("#")
        tint_rgb = tuple(int(tint_hex[i:i+2], 16) for i in (0, 2, 4))
        opacity = subtype.get("overlay_opacity", 0.6)

        if bg_path and is_video:
            raw_clip = VideoFileClip(bg_path)
            # FIX (kept from v6.2): stock clips from Pexels are sometimes
            # shorter than the narration. moviepy/ffmpeg does NOT validate
            # the source is long enough; it just freezes on the last
            # decoded frame once you read past the real end (verified this
            # directly). Loop short clips instead so the full duration is
            # real motion.
            if raw_clip.duration < duration:
                bg_clip = raw_clip.loop(duration=duration)
            else:
                bg_clip = raw_clip.subclip(0, duration)
            bg_clip = bg_clip.resize(height=1920)
            if bg_clip.w < 1080: bg_clip = bg_clip.resize(width=1080)
            bg_clip = bg_clip.crop(x_center=bg_clip.w/2, y_center=bg_clip.h/2, width=1080, height=1920)

            # Colored tint blend: result = video*(1-opacity) + tint*opacity,
            # applied per-pixel via numpy. This replaces the old fixed
            # "* 0.35" darken-toward-black -- that made every video just
            # dimmer, with no actual color identity. This blends toward
            # THIS subtype's specific brand color instead, so "Warn" reels
            # read as deep-red-tinted and "Command" reels read as
            # near-black-tinted, even though both start from arbitrary
            # stock footage.
            tint_array = np.array(tint_rgb, dtype=np.float64)
            def _tint_frame(image, _opacity=opacity, _tint=tint_array):
                blended = image.astype(np.float64) * (1 - _opacity) + _tint * _opacity
                return blended.astype(np.uint8)
            bg_clip = bg_clip.fl_image(_tint_frame)
        elif bg_path and not is_video:
            bg_img = Image.open(bg_path).convert("RGB").resize((1080, 1920), Image.Resampling.LANCZOS)
            # Same colored-tint approach as the video branch above, applied
            # once to the static image via PIL's blend instead of per-frame.
            tint_layer = Image.new("RGB", (1080, 1920), color=tint_rgb)
            bg_img = Image.blend(bg_img, tint_layer, opacity)
            bg_img_path = f"output/reel_bg_img_{int(time.time())}.jpg"
            bg_img.save(bg_img_path)
            bg_clip = ImageClip(bg_img_path, duration=duration)
        else:
            # Both Pexels and Unsplash failed (or returned nothing) --
            # graceful flat-color fallback using this subtype's own brand
            # color, so even a total fetch failure still looks intentional
            # and on-brand rather than a generic gray error card.
            flat_color = subtype.get("bg_color") or "#12100E"
            clean_bg = Image.new("RGB", (1080, 1920), color=flat_color)
            clean_bg_path = f"output/clean_bg_{int(time.time())}.jpg"
            clean_bg.save(clean_bg_path)
            bg_clip = ImageClip(clean_bg_path, duration=duration)

        overlay_img = Image.new("RGBA", (1080, 1920), (0,0,0,0))
        draw = ImageDraw.Draw(overlay_img)

        # Map this sub-type's short font_style name to a real font file --
        # local dict here since this is a single-file script now (no
        # separate renderer module to share a FONT_MAP with).
        # and one should never be able to break the other.
        reel_font_map = {
            "sans_bold":              FONT_SANS,
            "sans_bold_condensed":    FONT_SANS,
            "serif_italic":           FONT_ITALIC,
            "serif_thin":             FONT_SERIF,
            "serif_italic_elegant":   FONT_ITALIC,
            "serif_caption":          FONT_SERIF,
        }
        body_font_path = reel_font_map.get(subtype.get("font_style"), FONT_SERIF)

        try:
            font_hook  = ImageFont.truetype(FONT_ITALIC, 34)
            font_body  = ImageFont.truetype(body_font_path, 44)
            font_brand = ImageFont.truetype(FONT_SANS, 28)
        except:
            font_hook = font_body = font_brand = ImageFont.load_default()

        hook_color = subtype.get("accent_color", "#E0C080")
        body_color = subtype.get("text_color", "#FFFFFF")

        hook_text = textwrap.fill(data.get("hook", ""), width=30)
        draw.text((540, 360), hook_text, font=font_hook, fill=hook_color, anchor="mm", align="center")

        body_lines = data.get("script_english", "").strip().split("\n")
        wrapped_lines = []
        for line in body_lines:
            if line.strip(): wrapped_lines.extend(textwrap.wrap(line, width=28))
            else: wrapped_lines.append("")
        
        final_body_text = "\n".join(wrapped_lines)
        draw.text((540, 960), final_body_text, font=font_body, fill=body_color, anchor="mm", align="center", spacing=22)
        draw.text((540, 1720), IG_HANDLE, font=font_brand, fill=subtype.get("accent_color", "#888888"), anchor="mm")

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

    # ---- pick this run's column/sub-type from the rotation tracker ----
    # IMPORTANT: rotation_state is loaded and the NEXT pick is computed here,
    # but intentionally NOT SAVED yet. state (the in-memory dict) has already
    # been mutated by pick_next_column_and_advance() to reflect what comes
    # after THIS post -- but the FILE on disk still reflects the position
    # before this run. It only gets written (save_rotation_state) at the
    # very end, and ONLY if the post actually succeeds. This matters
    # because: if this run picks Column 2/"notice" and then TTS or video
    # rendering or the IG publish step fails, Column 2/"notice" never
    # actually got posted -- so the rotation must NOT advance, or the next
    # run would skip straight to Column 3 and the grid pattern would
    # silently drift off by one forever.
    state = load_rotation_state()
    column_num, subtype_idx, subtype = pick_next_column_and_advance(state)

    print(f"\n🚀 STARTING WORKFLOW: [REEL] for {IG_HANDLE}")
    print(f"   Grid Column {column_num} -> sub-type '{subtype['key']}' ({subtype['label']})\n")

    data = generate_content(subtype)

    # Hashtags now vary by sub-type's voice register instead of always
    # including "#darkpsychology" -- that tag fit the old "Warn"-style
    # content but reads oddly attached to a quiet "Sit With"/"Truth" post.
    base_tags = "#psychology #humanbehavior #mindset #brainblueprints"
    register_tags = {
        "imperative":          "#confidence #socialskills",
        "alarm":               "#darkpsychology #manipulation #redflags",
        "aphoristic":          "#mindfulness #wisdom #selfawareness",
        "actionable_steps":    "#growth #selfimprovement #confidence",
        "observational":       "#bodylanguage #humanbehavior #psychologyfacts",
        "identity_statement":  "#characterdevelopment #mindset #wisdom",
        "numbered_rule":       "#discipline #mindset #rules",
        "micro_scenario":      "#storytelling #relatable #psychology",
        "universal_truth":     "#wisdom #quotes #reflection",
    }
    extra_tags = register_tags.get(subtype.get("voice_register", ""), "#relatable")
    caption = f"{data.get('caption', '')}\n\n{base_tags} {extra_tags}"

    os.makedirs("output", exist_ok=True)
    tts_paths = generate_tts(data, subtype)
    if not tts_paths:
        print("❌ FATAL: No usable audio was produced by any TTS provider.")
        print(f"   -> Rotation NOT advanced (still Column {column_num}/'{subtype['key']}' next run).")
        sys.exit(1)

    reel_path = create_reel_video(data, tts_paths, subtype)
    if reel_path:
        success = post_to_instagram(reel_path, caption)
        if success:
            # ONLY save the advanced rotation state here, after a confirmed
            # successful publish -- see the big comment above run() for why
            # this ordering is load-bearing, not arbitrary.
            save_rotation_state(state)
            print(f"\n✅ WORKFLOW COMPLETED SUCCESSFULLY! (Column {column_num} / '{subtype['key']}' posted)")
            print(f"   Next run will post: Column {state['next_column']}")
        else:
            print("\n❌ WORKFLOW FAILED at the Instagram publish step -- see the ❌/⚠️ lines above for the exact reason.")
            print(f"   -> Rotation NOT advanced (still Column {column_num}/'{subtype['key']}' next run).")
            sys.exit(1)
    else:
        print("\n❌ WORKFLOW FAILED at video rendering -- see the ❌/⚠️ lines above for the exact reason.")
        print(f"   -> Rotation NOT advanced (still Column {column_num}/'{subtype['key']}' next run).")
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