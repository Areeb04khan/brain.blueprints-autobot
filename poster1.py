# -*- coding: utf-8 -*-
"""
Brain Blueprints Bot v6.7 (Multi-Tier AI, TTS & Media-Host Failover Engine
                           + 3-Column Grid Rotation System + Two-Segment
                           Hook/Reveal Content Structure)
- AI Chain:    Gemini -> OpenRouter -> Groq -> NVIDIA NIM
- TTS Chain:   ElevenLabs -> Groq TTS -> Edge-TTS (with rate/pitch/volume per subtype)
- Media Host:  tempfile.org -> catbox.moe
- Fully automated psychology & behavioral reels

VERSION HISTORY (each version incremented on every change, no matter how small):

v6.7 (CURRENT) - Complete content strategy change: two-segment hook/reveal reels, Aug 13 2026
  WHAT CHANGED (per Areeb's explicit request, replacing the single-scene
  "hook line + body text on one screen" format entirely):
  1. Every reel is now TWO GENUINELY SEPARATE VIDEO SEGMENTS concatenated
     into one file: a HOOK segment (its own background image, its own
     on-screen text, its own TTS audio) followed immediately by a REVEAL
     segment (different background, different text, different TTS audio).
     Hard cut between them, NO crossfade, NO simultaneous overlap -- hook
     text and reveal text are never on screen together.
  2. AI content generation now returns 5 fields instead of 4: hook,
     reveal (renamed from script_english), hook_search_query (NEW --
     hook gets its own image, not shared with reveal), reveal_search_query
     (renamed from search_query), and caption. Hook technique now rotates
     across 5 distinct styles (curiosity gap, direct callout, bold claim,
     numbered-stakes, question) chosen randomly per generation, so hooks
     don't all follow the same pattern.
  3. Caption instruction changed from "matches tone, ends with follow
     CTA" to "a genuine question that prompts a comment" -- explicit
     engagement-bait removed in favor of real audience-response prompts.
  4. generate_tts() and create_reel_video() are now SINGLE-SEGMENT
     functions -- each takes one text/query/audio-path and produces one
     clip. run() calls each function TWICE per post (once per segment).
  5. NEW FUNCTION: concatenate_reel_segments() -- stitches the two
     independently-rendered segment clips into the final reel using
     moviepy's concatenate_videoclips(method="compose").
  6. run() rewritten to orchestrate the two-segment flow: hook TTS -> hook
     video -> reveal TTS -> reveal video -> concatenate -> publish. Any of
     these 5 steps failing independently blocks rotation advancement,
     same safety property as before, now checked at 5 points instead of 2.
  7. Text layout in create_reel_video() unified into one full-frame
     centered block per segment (previously: small italic hook line at
     top + separate body block below, which only made sense when both
     shared one screen). Hook segment uses larger italic type in the
     subtype's accent color; reveal segment uses the subtype's main serif/
     sans style in its main text color. Same PIL-measured overflow guard
     (multiline_textbbox + anchor clamping) protects both segments.

  FILES CHANGED:
  - build_prompt():              full rewrite for 2-segment JSON schema + rotating hook techniques
  - REQUIRED_CONTENT_KEYS:       hook, reveal, hook_search_query, reveal_search_query, caption
  - _validate_content_dict():    completeness check now targets "reveal" field (renamed)
  - generate_tts():              signature changed to (text, subtype, segment_label) -- single segment
  - create_reel_video():         signature changed to (text, search_query, tts_path, subtype, segment)
  - concatenate_reel_segments(): NEW function
  - run():                       rewritten to call TTS/video twice and concatenate

  VERIFIED (Aug 13, via direct testing, not just code read-through):
  - JSON schema fields in generated prompts match REQUIRED_CONTENT_KEYS exactly
  - Full run() orchestration dry-run (all external calls mocked): correct
    8-step call sequence, correct data flowing to each segment
  - Failure-path dry-run: a failed reveal-segment render correctly exits(1)
    and does NOT advance rotation_state.json
  - Real end-to-end render (fake background video + silent fake audio):
    hook segment renders as a real 1080x1920 clip with ONLY hook text
    visible; reveal segment renders with ONLY reveal text visible, in a
    visually distinct style; concatenation produces a real playable file
    with a clean hard cut and no overlap, confirmed by extracting and
    viewing actual frames from both sides of the cut
  NOT YET VERIFIED: real Pexels/Unsplash fetch, real TTS audio (network
  restrictions in the dev sandbox block both), and the real Instagram
  publish step -- these can only be confirmed from an actual deployed run.

v6.6 (prior) - Full TTS tuning + loop removal, Aug 12 2026
  WHAT CHANGED:
  1. Removed all loop-trick logic entirely (previously v6.4-6.5 only applied it
     to 2 of 9 subtypes; now 0 of 9 get it). Every subtype ends on a COMPLETE,
     properly-punctuated sentence, no trailing clauses like "which is why..."
     This fixes the truncated-content bug seen in production.
  2. Replaced rate-only TTS control with full rate + pitch + volume tuning per
     subtype. Each of 9 subtypes now has a deliberately different voice profile:
     - Warn (alarm):        fast (+8%), high pitch (+15Hz), loud (+12%)  = urgent
     - Command/Do (action): fast (+6%), neutral pitch, louder (+8%)       = brisk
     - Rule (numbered):     moderate (+2%), neutral, loud (+10%)         = blunt
     - Notice (observe):    slow (-4%), low pitch (-6Hz), normal volume  = analytical
     - Sit With/Truth (reflect): very slow (-10%), very low pitch (-15Hz), quiet (-5%) = weighty
     - Become (identity):   slow (-8%), low pitch (-10Hz), normal volume = weighty
     - Story (narrative):   slow (-6%), neutral pitch, normal volume     = storytelling
  3. Validation strengthened to check ALL subtypes for sentence completeness,
     unconditionally (not just non-loop subtypes). Any script_english or caption
     ending in a dangling word (because, which, that, etc.) or "..." gets
     rejected and triggers the next AI tier fallback.
  4. Removed loop_style field from all 9 subtype dicts (was dead code after
     loop removal, only left confusion about intent).
  5. Fixed overflow guard in create_reel_video() to use PIL's actual
     multiline_textbbox measurement instead of estimated line-height ratio,
     plus explicit anchor-point clamping so tall text never escapes the frame.

  FILES CHANGED:
  - build_prompt():            removed loop_style branching
  - _validate_content_dict():  now applies completeness check to all 9 subtypes
  - build_tts_pacing():        rebuilt entirely to return (text, rate, pitch, volume)
  - generate_tts() Tier 3:     now passes pitch/volume to edge_tts.Communicate()
  - create_reel_video():       fixed overflow guard measurement logic and anchor clamping
  - COLUMNS dict:              removed loop_style field from all 9 subtypes

v6.5 (prior) - Preparation phase, never deployed to production
  - Attempted loop-trick selective scoping (keep for 2 types, remove for 7)
  - Built pitch/volume infrastructure but file never reached GitHub repo

v6.4 (prior) - Truncation bug fix phase, never deployed to production
  - Added loop_style per-subtype branching
  - Strengthened validation for non-loop subtypes
  - Built initial overflow guard

v6.3 (production for ~48 hours until Aug 12) - Grid rotation system (stale in repo)
  - Original 3-column rotation with 9 subtypes
  - BUG: applied loop-trick instruction to ALL subtypes unconditionally
  - BUG: validation only checked field presence, not sentence completeness
  - Result: produced truncated captions like "...which is why" seen in Aug 12 video
  - NOTE: file at poster__5_.py in repo is still v6.3; this is v6.6

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
    getting a flat color card.

    v6.7: CONTENT STRATEGY CHANGE -- restructured from one continuous
    script into a two-beat HOOK -> REVEAL structure, per Areeb's request.
    Every reel now has two sequential parts in the SAME video: a hook that
    withholds the actual information (holds on screen ~1-3s), then the
    reel continues into the reveal that delivers what the hook promised.
    This is a genuine two-act structure, not just a headline + body split
    -- the hook must create real curiosity/tension, and the reveal must
    be the payoff. subtype['content_instruction'] (unchanged from before)
    still defines each subtype's VOICE/substance -- it now describes what
    the REVEAL should say, since that's the actual content each subtype
    was always designed to deliver. The hook is generated fresh each time
    using a rotating set of hook techniques so hooks don't all sound the
    same (a single hardcoded hook style was v6.3-v6.6's actual failure
    mode -- not just the completeness bug, but a repetitive hook pattern
    too).

    v6.5-6.6 (still true, unchanged): the mid-thought-loop trick is REMOVED
    for every subtype. Every subtype's REVEAL must end on a complete,
    properly punctuated sentence, no exceptions. This is even more
    important now than before, not less -- the reveal is the entire
    payoff the hook built tension toward, so a truncated reveal is a
    worse failure than a truncated single-script post ever was."""
    import random
    # Rotating hook techniques -- deliberately varied so the AI doesn't
    # settle into one repetitive pattern (e.g. always "The most X people
    # always Y" as seen in the Aug 12 production video). Picked randomly
    # per generation call, not tied to subtype, so hook VARIETY is
    # independent of which of the 9 content voices is active.
    HOOK_TECHNIQUES = [
        (
            "a CURIOSITY GAP hook -- name that something specific exists "
            "(a signal, a mistake, a tell) WITHOUT revealing what it is. "
            "e.g. 'There's one thing liars always do with their hands.' "
            "The viewer must feel they're missing information."
        ),
        (
            "a DIRECT CALLOUT hook -- address the viewer's own behavior or "
            "situation in second person, implying something is happening "
            "TO them right now. e.g. 'You've done this in every "
            "interview you've ever had.'"
        ),
        (
            "a BOLD CLAIM hook -- state a specific, slightly counter-"
            "intuitive claim as fact, with no hedging, that demands "
            "justification. e.g. 'Confident people interrupt less than "
            "anyone else in the room.'"
        ),
        (
            "a NUMBERED-STAKES hook -- reference a specific number or "
            "fraction to create concreteness and stakes. e.g. 'Only 1 in "
            "20 people can do this under pressure.'"
        ),
        (
            "a QUESTION hook -- ask a short, pointed question the viewer "
            "can't immediately answer, that the reveal will answer for "
            "them. e.g. 'Why do powerful people talk slower?'"
        ),
    ]
    hook_technique = random.choice(HOOK_TECHNIQUES)

    reveal_ending_instruction = (
        "- CRITICAL: The reveal field MUST end with a COMPLETE, properly "
        "punctuated sentence -- a full stop, not a trailing clause. Do "
        "NOT end mid-thought, do NOT trail off with words like "
        "'because...', 'which...', 'that...', or any dangling "
        "conjunction. The reader should feel the thought has fully "
        "landed by the final word. This is the payoff the hook built "
        "tension toward -- it must deliver completely, with nothing left "
        "hanging."
    )

    return f"""Act as a social tactics expert and psychological strategist writing for an Instagram account.

CONTENT TYPE FOR THIS POST: "{subtype['label']}" ({subtype['voice_register']} register)

This reel is TWO SEPARATE SEGMENTS spliced into one video -- NOT one
continuous scene. Each segment has its OWN background image and its OWN
narration audio. The hook and the reveal are NEVER shown on screen at
the same time -- segment 1 shows ONLY the hook, then it's replaced
entirely by segment 2, which shows ONLY the reveal.

SEGMENT 1 -- HOOK: withholds the actual information, creates curiosity/
tension. Use {hook_technique}

SEGMENT 2 -- REVEAL: delivers the actual payoff, in the voice/substance
described below.

{subtype['content_instruction']}

IMPORTANT VOICE RULES:
- The hook and reveal must feel like ONE continuous idea across the two
  segments, not two disconnected posts -- the reveal should feel like
  the natural continuation/payoff of the specific tension the hook
  created, not a generic fact that happens to follow any hook.
- Stay STRICTLY within the voice register described above for the
  REVEAL. Do not blend in instructional language if this is a
  reflective/observational type, and vice versa -- the whole point is
  that this voice register is DISTINCT from other post types on this
  account.
{reveal_ending_instruction}
- Keep total spoken content (hook + reveal combined) under 10 seconds
  when read aloud at a natural, moderate pace with pauses (roughly 25-35
  words total).
- The caption is NOT a generic follow-CTA. It must be a genuine QUESTION
  directed at the viewer that prompts them to comment -- something they
  can answer about themselves or their own experience, directly related
  to what the reveal just said. e.g. if the reveal is about silence
  under pressure, ask something like "What do you do when someone tries
  to provoke you into speaking first?" NOT "Follow for more."

Return STRICTLY valid JSON, no markdown fences, no preamble:
{{
  "hook": "The attention-grabbing hook line using the technique specified above (under 10 words)",
  "reveal": "The full payoff content in the voice register specified above -- what the hook promised, delivered completely",
  "hook_search_query": "a short 2-4 word visual search query for SEGMENT 1's background -- should visually evoke tension/mystery matching the hook, not the answer",
  "reveal_search_query": "{subtype['visual_mood_instruction']}",
  "caption": "A genuine, specific question directly tied to what the reveal said, that the viewer can only answer by commenting their own experience -- MUST end with an explicit comment CTA like 'Tell me in the comments' or 'Comment your answer below.'"
}}"""


def build_tts_pacing(subtype: dict, full_text: str) -> tuple:
    """
    Returns (paced_text, rate, pitch, volume) for Edge-TTS's Communicate().
    Implements "moderate speed with pauses, proper pronunciation, and
    emphasis" using ONLY what this library actually supports -- confirmed
    by reading edge-tts's installed source directly (communicate.py,
    data_classes.py), not assumed:

    Communicate() escapes ALL text via xml.sax.saxutils.escape before
    sending to Microsoft's TTS service. That means raw SSML tags like
    `<break time="450ms"/>` embedded in the text arrive as the LITERAL
    string "&lt;break time=450ms/&gt;" and get READ ALOUD as garbled
    words -- not interpreted as a pause. An earlier version of this
    function tried exactly that and would have shipped broken audio;
    caught by reading the library source before deploying, not left in.
    There is no per-word emphasis/stress control in this library at all --
    it accepts a flat rate/pitch/volume for the whole utterance, nothing
    finer-grained. This is a real ceiling of edge-tts, not a gap I can
    code around within it.

    What actually works, confirmed against Communicate()'s exact
    validation regex in data_classes.py:
    1. `rate`   -- format "[+-]\\d+%", overall speaking speed.
    2. `pitch`  -- format "[+-]\\d+Hz", overall pitch shift. This is the
                   closest thing to "emphasis" this library has: a lower
                   pitch reads as weightier/more serious (fits Sit With,
                   Truth, Become), a higher pitch reads as more urgent/
                   alert (fits Warn). It's a single shift for the whole
                   clip, not per-word stress -- real emphasis on
                   individual words isn't something this library can do.
    3. `volume` -- format "[+-]\\d+%", overall loudness.
    4. Comma insertion at "..." pause markers -- edge-tts's underlying
       neural voice genuinely produces an audible micro-pause at commas as
       normal prosody (not a special API call, just how the voice reads
       punctuation), so converting "..." to "," gives a real, working
       pause where the script wants one.

    Per-subtype values below are chosen deliberately per voice_register,
    not just a blanket "sound better" tweak:
    - imperative/actionable (Command, Do): faster rate, neutral pitch,
      slightly louder -- reads as brisk and directive.
    - alarm (Warn): faster rate, RAISED pitch, louder -- reads as urgent,
      like catching something in real time.
    - aphoristic/universal_truth/identity_statement (Sit With, Truth,
      Become): slower rate, LOWERED pitch, slightly quieter -- reads as
      weighty and deliberate, matching a closing/reflective thought.
    - observational (Notice): slightly slower rate, neutral-low pitch --
      reads as measured and analytical.
    - numbered_rule (Rule): moderate rate, neutral pitch, louder -- reads
      as declarative and blunt.
    - micro_scenario (Story): slower rate, neutral pitch -- reads as
      narrative/storytelling cadence.
    """
    paced_text = full_text.replace("...", ",")
    register = subtype.get("voice_register", "")

    # (rate, pitch, volume) per register -- all values pre-validated
    # against edge-tts's exact regex (whole numbers, correct sign, correct
    # unit per parameter).
    REGISTER_TTS_PROFILES = {
        "imperative":         ("+6%",  "+0Hz",  "+8%"),   # Command: brisk, direct, a touch louder
        "actionable_steps":   ("+6%",  "+0Hz",  "+8%"),   # Do: same brisk directive energy
        "alarm":              ("+8%",  "+15Hz", "+12%"),  # Warn: urgent, raised pitch, louder
        "aphoristic":         ("-10%", "-15Hz", "-5%"),   # Sit With: slow, weighty, quieter
        "universal_truth":    ("-10%", "-15Hz", "-5%"),   # Truth: same weighty register
        "identity_statement": ("-8%",  "-10Hz", "-3%"),   # Become: weighty but slightly warmer
        "observational":      ("-4%",  "-6Hz",  "+0%"),   # Notice: measured, analytical
        "numbered_rule":      ("+2%",  "+0Hz",  "+10%"),  # Rule: declarative, blunt, louder
        "micro_scenario":     ("-6%",  "+0Hz",  "+0%"),   # Story: narrative storytelling pace
    }
    rate, pitch, volume = REGISTER_TTS_PROFILES.get(register, ("-2%", "+0Hz", "+0%"))

    return paced_text, rate, pitch, volume


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
REQUIRED_CONTENT_KEYS = ["hook", "reveal", "hook_search_query", "reveal_search_query", "caption"]

def _validate_content_dict(data, subtype: dict = None) -> bool:
    """
    Confirms the AI actually returned every field the rest of the pipeline
    needs. If a key is missing/empty, treat this as a FAILURE of that
    provider (fall through to the next AI tier) instead of crashing later,
    deep inside TTS or video generation, with a confusing KeyError.

    Also checks sentence COMPLETENESS, not just field PRESENCE -- a
    reveal value like "...waiting to see if you'll laugh along and let
    them slide, because..." used to pass this check fine (it's a
    non-empty string) even though it's a truncated sentence. That produced
    real cut-off captions/reels in production.

    v6.7: field renamed from script_english to reveal, matching the new
    two-beat hook->reveal content structure (see build_prompt()). The
    completeness check below now applies to the reveal field specifically
    -- this matters MORE now than before, since the reveal is the actual
    payoff the hook built tension toward. A truncated reveal after a hook
    has already created anticipation is a worse failure than a truncated
    single-script post ever was.

    v6.5-6.6 (still true): this completeness check applies to EVERY
    subtype unconditionally. An earlier version skipped it for subtypes
    flagged "mid_thought_loop" (a deliberate seamless-replay trick for 2
    of 9 types) -- that trick was removed entirely per Areeb's request
    ("get rid of all loops everywhere, didn't work out well"), so there's
    no longer any subtype where a dangling sentence is intentional. This
    is a second, independent layer of defense on top of the prompt
    instruction in build_prompt() -- it catches the case where the AI
    ignores that instruction, rather than trusting the instruction alone.
    subtype=None still skips the completeness check (used when a caller
    validates without a subtype in hand, e.g. in isolated tests) -- field
    presence is still checked either way.
    """
    if not (isinstance(data, dict) and all(data.get(k) for k in REQUIRED_CONTENT_KEYS)):
        return False

    if subtype is None:
        return True

    # Words that, as the LAST word of a sentence, almost always signal a
    # truncated/dangling clause rather than a real ending. Checked against
    # the final word only (case-insensitive, punctuation stripped) -- not
    # scanning for these words anywhere in the text, since e.g. "because"
    # is a perfectly normal word to use mid-sentence.
    DANGLING_LAST_WORDS = {
        "because", "which", "that", "who", "whose", "if", "when", "while",
        "since", "as", "so", "and", "but", "or", "to", "of", "the", "a",
        "an", "with", "for", "in", "on", "at", "by",
    }
    import re
    for field in ("reveal", "caption"):
        text = str(data.get(field, "")).strip()
        if not text:
            continue
        # Strip a trailing "..." explicitly first -- three dots at the end
        # is itself a strong truncation signal regardless of what word
        # precedes it, distinct from the word-based check below.
        if text.endswith("..."):
            return False
        words = re.findall(r"[a-zA-Z']+", text)
        if words and words[-1].lower() in DANGLING_LAST_WORDS:
            return False
        # A sentence that doesn't end in terminal punctuation at all
        # (., !, ?, or a closing quote/paren after one of those) is also
        # a truncation signal for these subtypes.
        if not re.search(r'[.!?]["\')]?\s*$', text):
            return False

    return True

def generate_content(subtype: dict) -> dict:
    """
    CHANGED IN v6.3: now takes `subtype` (one of the 9 dicts from
    column_types.py, chosen by the rotation tracker in run() below) instead
    of using one fixed prompt for every post. build_prompt() reads that
    sub-type's content_instruction/voice_register and constructs a prompt
    specific to it -- e.g. "command" gets an imperative-instruction prompt,
    "sit_with" gets a quiet-aphorism prompt. Everything below this line
    (the actual 4-tier AI failover chain) is UNCHANGED from v6.2, except
    that _validate_content_dict() now also receives `subtype` so it can
    check sentence-completeness for the 7 subtypes that need it (see that
    function's docstring for the v6.4 bug fix this implements).
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
            if _validate_content_dict(data, subtype):
                print("✅ Generated content successfully via Gemini!")
                return data
            print(f"⚠️ Gemini response was missing required fields or ended mid-sentence: {data}. Moving to Fallback Chain...")
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
            if _validate_content_dict(data, subtype):
                print(f"✅ Generated content successfully via {provider['name']}!")
                return data
            print(f"⚠️ {provider['name']} response was missing required fields or ended mid-sentence: {data}")
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

def generate_tts(text: str, subtype: dict, segment_label: str = "segment") -> list:
    """
    v6.7 CONTENT STRATEGY CHANGE: this function now generates audio for
    ONE SEGMENT at a time (either the hook or the reveal), not a combined
    hook+reveal string. Previously it took the whole `data` dict and
    joined data['hook'] + "... " + data['script_english'] into one
    full_text internally -- that made sense when hook and reveal were one
    continuous scene. Now that they're two genuinely separate video
    segments (separate image, separate on-screen text, per Areeb's
    explicit clarification: "Hook and actual content should not be
    present together simultaneously on the same screen"), run() calls
    this function TWICE -- once with the hook text, once with the reveal
    text -- and create_reel_video() is called twice to match, then the
    two resulting clips are concatenated. `segment_label` is used only
    for clearer log lines (e.g. "[TTS 1/4] Generating HOOK audio..."), it
    doesn't change any generation logic.

    Still applies per-sub-type pacing via build_tts_pacing() -- real rate
    control (slightly faster for urgent/alarm content, slower for
    reflective content) plus pitch/volume tuning plus comma-based pauses.
    (See build_tts_pacing()'s own docstring for why this uses comma
    insertion rather than SSML <break> tags -- that approach was tried
    first and confirmed broken by reading edge-tts's actual source before
    shipping it.)
    """
    # Defensive check -- even though the caller (run()) always passes a
    # real string, this guards against a future edit accidentally passing
    # None or an empty segment through silently.
    full_text = (text or "").strip()
    if not full_text:
        print(f"❌ FATAL: No {segment_label} text available to speak (empty string).")
        return []

    out_path = f"output/tts_{segment_label}_{int(time.time())}.mp3"

    # Tier 1: ElevenLabs
    if ELEVENLABS_API_KEY:
        try:
            print(f"🎙️ [TTS 1/4] Trying ElevenLabs for {segment_label}...")
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
                print(f"✅ ElevenLabs Audio generated successfully for {segment_label}!")
                return [out_path]
            print("⚠️ ElevenLabs returned an empty/too-small file. Moving to Groq TTS...")
        except Exception as e:
            print(f"⚠️ ElevenLabs failed ({e}). Moving to Groq TTS...")

    # Tier 2: Groq TTS
    if GROQ_API_KEY:
        try:
            print(f"🎙️ [TTS 2/4] Trying Groq TTS for {segment_label}...")
            client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=GROQ_API_KEY, timeout=HTTP_TIMEOUT_SECONDS)
            response = client.audio.speech.create(
                model="canopylabs/orpheus-v1-english",
                voice="hannah",
                input=full_text,
                response_format="wav",  # v6.9 FIX: Groq now rejects this model's default format; confirmed from the exact API error and now requested explicitly
            )
            response.stream_to_file(out_path)
            if _valid_audio_file(out_path):
                print(f"✅ Groq TTS Audio generated successfully for {segment_label}!")
                return [out_path]
            print("⚠️ Groq TTS returned an empty/too-small file. Moving to Edge-TTS...")
        except Exception as e:
            print(f"⚠️ Groq TTS failed ({e}). Moving to Edge-TTS...")

    # Tier 3: Edge-TTS (Bulletproof local safety net -- free, no API key needed)
    # Uses build_tts_pacing() for per-sub-type rate + pitch + volume +
    # comma-based pauses (see that function's docstring for why raw SSML
    # <break> tags do NOT work with this library -- verified by reading
    # edge-tts's source, not assumed, including the exact accepted format
    # for each parameter). ElevenLabs/Groq tiers above take plain text
    # with no per-call pacing knob in this simple API path, so they're
    # left as raw full_text -- unchanged.
    try:
        print(f"🎙️ [TTS 3/4] Generating fallback via Edge-TTS for {segment_label} (with pacing)...")
        import asyncio
        import edge_tts
        paced_text, rate, pitch, volume = build_tts_pacing(subtype, full_text)
        async def _speak():
            # rate/pitch/volume are all real Communicate() parameters,
            # confirmed against the library's own validation regex in
            # data_classes.py (rate/volume: "[+-]\d+%", pitch: "[+-]\d+Hz").
            # paced_text has "..." converted to "," which edge-tts's
            # neural voice genuinely pauses on as normal comma prosody.
            communicate = edge_tts.Communicate(
                paced_text, "en-US-ChristopherNeural",
                rate=rate, pitch=pitch, volume=volume,
            )
            await communicate.save(out_path)
        # edge-tts has no built-in timeout knob (it's a raw websocket call)
        # -- wrap it so a hung connection can't stall the whole job.
        asyncio.run(asyncio.wait_for(_speak(), timeout=60))
        if _valid_audio_file(out_path):
            print(f"✅ Edge-TTS Audio generated for {segment_label}! (rate={rate}, pitch={pitch}, volume={volume})")
            return [out_path]
        print(f"❌ FATAL: Edge-TTS also returned an empty/too-small file for {segment_label}.")
        return []
    except Exception as e:
        print(f"❌ FATAL: All TTS providers failed for {segment_label}: {e}")
        return []


# ============================================================
# REEL COMPOSITOR
# ============================================================
def create_reel_video(text: str, search_query: str, tts_path: str, subtype: dict, segment: str) -> str:
    """
    v6.7 CONTENT STRATEGY CHANGE: this function now renders ONE SEGMENT of
    the reel at a time (either the hook or the reveal) as its own
    standalone video clip -- not a combined hook+body single scene.
    run() calls this TWICE per post (once for the hook, once for the
    reveal) and concatenates the two resulting clips with
    concatenate_reel_segments() below. This matches Areeb's explicit
    clarification: "each single reel should use two images - 1st image
    for the hook, 2nd image for the actual content... Hook and actual
    content should not be present together simultaneously on the same
    screen." Each segment gets its OWN background fetch (own
    search_query) and its OWN TTS audio (own tts_path) -- genuinely
    independent, not two views into one shared scene.

    `segment` is "hook" or "reveal" -- controls ONLY the text layout (the
    hook gets one large centered block since it's the only text on that
    screen; previously there was a small italic line near the top PLUS a
    separate body block below it, which doesn't make sense when the hook
    is alone on its own screen with nothing to sit above). Background
    fetch, tint, and video-composite logic is otherwise IDENTICAL for
    both segments.

    UNCHANGED FROM v6.6:
    1. BACKGROUND SOURCE + TREATMENT: fetches a real Pexels/Unsplash
       video/image via get_reel_background(), tinted with subtype's brand
       color at subtype["overlay_opacity"]. Bold/graphic subtypes
       (command/warn/rule) use a strong tint (~0.70-0.72) so the brand
       color still reads instantly; quieter/narrative subtypes
       (sit_with/story) use a lighter tint (~0.35-0.55).
    2. TEXT STYLING: colors/fonts pulled from the sub-type dict.
    3. OVERFLOW GUARD: uses PIL's actual multiline_textbbox measurement
       plus anchor-point clamping so long text never escapes the frame --
       this matters for the reveal especially, since a truncated reveal
       after the hook already built tension is now a worse failure than
       before.
    """
    print(f"🎬 Compositing 1080x1920 [{segment.upper()}] segment with MoviePy [{subtype['label']} / {subtype['key']}]...")
    try:
        from moviepy.editor import VideoFileClip, AudioFileClip, CompositeVideoClip, ImageClip
        import numpy as np

        tts_audio = AudioFileClip(tts_path)
        duration = min(tts_audio.duration + 1, 15)  # +1s tail instead of +2s -- each segment is shorter than the old combined scene, so less trailing padding needed per segment

        # Every subtype attempts a real background fetch now -- no more
        # needs_photo_bg gate. get_reel_background() already has its own
        # Pexels -> Unsplash -> (None, False) fallback chain (unchanged,
        # verified directly in that function above), so a failed fetch
        # here just falls through to the flat-color branch below exactly
        # as it always could.
        bg_path, is_video = get_reel_background(search_query or "dark moody cinematic scene")

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
            font_brand = ImageFont.truetype(FONT_SANS, 28)
        except:
            font_brand = ImageFont.load_default()

        hook_color = subtype.get("accent_color", "#E0C080")
        body_color = subtype.get("text_color", "#FFFFFF")
        # Hook segment uses the accent color (brighter/more attention-
        # grabbing), reveal segment uses the main text color -- same
        # per-subtype palette as before, just applied per-segment instead
        # of both appearing together on one screen.
        text_color = hook_color if segment == "hook" else body_color

        # OVERFLOW GUARD: every segment's text (hook OR reveal) uses this
        # full-frame centered layout with dynamic font-shrink, since each
        # is now the ONLY text on its own screen -- there's no separate
        # "headline above, body below" split anymore (that made sense
        # when hook+script_english shared one screen; it doesn't once
        # they're on separate screens entirely). This is the exact same
        # measurement approach validated earlier: an initial version
        # estimated wrapped-text height via a fixed line_height_ratio
        # constant and was found inaccurate in BOTH directions on a
        # stress test (triggered unnecessary shrinks, and after removing
        # them, real renders landed only ~14px inside the boundary with
        # almost no margin). Replaced with PIL's own multiline_textbbox()
        # call, which measures the ACTUAL rendered bounding box for the
        # real font/text/spacing -- not an approximation -- plus a small
        # explicit margin so even a measured "just fits" case has
        # breathing room.
        available_height = (1650 - 300) - 40  # frame space above the brand watermark, minus safety margin
        base_font_size = 52  # larger than the old body size (44) since this text now owns the full screen alone
        text_font_path = FONT_ITALIC if segment == "hook" else body_font_path

        def _wrap_and_measure(font_size):
            f = ImageFont.truetype(text_font_path, font_size)
            lines = []
            for line in raw_lines:
                wrap_width = int(24 * (52 / font_size))
                if line.strip():
                    lines.extend(textwrap.wrap(line, width=wrap_width))
                else:
                    lines.append("")
            wrapped_text = "\n".join(lines)
            bbox = draw.multiline_textbbox((0, 0), wrapped_text, font=f, spacing=24, align="center")
            measured_height = bbox[3] - bbox[1]
            return f, lines, measured_height

        raw_lines = (text or "").strip().split("\n")
        font_size = base_font_size
        text_font, wrapped_lines, measured_height = _wrap_and_measure(font_size)
        # Shrink in steps until it fits, with a floor so text never
        # becomes illegibly small -- if even the floor size doesn't fit,
        # render at the floor anyway (better a tight fit than an infinite
        # loop or a crash).
        while measured_height > available_height and font_size > 32:
            font_size -= 2
            text_font, wrapped_lines, measured_height = _wrap_and_measure(font_size)

        final_text = "\n".join(wrapped_lines)
        # Anchor="mm" centers on y=960 regardless of block height, which
        # can still push a tall block's TOP/BOTTOM edge outside the safe
        # frame area even when total measured height is within budget
        # (font metrics used for centering don't perfectly match the
        # tight bbox used for measurement above). Explicitly clamp the
        # vertical center between y=300 (top safe boundary) and y=1650
        # (above the brand watermark) so this directly controls the
        # failure mode instead of relying on the height budget alone.
        final_bbox = draw.multiline_textbbox((0, 0), final_text, font=text_font, spacing=24, align="center")
        final_text_height = final_bbox[3] - final_bbox[1]
        min_center_y = 300 + (final_text_height / 2)
        max_center_y = 1650 - (final_text_height / 2)
        text_center_y = max(min_center_y, min(960, max_center_y))
        draw.text((540, text_center_y), final_text, font=text_font, fill=text_color, anchor="mm", align="center", spacing=24)
        draw.text((540, 1720), IG_HANDLE, font=font_brand, fill=subtype.get("accent_color", "#888888"), anchor="mm")

        overlay_fname = f"output/overlay_{segment}_{int(time.time())}.png"
        overlay_img.save(overlay_fname)
        txt_clip = ImageClip(overlay_fname, duration=duration)

        final_video = CompositeVideoClip([bg_clip, txt_clip]).set_audio(tts_audio)
        reel_path = f"output/segment_{segment}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        # v6.8 FIX: added ffmpeg_params=["-movflags", "+faststart"]. Confirmed
        # directly from moviepy 1.0.3's installed source
        # (ffmpeg_writer.py) that this flag was NEVER being passed by
        # default -- moviepy's own ffmpeg command construction has no
        # movflags handling at all unless explicitly supplied via this
        # parameter. Confirmed from Meta's own Instagram Graph API docs
        # that this is a real, stated requirement: "moov atom at the front
        # of the file." Without it, ffmpeg writes the moov atom at the END
        # of the file by default -- a file like that plays fine locally
        # (most players buffer the whole file first) and uploads fine to
        # any generic host (which doesn't inspect the internal structure),
        # but Instagram's own video processor is documented to require the
        # front-loaded moov atom specifically, which matches the exact
        # symptom seen in production: upload succeeded, then IG's own
        # container processing failed with {'status_code': 'ERROR'} and no
        # further detail (a gap in visibility also fixed in
        # post_to_instagram()'s polling call, see that function for the
        # "status" field fix).
        final_video.write_videofile(
            reel_path, fps=24, codec="libx264", audio_codec="aac",
            verbose=False, logger=None,
            ffmpeg_params=["-movflags", "+faststart"],
        )

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


def concatenate_reel_segments(hook_video_path: str, reveal_video_path: str) -> str:
    """
    v6.7 NEW FUNCTION: stitches the two independently-rendered segment
    clips (hook, then reveal) into one final reel file, back to back with
    no overlap and no crossfade -- a hard cut, matching Areeb's
    requirement that hook and reveal content never appear on screen
    together. Each input clip already has its own correct audio (from its
    own TTS call) baked in via create_reel_video()'s
    CompositeVideoClip(...).set_audio(...) step, so concatenation here is
    audio+video together, not video-only with a separate audio merge.

    Uses moviepy's concatenate_videoclips with method="compose" rather
    than the default "chain" -- "compose" pads any inconsistent frame
    sizing between the two clips onto a common canvas instead of failing
    outright, which matters here because the hook and reveal clips come
    from two SEPARATE get_reel_background() fetches that could technically
    return sources with slightly different native aspect ratios before
    the existing resize/crop-to-1080x1920 step in create_reel_video()
    normalizes them -- "compose" is a safety net on top of that
    normalization, not a replacement for it.
    """
    print("🔗 Concatenating hook + reveal segments into final reel...")
    try:
        from moviepy.editor import VideoFileClip, concatenate_videoclips

        hook_clip = VideoFileClip(hook_video_path)
        reveal_clip = VideoFileClip(reveal_video_path)

        final_clip = concatenate_videoclips([hook_clip, reveal_clip], method="compose")
        final_path = f"output/reel_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        # v6.8 FIX: same -movflags +faststart fix as create_reel_video()
        # above, and MORE important here specifically -- this call
        # produces the FINAL file that actually gets uploaded to
        # Instagram (the two segment-level files from create_reel_video()
        # are only intermediate inputs to this concatenation step and get
        # deleted afterward in run() on success). If only the segment-level
        # write_videofile had been fixed and this one missed, the
        # per-segment intermediate files would have had the correct moov
        # atom position but the actual published file would not have --
        # since concatenate_videoclips() re-encodes rather than just
        # concatenating the raw bytes, this write_videofile call is a
        # completely independent ffmpeg invocation that needs its own
        # explicit flag, not something inherited from the inputs.
        final_clip.write_videofile(
            final_path, fps=24, codec="libx264", audio_codec="aac",
            verbose=False, logger=None,
            ffmpeg_params=["-movflags", "+faststart"],
        )

        hook_clip.close()
        reveal_clip.close()

        # Same sanity check as create_reel_video's own output check --
        # a real concatenated 2-segment reel is always well over 100KB
        # (roughly double the single-segment 50KB floor, since it's two
        # segments' worth of video+audio).
        if not os.path.exists(final_path) or os.path.getsize(final_path) < 100_000:
            print("❌ Concatenated video file is missing or suspiciously small -- treating as a failed render.")
            return None

        print(f"✅ Final reel assembled: {final_path} (hook: {hook_clip.duration:.1f}s + reveal: {reveal_clip.duration:.1f}s)")
        return final_path
    except Exception as e:
        print(f"❌ Segment concatenation failure: {e}")
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
                # v6.8 FIX: previously only requested "status_code", which
                # on an ERROR container returns just the bare word "ERROR"
                # with no explanation -- exactly what the Aug 12 failure
                # log showed: {'status_code': 'ERROR', 'id': '...'} and
                # nothing else to diagnose from. Instagram's Graph API has
                # a SEPARATE "status" field that carries a human-readable
                # explanation on error (e.g. a specific codec/format
                # rejection reason) -- other working implementations
                # request "id,status,status_code" together for exactly
                # this reason. Requesting it now so a future ERROR is
                # actually diagnosable from the Actions log directly.
                params={"fields": "status_code,status", "access_token": INSTAGRAM_ACCESS_TOKEN}
            )
            code = status.get("status_code")
            if code == "FINISHED":
                finished = True
                break
            elif code == "ERROR":
                print(f"❌ IG reported a processing error on the container: {status}")
                print(f"   -> Full container response for debugging: id={container_id}, status_code={code}, status={status.get('status', '<not provided by API>')}")
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

    # v6.7 CONTENT STRATEGY CHANGE: hook and reveal are now two genuinely
    # separate segments -- own audio, own background image, own on-screen
    # text -- concatenated into one final reel. Each of the 4 steps below
    # (hook TTS, hook video, reveal TTS, reveal video) can independently
    # fail; if ANY of them does, the whole run fails and the rotation does
    # NOT advance, exactly the same safety property as before, just now
    # checked at 4 points instead of 2.
    print("\n--- SEGMENT 1: HOOK ---")
    hook_tts_paths = generate_tts(data.get("hook", ""), subtype, segment_label="hook")
    if not hook_tts_paths:
        print("❌ FATAL: No usable audio was produced for the HOOK segment.")
        print(f"   -> Rotation NOT advanced (still Column {column_num}/'{subtype['key']}' next run).")
        sys.exit(1)

    hook_video_path = create_reel_video(
        text=data.get("hook", ""),
        search_query=data.get("hook_search_query", ""),
        tts_path=hook_tts_paths[0],
        subtype=subtype,
        segment="hook",
    )
    if not hook_video_path:
        print("❌ FATAL: HOOK segment video render failed.")
        print(f"   -> Rotation NOT advanced (still Column {column_num}/'{subtype['key']}' next run).")
        sys.exit(1)

    print("\n--- SEGMENT 2: REVEAL ---")
    reveal_tts_paths = generate_tts(data.get("reveal", ""), subtype, segment_label="reveal")
    if not reveal_tts_paths:
        print("❌ FATAL: No usable audio was produced for the REVEAL segment.")
        print(f"   -> Rotation NOT advanced (still Column {column_num}/'{subtype['key']}' next run).")
        sys.exit(1)

    reveal_video_path = create_reel_video(
        text=data.get("reveal", ""),
        search_query=data.get("reveal_search_query", ""),
        tts_path=reveal_tts_paths[0],
        subtype=subtype,
        segment="reveal",
    )
    if not reveal_video_path:
        print("❌ FATAL: REVEAL segment video render failed.")
        print(f"   -> Rotation NOT advanced (still Column {column_num}/'{subtype['key']}' next run).")
        sys.exit(1)

    print("\n--- ASSEMBLING FINAL REEL ---")
    reel_path = concatenate_reel_segments(hook_video_path, reveal_video_path)
    if reel_path:
        success = post_to_instagram(reel_path, caption)
        if success:
            # ONLY save the advanced rotation state here, after a confirmed
            # successful publish -- see the big comment above run() for why
            # this ordering is load-bearing, not arbitrary.
            save_rotation_state(state)
            # Clean up the intermediate per-segment files now that the
            # final concatenated reel has been confirmed published -- the
            # segment_hook_*.mp4 / segment_reveal_*.mp4 files served their
            # purpose as inputs to concatenate_reel_segments() and aren't
            # needed after a successful run. Left in place on FAILURE
            # (no cleanup call in any of the sys.exit(1) branches above)
            # so a failed run's intermediate files are still on disk for
            # debugging in the Actions log/artifact, if needed.
            for leftover in (hook_video_path, reveal_video_path):
                try:
                    os.remove(leftover)
                except OSError:
                    pass
            print(f"\n✅ WORKFLOW COMPLETED SUCCESSFULLY! (Column {column_num} / '{subtype['key']}' posted)")
            print(f"   Next run will post: Column {state['next_column']}")
        else:
            print("\n❌ WORKFLOW FAILED at the Instagram publish step -- see the ❌/⚠️ lines above for the exact reason.")
            print(f"   -> Rotation NOT advanced (still Column {column_num}/'{subtype['key']}' next run).")
            sys.exit(1)
    else:
        print("\n❌ WORKFLOW FAILED at final segment concatenation -- see the ❌/⚠️ lines above for the exact reason.")
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
