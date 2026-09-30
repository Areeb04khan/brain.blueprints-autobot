# -*- coding: utf-8 -*-
"""
Brain Blueprints Bot v7.3 (Multi-Tier AI & TTS Failover Engine + 5-Field
                           Rotation System + Hindi 5-Segment Listicle
                           Content Structure + Theme-First Content Model)
- AI Chain:    Gemini -> OpenRouter -> Groq -> NVIDIA NIM (unchanged, language-agnostic)
- TTS Chain:   ElevenLabs (Hindi) -> Edge-TTS (Hindi)  [Groq TTS dropped -- no Hindi model, see v7.0 notes]
- Media Host:  tempfile.org -> catbox.moe
- Fully automated Hindi life-advice reels ("4 baatein" format, multiple life fields)

VERSION HISTORY (each version incremented on every change, no matter how small):

v7.3 (CURRENT) - Production bug fixes: Devanagari rendering + TTS repetition, Sep 28 2026
  Areeb ran v7.1 in production (the last version actually delivered to
  him -- v7.2 above was built but not yet shipped when this report came
  in) and hit two real bugs: on-screen text showing boxes instead of
  Hindi letters, and TTS audio "repeating" with bad pronunciation/tone.
  Both root-caused from the actual code rather than guessed at.

  1. BOXES INSTEAD OF LETTERS. Traced exactly how this could happen with
     NO crash (a genuinely missing font file raises inside
     create_reel_video()'s try/except and fails the run loudly, so a
     silent bad-looking video pointed elsewhere). Devanagari needs TWO
     preconditions, and only one was ever being relied on:
       - The font FILES (fonts-noto-core) -- checked before, but only
         indirectly (a crash if missing, not a clear message).
       - Pillow built WITH libraqm (complex text shaping for conjuncts/
         matra reordering). THIS is the one that fails silently: if
         raqm is missing, ImageFont.truetype() does NOT raise, the font
         loads fine, and rendering just falls back to naive glyph
         layout -- which is exactly a "no crash, but boxes" failure. My
         earlier testing verified Devanagari rendering correctly in MY
         dev sandbox, but never confirmed raqm would be present in
         Areeb's actual environment -- a real gap in what "verified"
         covered.
     FIX: validate_environment() now checks both explicitly --
     PIL.features.check("raqm") and each Devanagari font file's
     existence -- and exits with a specific, actionable message naming
     the exact fix for whichever one is missing, before any expensive
     work runs. Placed BEFORE the Instagram network check (both are
     local, instant, network-free -- no reason to wait on a network
     round-trip to catch a local misconfiguration first).
  2. TTS "REPEATING", BAD PRONUNCIATION/TONE. Leading cause: v7.1 raised
     CONTENT_TEMPERATURE from 0.7 to 1.0 for catchier phrasing. Higher
     sampling temperature is a well-documented cause of degenerate
     repetition loops in LLM generation, and none of the 4 AI tiers here
     have a repetition/frequency penalty set -- likely my mistake in
     v7.1, raising the one knob that increases repetition risk without
     adding the knob that guards against it. TTS reads back exactly the
     text it's given, so a repeated clause in the generated text is
     exactly what "repeating" audio sounds like, and an awkward
     higher-temperature sentence reads back with worse prosody even
     short of outright repetition.
     FIX (defense in depth, not reliant on one guess being exactly
     right):
       - CONTENT_TEMPERATURE: 1.0 -> 0.85 (still above the original
         conservative 0.7, kept for catchiness, pulled back from the
         value most likely to have caused this).
       - _validate_content_dict(): NEW repetition guard -- rejects a
         response if any 4+ word run repeats verbatim within one text
         field, or if two segments (hook/points/caption) come back as
         exact duplicates. Falls through to the next AI tier exactly
         like any other malformed response already does.
       - build_prompt(): added an explicit no-repetition instruction
         alongside the existing completeness/specificity rules.
     Groq TTS remains correctly absent (still no Hindi model -- verified
     in v7.0, unrelated to this).

  NOT CHANGED: FIELDS, the 5-segment structure, fonts, video compositing,
  concatenation -- this pass is entirely about the two specific failure
  modes reported, not a broader rewrite.

  FILES CHANGED:
  - validate_environment():     NEW raqm + font-file preflight checks, reordered before the Instagram network check
  - CONTENT_TEMPERATURE:        1.0 -> 0.85
  - _validate_content_dict():   NEW repetition guard (intra-text word-run repeats + cross-segment exact duplicates)
  - build_prompt():             NEW no_repetition_instruction wired into the returned prompt

  NOT VERIFIED: this pass was implemented and reasoned through without
  sandbox execution (Areeb asked that this round of work not be run/
  tested in the sandbox), so unlike every earlier version in this file,
  none of this was empirically exercised before delivery -- reviewed
  carefully by hand instead. The preflight checks are simple enough
  (a boolean feature check, a file-existence check) that this is a
  reasonable tradeoff, but the very first real run's log is the actual
  test for all of this, more so than usual.

v7.2 (prior) - Theme-first content model + narrative arc, Sep 27 2026
  Areeb brought in an outside content-strategy review of v7.1's output
  design (the v7.1 catchiness pass helped, but he wanted the content
  itself stronger). Its core diagnosis: the prompt still produced "4 tips
  about a broad field" -- generic, listicle-shaped, with exaggerated hooks.
  Evaluated point by point against what was already built and tested,
  rather than adopted wholesale.

  ADOPTED (all prompt/content changes -- rendering, TTS, fonts, badge,
  concatenation and validation logic are untouched):
  1. THEME-FIRST. The AI now picks ONE specific theme inside the field
     each run ("topic", the FIRST key in the JSON -- a model writes JSON
     in order, so stating the theme first makes it commit to it before
     writing the hook) and builds hook + all 4 points + caption around
     it. FIELDS stay the rotating category (visual identity + voice);
     each field gained 3 example_themes for calibration (2 shown at
     random per run, model told not to reuse them).
  2. NO REPEATS. Added get_recent_topics() + a recent_topics parameter on
     generate_content()/build_prompt(): the last 8 posted themes are shown
     to the model as a blocklist. run() records each theme into
     rotation_state.json's history ONLY after a confirmed publish (same
     safety rule as the rotation itself). Not in the outside review, but
     a theme-first design without it tends to converge on the same few
     themes per field. Backward compatible: old history entries have no
     "topic" and are simply skipped.
  3. ARC. The 4 points now have jobs -- situation -> reframe -> action ->
     takeaway -- instead of being 4 interchangeable tips. (Merged two
     overlapping suggestions from the review into one structure.) The
     JSON is still points[4] of {text, search_query}.
  4. LESS CLICKBAIT. Hook techniques rewritten around relevance +
     curiosity + specificity; "ज़िंदगी बदल देंगी" / "आखिरी वाली सबसे
     ज़रूरी है" promises removed and explicitly forbidden in the prompt.
  5. SPECIFICITY RULES. Each point needs a concrete element (behavior,
     decision, boundary, observation, mistake, example or situation);
     six stock phrases (खुद पर विश्वास रखो, मेहनत करते रहो, ...) are
     banned unless the sentence says exactly how/when.

  DELIBERATELY NOT ADOPTED:
  - Changing the JSON to points[3] + a separate final_takeaway field. The
    creative goal (point 4 as the memorable closing line) is fully met by
    giving point 4 that job in the prompt. The schema change would have
    rippled through _validate_content_dict, run(), and the "बात X/4"
    badge -- all currently tested and working -- for no extra creative
    benefit.
  - A separate point_search_queries[4] array. Each point already carries
    its own search_query inside its own object, which is safer than two
    parallel arrays that could drift out of index alignment.

  ALSO FIXED WHILE HERE (found during this pass, not from the review):
  - Hook/CTA examples in the prompt were Roman Hindi while the prompt
    demanded Devanagari (my v7.0/v7.1 mistake) -- now all Devanagari.
  - v7.1's walking example claimed an effect "more than any supplement",
    an unverifiable health claim the model could have copied -- replaced.
  - Field content_instructions said "the 4 points must each be ONE tip",
    which contradicted the new arc -- reworded to domain + voice only.
    Removed a stale reference to the pre-v7.0 "Command" voice.
  - Content guardrails: sehat never makes medical claims/diagnoses;
    career_paisa never recommends specific stocks/funds or promises
    returns (account gives everyday-habit advice, not health/finance
    advice).
  - This header's title still said v7.0 after the v7.1 bump.

  FILES CHANGED:
  - FIELDS:                   content_instruction reworded x5, example_themes added x5
  - REQUIRED_CONTENT_KEYS:    "topic" added (required, and deliberately kept out of the sentence-completeness check -- it's a label, not spoken prose)
  - get_recent_topics():      NEW, next to the rotation helpers
  - build_prompt():           new signature (recent_topics), theme-first STEP 1/STEP 2 structure, arc, hooks, specificity rules, JSON with "topic" first
  - generate_content():       new optional recent_topics, passed through; failover body untouched
  - run():                    passes recent topics in, logs theme + hook, records topic after a confirmed publish

  NOT VERIFIED (same honest limit as v7.1): actual model output quality
  and how much the arc/theme instructions change real Hindi output. That
  can only be judged from real runs -- the first few Actions logs will
  show "Theme this run:" and "Hook:" lines for exactly that purpose.

v7.1 (prior) - Catchiness pass: cliche-avoidance + higher temperature, Sep 26 2026
  Areeb's feedback after v7.0 shipped (and gained a few new followers on
  the Hindi content already): "not catchy enough." Two real levers found
  and fixed, both grounded in actual research rather than guessing:
  1. CONTENT_TEMPERATURE: was hardcoded temperature=0.7 at both AI call
     sites (Gemini + the shared OpenRouter/Groq/NVIDIA fallback loop) --
     pulled into one named constant, bumped to 1.0. 0.7 is conservative
     for creative copy (most of these providers default to ~1.0 if left
     unset); the existing validate-and-failover architecture already
     absorbs the small extra risk of a less predictable response at
     higher temperature, so this wasn't new risk, just an unused lever.
  2. build_prompt(): added CLICHE_AVOIDANCE and point_specificity_
     instruction. VERIFIED (Sep 26, via actual web research, not
     assumed): searched what real Hindi "motivational quote" content
     looks like online and found it's dominated by a specific,
     over-saturated register -- rhyming two-line aphorisms and generic
     inspirational vocabulary (मंज़िल/हिम्मत/सफ़र/हौसला) used
     decoratively. That's the likely default an unguided LLM drifts
     toward for "Hindi motivational content," which is very likely why
     v7.0's content read as flat. Also added 2 new hook techniques
     (COMMON-MISTAKE, INSIDER-INFO) adapted from proven viral-hook
     formulas ("nobody tells you this about X", "stop doing X if you
     want Y") found via the same research, and sharpened hook technique
     #4's example, which was closer to the generic-wisdom-quote register
     than the others.
  NOT a structural change -- FIELDS, the 5-segment structure, TTS chain,
  fonts, and video compositing are all untouched from v7.0. This is a
  prompt-engineering + config pass only, which is also why it was
  deliverable as a real targeted diff instead of another sweeping
  rewrite.

v7.0 (prior) - Hindi migration: 5-segment "4 baatein" listicle structure, Sep 26 2026
  WHAT CHANGED (per Areeb's explicit request: move from English psychology
  content to Hindi advice reels, "4 baatein jo jeevan me zarur yaad rakhna"
  format, with a hook that keeps the viewer watching till the last point,
  and variety across multiple life fields instead of one psychology niche):

  1. CONTENT STRUCTURE: replaced the 2-segment hook/reveal structure with a
     5-segment structure -- HOOK + 4 separately-rendered POINT segments,
     hard-cut concatenated in order (hook, point 1, point 2, point 3,
     point 4). Each point gets its OWN background fetch and its OWN TTS
     audio, same "genuinely separate segments" principle v6.7 established
     for hook/reveal, just extended to 5 segments instead of 2. This was
     a deliberate tradeoff Areeb chose explicitly (more cinematic, ~2x
     render time) over a cheaper single-clip "all 4 points read together"
     alternative -- see the ask_user_input exchange this version responds to.
  2. LANGUAGE: all AI-generated viewer-facing text (hook, each point's
     text, caption) is now Hindi in Devanagari script, not English.
     VERIFIED (Sep 26, via direct rendering test in this dev sandbox, not
     assumed): Pillow 12.1.1 + libraqm 0.10.3 correctly shapes Devanagari
     conjuncts/matras/nukta (tested with क्षणिक, ज्ञान, ज़रूर) using the
     free `fonts-noto-core` Ubuntu package -- no tofu boxes, no reordering
     bugs. See FONT_HINDI_* constants below and the new required apt-get
     step in main.yml (setup notes at the bottom of this changelog entry).
  3. NUMBERED PROGRESS BADGE: each point segment now renders a small
     "बात X/4" badge near the top of frame (create_reel_video's new
     point_number/point_total params) -- a persistent on-screen progress
     cue is a deliberate retention mechanic for "hooked till the end,"
     giving the viewer a reason to keep watching for the next number.
  4. TTS CHAIN: Groq TTS (canopylabs/orpheus-v1-english) is REMOVED from
     the chain entirely for this content. VERIFIED (Sep 26, via direct
     research, not assumed): that model only serves English and Arabic --
     it has no Hindi voice at all, so keeping it as a "tier" would just be
     dead code that always falls through. ElevenLabs stays Tier 1 (its
     eleven_multilingual_v2 model already supports Hindi -- confirmed this
     was ALREADY the model_id in use, no change needed there) and Edge-TTS
     stays the bulletproof free fallback, now using Hindi neural voices
     (hi-IN-MadhurNeural) instead of English ones. Areeb explicitly chose
     to keep ElevenLabs as Tier 1 despite its free tier being capped
     (~10 min audio/month) and licensed non-commercial-only -- flagged to
     him plainly before this decision; Edge-TTS Hindi (100% free,
     unlimited, no licensing restriction) is the safety net either way.
  5. FIELDS REPLACES COLUMNS: the old 3-column x 3-subtype grid (9 fixed
     psychology identities) is replaced with FIELDS, a flat list of 5
     Hindi life-advice fields (सेहत/health, रिश्ते/relationships,
     करियर-पैसा/career-money, अनुशासन-मानसिकता/discipline-mindset,
     आध्यात्म/inner peace) -- this is the "variety... multiple fields"
     Areeb asked for. Rotation simplified to match: a flat round-robin
     over 5 fields instead of independent per-column cycles over 9
     subtypes nested in 3 columns. Renamed throughout: COLUMNS->FIELDS,
     get_subtype()->get_field(), pick_next_column_and_advance()->
     pick_next_field_and_advance(), rotation_state.json's shape changes
     from {next_column, column_subtype_index} to {next_field_index} --
     see the one-time migration note in load_rotation_state()'s docstring.
  6. LOOP-TRICK RULE: still 100% removed (confirmed unchanged from v6.6 --
     no new work needed here, just verified the rule still applies to
     every point's text in the new 4-point structure, not just to one
     "reveal" field).
  7. FONT: added FONT_HINDI_SANS_BOLD/REGULAR and FONT_HINDI_SERIF_BOLD/
     REGULAR (Noto Sans/Serif Devanagari, installed via free apt package
     -- see main.yml note below). Devanagari has no italic face in this
     free family (verified via fc-list -- Noto Sans/Serif Devanagari only
     ship Regular+Bold), so the hook's old "always italic" treatment is
     replaced with "always bold sans" for visual punch instead.

  FILES CHANGED:
  - COLUMNS dict:                 replaced entirely with FIELDS (5 Hindi life-fields)
  - get_subtype/total_subtypes_in_column: replaced with get_field()
  - ROTATION_STATE / pick_next_column_and_advance(): simplified to flat 5-field rotation
  - build_prompt():               full rewrite -- Hindi output, hook + 4-point JSON schema, new hook techniques tuned for multi-point retention
  - build_tts_pacing():           REGISTER_TTS_PROFILES re-keyed to the 5 new field voice_registers
  - FONT_SERIF/ITALIC/SANS:       kept (unused by Hindi text now, harmless to leave); added 4 new FONT_HINDI_* constants
  - REQUIRED_CONTENT_KEYS:        hook, points, hook_search_query, caption (reveal/reveal_search_query removed)
  - _validate_content_dict():     Hindi-aware completeness check (Devanagari word regex, Hindi dangling-word list, danda "।" accepted as terminal punctuation) + structural check that points has exactly 4 well-formed entries
  - generate_tts():               Groq TTS tier removed; Edge-TTS fallback now uses hi-IN-MadhurNeural
  - create_reel_video():          Hindi font map; new optional point_number/point_total params draw the "बात X/4" badge
  - concatenate_reel_segments():  signature changed from (hook_path, reveal_path) to (segment_paths: list) -- now handles 5 clips, not 2
  - run():                        rewritten to loop over the 4 points (5 segments total), new Hindi-relevant hashtag map

  ONE-TIME SETUP STEP NEEDED IN main.yml (not in this file -- Areeb adds
  this to his own workflow, see chat reply for the exact line): install
  `fonts-noto-core` via apt-get BEFORE the Python steps run, so the
  Devanagari font files this script points to actually exist on the
  runner. Free (official Ubuntu package), adds a few seconds to the job.

  NOT YET VERIFIED (same honest-limits spirit as v6.2's note below): real
  ElevenLabs Hindi audio quality/voice fit, real Edge-TTS Hindi audio in
  an actual GitHub Actions run, and how the 5-segment reel's total length
  feels in practice -- these can only be confirmed from a real deployed
  run, same as v6.7's equivalent caveat.

v6.7 (prior) - Complete content strategy change: two-segment hook/reveal reels, Aug 13 2026
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
# FIELD ROTATION SYSTEM (v7.0 -- replaces the old 3-column x 3-subtype grid)
# ----------------------------------------------------------------------------
# v6.3-v6.7 organized 9 psychology identities into a 3-column grid (each
# column cycling through its own 3 sub-types independently). That grouping
# existed only to keep 3 *related* psychology voices visually/thematically
# clustered -- it added real complexity (nested dict, per-column index
# tracking) for a benefit that doesn't apply anymore now that each of the
# 5 new Hindi life-fields below is already a fully separate, self-contained
# identity (own colors, own voice, own field of advice). So FIELDS is a
# FLAT list instead of a nested column dict, and rotation is a single flat
# round-robin -- simpler code, same "never repeat the same identity twice
# in a row, cycle predictably" guarantee the old grid gave you.
# ============================================================================

# ---- FIELDS: 5 total identities, one per life field --------------------
# Single source of truth for every field's colors/fonts/voice rules, same
# role COLUMNS played before. Every field produces the SAME content SHAPE
# (hook + 4 standalone points, "4 baatein jo zindagi me zarur yaad
# rakhna" format) -- content_instruction below is what varies: it tells
# the AI which LIFE DOMAIN those 4 points should draw from and in what
# voice, exactly like the old subtypes' content_instruction varied the
# psychology angle. This is the "variety... multiple fields" Areeb asked
# for -- health, relationships, career/money, discipline, inner peace,
# rather than one single psychology niche.
#
# All viewer-facing text (hook + each point + caption) must come back in
# HINDI, Devanagari script -- see build_prompt() below for exactly how
# that's enforced in the AI prompt.
#
# v7.2: TWO-LEVEL CONTENT MODEL. A FIELD (below) is still the broad,
# rotating category -- it decides the visual identity (colors/fonts) and
# the voice register, exactly as before. What changed is that the AI now
# first picks ONE specific THEME inside the field each run (e.g. within
# "rishtey": "जब कोई आपकी इज़्ज़त न करे तो क्या करें") and builds the whole
# reel around that theme, instead of writing "4 things about
# relationships." Two keys support that:
#   - content_instruction now describes only the field's DOMAIN and VOICE
#     (it used to say "the 4 points must each be ONE tip", which
#     contradicted the new situation->reframe->action->takeaway arc that
#     build_prompt() asks for).
#   - example_themes: 3 sample themes showing the right level of
#     specificity. build_prompt() shows 2 random ones per run as
#     calibration ONLY and tells the model not to reuse them.
FIELDS = [
    {
        "key": "sehat", "label": "Sehat (Health)",
        "bg_color": "#0A2E1F", "text_color": "#F2F5F0", "accent_color": "#7DDB9E",
        "font_style": "sans_bold", "voice_register": "sehat", "overlay_opacity": 0.68,
        "visual_mood_instruction": (
            "a short 2-4 word visual search query for health, movement, or "
            "calm-vitality imagery (e.g. 'morning run sunrise', 'fresh fruit "
            "bowl light', 'person stretching outdoors')"
        ),
        "content_instruction": (
            "FIELD: physical health and daily body discipline -- sleep, "
            "movement, food, energy, posture, hydration. VOICE: direct and "
            "practical, like a grounded friend who genuinely takes care of "
            "himself -- NOT clinical/medical-sounding, NOT preachy. Advice "
            "should be something a viewer could act on TODAY. Stay with "
            "everyday habits -- NEVER make medical claims, diagnose "
            "anything, or promise that something cures or prevents a "
            "disease."
        ),
        "example_themes": [
            "थकान हमेशा काम की वजह से नहीं होती",
            "सुबह उठते ही फ़ोन देखने की आदत कैसे छोड़ें",
            "देर रात तक जागने की आदत कैसे तोड़ें",
        ],
    },
    {
        "key": "rishtey", "label": "Rishtey (Relationships)",
        "bg_color": "#3D1420", "text_color": "#F5EDE8", "accent_color": "#E8B4A8",
        "font_style": "serif_regular", "voice_register": "rishtey", "overlay_opacity": 0.60,
        "visual_mood_instruction": (
            "a short 2-4 word visual search query for warm human-connection "
            "imagery (e.g. 'two people talking warmly', 'hands holding "
            "warm light', 'friends walking together')"
        ),
        "content_instruction": (
            "FIELD: relationships -- boundaries, communication, "
            "self-respect inside a relationship, choosing the right "
            "people, not over-giving. VOICE: warm but not soft or weak -- "
            "grounded relationship wisdom, the kind that sounds obvious "
            "only AFTER someone says it out loud."
        ),
        "example_themes": [
            "जब कोई आपकी इज़्ज़त न करे तो क्या करें",
            "हर किसी को खुश करने की कोशिश क्यों छोड़नी चाहिए",
            "रिश्ते में हर बात पर सफ़ाई देना कब बंद करें",
        ],
    },
    {
        "key": "career_paisa", "label": "Career-Paisa (Career & Money)",
        "bg_color": "#0B1A3D", "text_color": "#FFFFFF", "accent_color": "#4A9EFF",
        "font_style": "sans_bold", "voice_register": "career_paisa", "overlay_opacity": 0.68,
        "visual_mood_instruction": (
            "a short 2-4 word visual search query for purposeful work/"
            "growth imagery (e.g. 'person working focused desk', 'city "
            "skyline morning', 'hands writing notes')"
        ),
        "content_instruction": (
            "FIELD: career and everyday money habits -- saving before "
            "spending, patience with compounding, building a real skill "
            "vs chasing shortcuts, not comparing your timeline to "
            "others. VOICE: practical and no-nonsense, like advice from "
            "someone who actually built something, not generic 'hustle "
            "harder' motivational fluff. Stay with habits and decisions -- "
            "NEVER recommend specific stocks, funds or investments, and "
            "NEVER promise returns or guaranteed results."
        ),
        "example_themes": [
            "कमाई बढ़ने के बाद भी पैसा क्यों नहीं बचता",
            "कम सैलरी में पैसे बचाने की शुरुआत कैसे करें",
            "पहली सैलरी आने पर पैसे का क्या करें",
        ],
    },
    {
        "key": "anushasan", "label": "Anushasan (Discipline & Mindset)",
        "bg_color": "#0A0A0A", "text_color": "#FFFFFF", "accent_color": "#E0C080",
        "font_style": "sans_bold", "voice_register": "anushasan", "overlay_opacity": 0.72,
        "visual_mood_instruction": (
            "a short 2-4 word visual search query for stark, minimal, "
            "disciplined imagery (e.g. 'empty modern architecture', "
            "'single silhouette dark room', 'clean minimal hallway')"
        ),
        "content_instruction": (
            "FIELD: self-discipline and mindset -- consistency over "
            "motivation, owning your reactions, cutting distraction, doing "
            "the hard thing first. VOICE: blunt, direct, drill-sergeant-"
            "adjacent -- short, forceful sentences, command verbs, zero "
            "softening."
        ),
        "example_themes": [
            "जब काम करने का मन बिल्कुल न हो तब क्या करें",
            "हर बार बहाना बनाने की आदत कैसे छोड़ें",
            "काम कल पर टालने की आदत क्यों नहीं छूटती",
        ],
    },
    {
        "key": "adhyatm", "label": "Adhyatm (Inner Peace)",
        "bg_color": "#F2EEE6", "text_color": "#1A1A1A", "accent_color": "#8A8578",
        "font_style": "serif_regular", "voice_register": "adhyatm", "overlay_opacity": 0.50,
        "visual_mood_instruction": (
            "a short 2-4 word visual search query for calm, quiet imagery "
            "(e.g. 'empty park bench morning', 'still water soft light', "
            "'quiet room window light')"
        ),
        "content_instruction": (
            "FIELD: inner peace -- acceptance, gratitude, letting go, "
            "presence, not needing external validation. VOICE: quiet and "
            "reflective, universal and inclusive, NOT tied to any one "
            "religion or dogma -- the kind of line someone would want to "
            "sit with rather than act on immediately."
        ),
        "example_themes": [
            "हर बात का जवाब देना ज़रूरी नहीं होता",
            "जो बीत गया उसे बार-बार सोचना क्यों छोड़ना चाहिए",
            "दूसरों की राय से फ़र्क़ पड़ना कैसे कम करें",
        ],
    },
]


def get_field(field_index: int) -> dict:
    """Looks up one field by its position in the flat rotation. The ONLY
    function that should read FIELDS directly, so every caller stays in
    sync if the definitions above ever change (same role get_subtype()
    played for COLUMNS before)."""
    return FIELDS[field_index % len(FIELDS)]


# ---- ROTATION TRACKER: which field posts next, persisted -----------------
# Same persistence model as before: GitHub Actions gives a fresh container
# every run, so rotation_state.json needs the existing main.yml step that
# commits it back after each run -- unchanged, no new workflow step needed
# for this specific file (only the new font-install step is new, see the
# v7.0 changelog entry's setup note and the chat reply for the exact line).
ROTATION_STATE_PATH = "rotation_state.json"

# SHAPE CHANGE from v6.7: {"next_column": int, "column_subtype_index":
# {...}} is replaced with just {"next_field_index": int} -- the flat list
# only needs one position, not a per-column index map. If an OLD-shape
# rotation_state.json from before this version is still in the repo,
# load_rotation_state() below won't find "next_field_index" in it and will
# safely start fresh at field 0 -- there's no meaningful way to map an old
# 3-column position onto the new 5-field list anyway, so a clean restart
# is the correct behavior here, not a bug to work around.
DEFAULT_ROTATION_STATE = {
    "next_field_index": 0,
    "last_updated": None,
    "history": [],
}


def load_rotation_state(path: str = ROTATION_STATE_PATH) -> dict:
    """Reads rotation_state.json. Missing/corrupt file -- OR an old v6.7-
    shape file that has no "next_field_index" key -- both safely fall back
    to a fresh start at field 0, not a crash. See the SHAPE CHANGE note on
    DEFAULT_ROTATION_STATE above for why an old-shape file isn't migrated."""
    if not os.path.exists(path):
        print(f"ℹ️ No {path} found -- starting fresh rotation at field 0.")
        return dict(DEFAULT_ROTATION_STATE)
    try:
        with open(path, "r", encoding="utf-8") as f:
            state = json.load(f)
        if "next_field_index" not in state:
            print(f"ℹ️ {path} is from an older version (different rotation shape) -- starting fresh at field 0.")
            return dict(DEFAULT_ROTATION_STATE)
        merged = dict(DEFAULT_ROTATION_STATE)
        merged.update(state)
        return merged
    except (json.JSONDecodeError, OSError) as e:
        print(f"⚠️ {path} exists but couldn't be read ({e}). Falling back to fresh rotation state.")
        return dict(DEFAULT_ROTATION_STATE)


def save_rotation_state(state: dict, path: str = ROTATION_STATE_PATH) -> None:
    """Writes rotation_state.json. Unchanged logic from v6.7 -- this alone
    does NOT persist across runs, the existing main.yml commit+push step
    handles that, exactly as before."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def pick_next_field_and_advance(state: dict) -> tuple:
    """Core rotation logic, called once per run. Returns (field_index,
    field_dict) for THIS run, and mutates `state` in place to reflect what
    comes NEXT run. Flat round-robin over all 5 fields: 0->1->2->3->4->0...
    Simpler than v6.7's per-column independent cycling since there's only
    one list to advance through now, not 3 nested ones."""
    field_index = state["next_field_index"] % len(FIELDS)
    field = get_field(field_index)

    state["next_field_index"] = (field_index + 1) % len(FIELDS)
    state["last_updated"] = datetime.now().isoformat()
    state["history"].append({"field": field["key"], "at": state["last_updated"]})
    state["history"] = state["history"][-12:]  # keep last 12 only, for debugging visibility

    return field_index, field


def get_recent_topics(state: dict, limit: int = 8) -> list:
    """v7.2 NEW: returns up to `limit` themes ("topic" values) that were
    already posted, oldest first, read from rotation_state.json's history.
    build_prompt() shows them to the model so a theme-first design doesn't
    quietly repeat the same few "best" themes -- without this, an LLM asked
    to invent one specific theme per run tends to converge on the same
    handful for a given field.

    Safe by construction, no migration needed:
    - History entries written before v7.2 have no "topic" key -> skipped.
    - THIS run's own entry (already appended by pick_next_field_and_advance
      but with no topic yet, since it's recorded only AFTER a successful
      publish -- see run()) -> skipped the same way.
    - pick_next_field_and_advance() already keeps only the last 12 history
      entries, so this can never grow the state file unboundedly."""
    topics = [h.get("topic") for h in state.get("history", []) if h.get("topic")]
    return topics[-limit:]

# ---- CONTENT PROMPT BUILDER: different AI prompt per sub-type ------------
def build_prompt(subtype: dict, recent_topics: list = None) -> str:
    """Builds the AI content-generation prompt for whichever field is
    active this run. NOTE ON THE PARAMETER NAME: this still says
    `subtype` even though FIELDS replaced COLUMNS/subtypes in v7.0 --
    kept deliberately unchanged (rather than renamed to `field`
    everywhere) so this diff stays about the actual content/schema
    change, not a cosmetic rename rippling through every function
    signature. It's still the same dict shape as before (key, label,
    content_instruction, visual_mood_instruction, voice_register, etc),
    just sourced from FIELDS now instead of COLUMNS.

    v7.0 CONTENT STRATEGY CHANGE (Hindi migration, per Areeb's explicit
    request): replaces the two-beat HOOK -> REVEAL structure with a
    FIVE-beat HOOK -> POINT 1 -> POINT 2 -> POINT 3 -> POINT 4 structure
    -- the "4 baatein jo zindagi me zarur yaad rakhna" (4 things to
    always remember in life) listicle format. subtype['content_instruction']
    still defines the field's voice/substance, same role as before -- it
    now describes what KIND of 4 standalone points that field should
    produce, in Hindi. The hook's job changed too: instead of teasing
    ONE reveal, it must tease that there are specifically 4 things
    coming and give the viewer a reason to stay for all 4 (see
    HOOK_TECHNIQUES below, redesigned for multi-point retention, not
    single-reveal curiosity).

    ALL VIEWER-FACING TEXT MUST BE HINDI (Devanagari script) -- this is
    new in v7.0 and enforced repeatedly below, not just mentioned once,
    since getting this wrong (e.g. the model defaulting to English, or
    to Hinglish typed in Latin letters) would silently break the whole
    point of this migration.

    v6.5-6.6 (still true, unchanged): the mid-thought-loop trick is still
    REMOVED for every field. EVERY point (not just one "reveal" field
    now) must end on a complete, properly punctuated sentence -- more
    important than ever now, since a listicle with a truncated point 3
    is a worse failure than a truncated single reveal ever was.

    v7.1 CATCHINESS PASS (per Areeb's feedback after v7.0 shipped: "not
    catchy enough"): added CLICHE_AVOIDANCE and point_specificity_instruction
    below, and 2 new hook techniques. This was grounded in actual research
    (Sep 26), not just assumption -- searched what real Hindi "motivational
    quote" content looks like and found it's dominated by a specific,
    over-saturated register: rhyming two-line aphorisms ("मन के हारे हार
    है, मन के जीते जीत" is a genuinely common example that turned up) and
    generic inspirational vocabulary (मंज़िल/हिम्मत/सफ़र/हौसला) strung
    together decoratively rather than saying anything specific. That's
    the default an unguided LLM tends toward for "Hindi motivational
    content" -- it's the same register as a million quote-graphic
    accounts, which is very likely WHY the original content read as flat
    rather than catchy. Also searched proven viral-hook formulas
    ("Nobody tells you this about X", "Stop doing X if you want Y") and
    adapted 2 of them below as new hook techniques -- these are
    well-tested patterns, not invented from scratch.

    v7.2 THEME-FIRST + ARC PASS (per outside content-strategy feedback
    Areeb brought in after v7.1 -- evaluated critically, not adopted
    wholesale; see the v7.2 changelog entry for what was and wasn't
    taken). Adopted here:
    - THEME-FIRST: the model must first pick ONE specific theme inside
      the field ("topic", the first key in the JSON) and build the hook,
      all 4 points and the caption around it. A field alone
      ("relationships") invites "4 generic tips about relationships"; a
      theme ("what to do when someone doesn't respect you") gives it
      something concrete to say. `recent_topics` (new optional
      parameter, fed from rotation_state.json's history by run()) lists
      themes already posted so the model doesn't repeat them -- without
      that, a theme-first design tends to converge on the same few
      "best" themes per field.
    - ARC: the 4 points now have jobs (situation -> reframe -> action ->
      takeaway) instead of being 4 interchangeable tips. The JSON shape
      is still points[4] of {text, search_query} -- the arc lives in the
      prompt, so validation, rendering and the "बात X/4" badge are all
      untouched.
    - LESS CLICKBAIT: hook techniques rewritten around relevance +
      curiosity + specificity; "ज़िंदगी बदल देंगी" / "आखिरी वाली सबसे
      ज़रूरी है" style promises are gone, and the prompt now says so
      explicitly. Hook/CTA examples are now written in Devanagari --
      through v7.1 they were Roman Hindi while the prompt demanded
      Devanagari, a mixed signal that could nudge the model toward
      Hinglish output.
    - SPECIFICITY RULES: each point needs at least one concrete element
      (behavior, decision, boundary, observation, mistake, example or
      situation), and six stock phrases are banned unless the sentence
      says exactly how or when. Also swapped v7.1's walking example,
      which claimed an effect "more than any supplement" -- an
      unverifiable health claim the model could have copied."""
    import random

    # v7.2: HOOK_TECHNIQUES rewritten. Through v7.1 several techniques
    # leaned on exaggerated promises ("ज़िंदगी बदल देंगी", "आखिरी वाली सबसे
    # ज़रूरी है") -- believable-sounding hooks that earn attention from
    # RELEVANCE (a situation the viewer is actually in) and CURIOSITY (a
    # gap they want closed) hold up better than hype, and they no longer
    # need "4 things are coming" to be part of the hook at all (the on-
    # screen "बात X/4" badge already tells the viewer the count).
    # Every example below is in Devanagari on purpose -- v7.0/v7.1 used
    # Roman Hindi examples while demanding Devanagari output, a mixed
    # signal. Picked randomly per generation call, independent of field.
    HOOK_TECHNIQUES = [
        (
            "a SPECIFIC-HABIT hook -- point at ONE specific, everyday "
            "habit or behavior connected to the theme and hint it may be "
            "quietly causing a problem, so the viewer stays to check "
            "themselves. e.g. 'आपकी ये एक आदत रिश्ते खराब कर सकती है।'"
        ),
        (
            "a QUESTION-AND-REFRAME hook -- open with the viewer's real, "
            "specific frustration as a short question, then hint the "
            "cause is not what they assume. e.g. 'पैसे बचाने में दिक्कत "
            "है? शायद समस्या कमाई नहीं है।'"
        ),
        (
            "an IF-YOU hook -- start from a situation the viewer is "
            "probably in right now ('अगर आप...') and tell them these "
            "points are for them. e.g. 'अगर आप हमेशा थके रहते हैं, ये 4 "
            "बातें देखिए।'"
        ),
        (
            "a CALM-TRUISM hook -- a quiet, believable statement that "
            "makes the viewer nod, with no hype and no promise. e.g. "
            "'हर बात का जवाब देना ज़रूरी नहीं होता।'"
        ),
        (
            "a REALIZATION hook -- frame the theme as something people "
            "usually understand only late. e.g. 'एक उम्र के बाद ये बात "
            "समझ आ ही जाती है।' or 'काश ये बात मुझे पहले पता होती।'"
        ),
        (
            "a COMMON-MISTAKE hook -- name a specific mistake most people "
            "make around the theme without realizing it. e.g. "
            "'ज़्यादातर लोग पैसे बचाने की शुरुआत ही गलत जगह से करते हैं।'"
        ),
        (
            "an UNSPOKEN-TRUTH hook -- use ONLY if the theme really is "
            "something people rarely say out loud (never force it). "
            "e.g. 'रिश्तों के बारे में ये बात कोई खुलकर नहीं बोलता।'"
        ),
    ]
    hook_technique = random.choice(HOOK_TECHNIQUES)

    # v7.2 NEW: says out loud what the v7.2 hook techniques above already
    # do by example, so the model has both the pattern AND the rule.
    hook_believability_instruction = (
        "- The hook must sound like a believable person, not a promo: NO "
        "promises that life will change, NO claims that one point is 'the "
        "most important', NO 'you won't believe this' style hype. Earn "
        "the viewer's attention with RELEVANCE (a situation they are "
        "actually in) and CURIOSITY (a gap they want closed), not "
        "exaggeration. It is fine, but not required, to mention that 4 "
        "points are coming."
    )

    # v7.1 (kept, wording tweaked in v7.2 from "THIS field" to "THIS
    # theme"): explicitly names and steers away from the generic "quote-
    # card" register that research (Sep 26) confirmed dominates Hindi
    # motivational content, with a concrete test the model can apply.
    CLICHE_AVOIDANCE = (
        "- AVOID the generic 'WhatsApp-forward quote card' register that "
        "floods Hindi motivational content online -- rhyming two-line "
        "aphorisms, and generic inspirational words (मंज़िल, हिम्मत, "
        "सफ़र, हौसला, गुलज़ार) strung together decoratively without "
        "saying anything specific. This is the most common failure mode "
        "for AI-generated Hindi content -- it ends up sounding like a "
        "quote graphic, not a real person talking to camera. Test: if a "
        "line could be pasted onto a random sunset photo and still make "
        "sense with zero context, it's too generic -- rewrite it "
        "specific to THIS theme and THIS point."
    )

    # v7.2 NEW: gives each of the 4 points a job, merging two separate
    # suggestions from the outside feedback (problem->realization->action
    # ->takeaway, and relatable->challenge->practical->memorable) into ONE
    # arc so the model isn't asked to juggle two overlapping structures.
    # This is text only -- the JSON is still points[4] of {text,
    # search_query}, so nothing downstream had to change.
    point_arc_instruction = (
        "The 4 points are NOT 4 interchangeable tips -- together they are "
        "one short argument that builds, and each point has its own job:\n"
        "  POINT 1 = THE SITUATION: something instantly relatable -- a "
        "specific moment, feeling or mistake the viewer recognizes from "
        "their own life.\n"
        "  POINT 2 = THE REFRAME: challenge a common assumption about "
        "that situation -- the 'I never looked at it that way' beat.\n"
        "  POINT 3 = THE ACTION: one concrete thing the viewer can do or "
        "try -- a specific behavior, decision or way of responding (for "
        "quiet, reflective fields this can be a small mental habit or a "
        "way of responding, not a big task).\n"
        "  POINT 4 = THE TAKEAWAY: one short, memorable line that sums the "
        "whole reel up -- the line a viewer would screenshot or send to a "
        "friend. It is the one place a short quotable line is welcome, "
        "but it must still be specific to THIS theme (see the cliche "
        "rule below) and feel like the natural conclusion of points 1-3.\n"
        "Each point must still be a complete, clear thought that makes "
        "sense on its own screen (no 'as I said above'), even though the "
        "four build on each other."
    )

    # v7.1 rule, extended in v7.2: (a) a taxonomy of what counts as
    # "concrete", (b) a second contrast pair showing the "how/when"
    # requirement, (c) six stock phrases banned unless qualified. Also
    # replaced v7.1's walking example, which claimed an effect "more than
    # any supplement" -- an unverifiable health claim the model could have
    # copied into real posts.
    point_specificity_instruction = (
        "- Every point must contain at least ONE of these concrete "
        "elements: a specific behavior, a decision, a boundary, an "
        "observation, a common mistake, an example, or a real situation "
        "-- not just a restated principle. Compare: 'रोज़ टहलना ज़रूरी है' "
        "(generic, forgettable, could be any health post ever) vs 'खाने के "
        "बाद 10 मिनट टहलने की आदत बना लो; इससे भारीपन कम लगता है।' "
        "(specific -- a number, a concrete moment, a modest effect). And: "
        "'खुद को प्राथमिकता देना सीखो।' (generic) vs 'हर काम के लिए तुरंत "
        "हाँ मत कहो; पहले देखो कि उसके लिए आपके पास समय और ऊर्जा है या "
        "नहीं।' (specific -- says exactly what to do and when).\n"
        "- These stock phrases are BANNED unless the same sentence "
        "explains exactly HOW or WHEN: 'खुद पर विश्वास रखो', 'मेहनत करते "
        "रहो', 'समय सब सिखा देता है', 'नकारात्मक लोगों से दूर रहो', 'अपने "
        "सपनों का पीछा करो', 'खुद को प्राथमिकता दो'."
    )

    point_ending_instruction = (
        "- CRITICAL: EVERY point's text (all 4) MUST end with a "
        "COMPLETE, properly punctuated sentence -- a full stop (. or "
        "the Hindi danda ।), not a trailing clause. Do NOT end "
        "mid-thought, do NOT trail off with a dangling connector like "
        "'क्योंकि...', 'जो...', 'अगर...' or similar. Each point is its "
        "own complete thought, not a fragment of a longer one."
    )

    # v7.3 NEW: pairs with the repetition guard now in
    # _validate_content_dict() -- that guard is the safety net; this is
    # the prompt-level ask that should make it rarely need to fire.
    no_repetition_instruction = (
        "- Do NOT repeat the same word or phrase (4 or more words in a "
        "row) anywhere in the hook, a point, or the caption, and do NOT "
        "let two different points end up saying nearly the same thing. "
        "Each of the 5 pieces of text must be genuinely distinct."
    )

    hindi_language_instruction = (
        "- ALL viewer-facing text -- hook, every point's text, and the "
        "caption -- MUST be written ENTIRELY in HINDI using DEVANAGARI "
        "SCRIPT (e.g. जीवन, not 'jeevan'). Do NOT write Hindi in Roman/"
        "Latin transliteration. Use natural, conversational spoken Hindi "
        "(the way a relatable Instagram creator actually talks), NOT "
        "stiff, overly Sanskritized, textbook/news-anchor Hindi. Common "
        "everyday English loanwords are fine if that's how people "
        "actually say it (e.g. फोकस, टाइम), but the sentence structure "
        "and grammar must be genuinely Hindi."
    )

    # ---- STEP 1 support (v7.2): calibration examples + repeat-blocklist ----
    # Show only 2 of the field's 3 example themes, chosen at random each
    # run: models tend to copy whatever examples they're shown, so
    # rotating which ones appear (plus telling the model not to reuse
    # them) reduces the chance every run gravitates to the same theme.
    example_pool = subtype.get("example_themes", [])
    shown_examples = random.sample(example_pool, min(2, len(example_pool)))
    if shown_examples:
        example_lines = "\n".join(f"    - {t}" for t in shown_examples)
        examples_block = (
            "These examples show the right level of specificity for this "
            "field (for calibration ONLY -- do NOT reuse them, invent a "
            "different theme):\n" + example_lines + "\n"
        )
    else:
        examples_block = ""  # a field without example_themes still works, just uncalibrated

    # recent_topics comes from rotation_state.json's history via run() --
    # themes already posted, so a theme-first design doesn't quietly
    # repeat itself. Empty/None (first run after upgrading, or history
    # without topics yet) just means no blocklist is shown.
    recent_block = ""
    if recent_topics:
        recent_lines = "\n".join(f"    - {t}" for t in recent_topics)
        recent_block = (
            "These themes were ALREADY posted recently -- do NOT pick the "
            "same theme or a close variation of any of them:\n"
            + recent_lines + "\n"
        )

    return f"""Act as a grounded, relatable life-advice creator writing for a Hindi-language Instagram account.

CONTENT FIELD FOR THIS POST: "{subtype['label']}" ({subtype['voice_register']} register)

{subtype['content_instruction']}

STEP 1 -- CHOOSE ONE SPECIFIC THEME (do this before writing anything else):
Do NOT write about the broad field. Pick ONE concrete situation, problem
or question INSIDE it -- something the viewer could name in a single
sentence, not just the field's name. Every part of the reel -- hook, all
4 points and caption -- must be about this ONE theme.
{examples_block}{recent_block}
STEP 2 -- BUILD THE REEL AROUND THAT THEME:

This reel is FIVE SEPARATE SEGMENTS spliced into one video -- NOT one
continuous scene. Each segment has its OWN background image and its OWN
narration audio. Only ONE segment's text is ever on screen at a time --
hard cuts between them, no overlap:
  SEGMENT 1 = HOOK
  SEGMENT 2 = POINT 1
  SEGMENT 3 = POINT 2
  SEGMENT 4 = POINT 3
  SEGMENT 5 = POINT 4

SEGMENT 1 -- HOOK: introduces the theme so the viewer wants to hear the
rest, WITHOUT giving away what the points say. Use {hook_technique}

SEGMENTS 2-5 -- THE 4 POINTS ("4 बातें जो ज़िंदगी में ज़रूर याद रखना"):
{point_arc_instruction}

IMPORTANT VOICE RULES:
- The hook and all 4 points must feel like ONE continuous idea about the
  one theme, not 5 disconnected posts -- the hook sets up exactly what
  the points deliver.
- Stay STRICTLY within the voice register described above for all 4
  points. Do not blend in a different field's tone -- the whole point
  is that this voice register is DISTINCT from other fields on this
  account.
{hook_believability_instruction}
{CLICHE_AVOIDANCE}
{point_specificity_instruction}
{point_ending_instruction}
{no_repetition_instruction}
{hindi_language_instruction}
- Pacing: the hook should read aloud in under 4 seconds (roughly 8-12
  Hindi words). Each point should read aloud in 4-7 seconds (roughly
  12-20 Hindi words) -- long enough to be a genuinely complete thought,
  short enough to keep the reel moving. Total reel length (hook + 4
  points spoken back to back) should land naturally around 28-45
  seconds, which is a normal, expected length for this listicle format
  on Instagram Reels.
- The caption is NOT a generic follow-CTA. It must be a genuine
  QUESTION in Hindi directed at the viewer that prompts them to
  comment -- something they can answer about their own life, directly
  related to the theme. MUST end with an explicit Hindi comment CTA
  (e.g. "अपना जवाब कमेंट में ज़रूर बताइए।").

Return STRICTLY valid JSON, no markdown fences, no preamble. Write the
keys in exactly this order ("topic" FIRST -- commit to the theme before
writing anything else). "points" MUST contain EXACTLY 4 objects, in
order (point 1 first, point 4 last):
{{
  "topic": "The ONE specific theme you chose in STEP 1, as a short Hindi phrase (5-10 words) -- write this FIRST; everything below must be about it",
  "hook": "The Hindi hook line about that theme, using the technique specified above (under 12 words)",
  "points": [
    {{"text": "POINT 1 (the situation): complete Hindi text, in the voice register specified above", "search_query": "{subtype['visual_mood_instruction']}"}},
    {{"text": "POINT 2 (the reframe): complete Hindi text, same voice register", "search_query": "{subtype['visual_mood_instruction']}"}},
    {{"text": "POINT 3 (the action): complete Hindi text, same voice register", "search_query": "{subtype['visual_mood_instruction']}"}},
    {{"text": "POINT 4 (the takeaway): complete Hindi text, same voice register", "search_query": "{subtype['visual_mood_instruction']}"}}
  ],
  "hook_search_query": "a short 2-4 word visual search query for SEGMENT 1's background -- should match the mood of the hook and theme, without depicting any of the 4 points' answers",
  "caption": "A genuine, specific Hindi question tied to the theme, that the viewer can only answer by commenting their own experience -- MUST end with an explicit Hindi comment CTA."
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

    v7.0: re-keyed from the 9 psychology voice_registers to the 5 Hindi
    FIELDS voice_registers (sehat/rishtey/career_paisa/anushasan/adhyatm)
    -- the rate/pitch/volume MECHANISM above is completely unchanged
    (still the same 3 real Communicate() knobs, same comma-pause trick),
    only the per-register VALUES are new, chosen per field's character:
    - sehat (health): brisk, encouraging -- faster rate, neutral pitch,
      slightly louder, like a friend pushing you to move.
    - rishtey (relationships): warm and sincere -- slightly slower rate,
      slightly lowered pitch, normal volume -- reads as heartfelt, not
      rushed.
    - career_paisa (career/money): brisk and practical -- faster rate,
      neutral pitch, louder -- reads as no-nonsense and direct.
    - anushasan (discipline/mindset): forceful, drill-sergeant energy --
      faster rate, RAISED pitch, louder -- reads as blunt and urgent,
      same energy the old "Command"/"Warn" registers had.
    - adhyatm (inner peace): slow and weighty -- slower rate, LOWERED
      pitch, slightly quieter -- reads as reflective and calm, matching
      a closing/meditative thought.
    """
    paced_text = full_text.replace("...", ",")
    register = subtype.get("voice_register", "")

    # (rate, pitch, volume) per register -- all values pre-validated
    # against edge-tts's exact regex (whole numbers, correct sign, correct
    # unit per parameter). These knobs are NOT Hindi-specific -- Azure's
    # neural voices accept rate/pitch/volume identically regardless of
    # which locale voice is selected, so no new verification was needed
    # for this part when moving to hi-IN-MadhurNeural below.
    REGISTER_TTS_PROFILES = {
        "sehat":         ("+5%",  "+0Hz",  "+6%"),   # brisk, encouraging
        "rishtey":       ("-4%",  "-4Hz",  "+0%"),   # warm, sincere
        "career_paisa":  ("+5%",  "+0Hz",  "+8%"),   # brisk, practical
        "anushasan":     ("+7%",  "+10Hz", "+10%"),  # forceful, blunt
        "adhyatm":       ("-10%", "-12Hz", "-5%"),   # slow, weighty, calm
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

# v7.1 NEW: was hardcoded as temperature=0.7 separately at both AI call
# sites in generate_content() below (easy to update one and forget the
# other) -- pulled into one named constant instead, used by all 4
# providers (Gemini + the 3 OpenAI-compatible fallbacks).
#
# v7.3 REVISED DOWN, 1.0 -> 0.85. v7.1 bumped this to 1.0 for catchier
# phrasing; Areeb then reported TTS audio "repeating" in production. That
# call was likely a mistake on my part: higher sampling temperature is a
# well-documented cause of degenerate repetition loops in LLM generation,
# and none of the 4 providers here have a repetition/frequency penalty
# set to counteract it -- I raised the one knob that increases repetition
# risk without adding the knob that guards against it. 0.85 is a
# deliberate middle ground: still above the original conservative 0.7
# (keeping most of the lexical-variety benefit v7.1 was going for), but
# pulled back from 1.0. This is a judgment call, not a certainty -- paired
# with a real safety net regardless of the exact right number:
# _validate_content_dict() (v7.3) now explicitly detects a repeated
# word-run within a single response and rejects it, falling through to
# the next AI tier the same way any other malformed response already
# does, so a bad roll at whatever temperature is caught rather than
# reaching TTS.
CONTENT_TEMPERATURE = 0.85

def validate_environment():
    missing = [name for name in REQUIRED_ENV_VARS if not os.environ.get(name)]
    if missing:
        print(f"❌ FATAL: Missing required secret(s): {', '.join(missing)}")
        sys.exit(1)
    if not any([GEMINI_API_KEY, OPENROUTER_API_KEY, GROQ_API_KEY, NVIDIA_API_KEY]):
        print("❌ FATAL: At least one AI API key must be provided!")
        sys.exit(1)

    # v7.3 NEW PRE-FLIGHT CHECK: Devanagari text needs TWO separate things
    # to render correctly, and each fails a DIFFERENT way if missing:
    #   1. The actual Devanagari font FILES (fonts-noto-core). If these are
    #      genuinely missing, ImageFont.truetype() raises inside
    #      create_reel_video()'s own try/except, which already fails the
    #      run loudly (see that function's final "except Exception as e:
    #      print(...); return None") -- so this is checked here mainly to
    #      fail in under a second instead of after content generation +
    #      TTS have already run.
    #   2. Pillow built WITH libraqm (complex text shaping -- conjuncts
    #      like क्ष/ज्ञ, matra reordering). THIS is the dangerous one:
    #      if raqm is missing, the font file still loads fine and
    #      ImageFont.truetype() does NOT raise -- rendering just silently
    #      falls back to naive glyph-by-glyph layout, which can produce
    #      "boxes instead of letters" for character SEQUENCES the font can
    #      only produce via ligature substitution, with NO exception, NO
    #      error, and NO way for create_reel_video()'s try/except to catch
    #      it -- so without this explicit check it fails completely
    #      silently, exactly the failure Areeb hit in production.
    #   VERIFIED (Sep 26, in the dev sandbox this was built in): Pillow's
    #   official PyPI wheels bundle libraqm directly into _imagingft's
    #   binary (confirmed via `strings` on that .so -- HAVE_RAQM,
    #   raqm_create() etc. are compiled in, no separate system package
    #   needed) -- but this depends on the ACTUAL Pillow build in use,
    #   which this script cannot control from inside itself, hence a
    #   runtime check rather than just trusting it.
    #   Placed BEFORE the Instagram network check below on purpose: this
    #   is a fast, fully local, deterministic check -- no reason to wait
    #   on a network round-trip before catching a local misconfiguration.
    from PIL import features as _pil_features
    if not _pil_features.check("raqm"):
        print("❌ FATAL: Pillow was loaded WITHOUT libraqm (complex text shaping) support.")
        print("   -> Hindi text will render with WRONG/MISSING glyphs (boxes) with no other error shown.")
        print("   -> Fix: pip install --upgrade --force-reinstall Pillow (the official wheel bundles raqm).")
        sys.exit(1)
    _missing_fonts = [p for p in (
        "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Regular.ttf",
    ) if not os.path.exists(p)]
    if _missing_fonts:
        print(f"❌ FATAL: Devanagari font file(s) not found: {', '.join(_missing_fonts)}")
        print("   -> Fix: add this step to main.yml BEFORE the Python steps run:")
        print("      sudo apt-get update && sudo apt-get install -y fonts-noto-core")
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
# v7.0: kept the 3 DejaVu (Latin) constants above even though Hindi text no
# longer uses them -- harmless to leave, and removing them would be a
# no-benefit diff. All actual on-screen text now uses the 4 Devanagari
# fonts below instead (see create_reel_video()'s reel_font_map).
#
# REQUIRES a new one-line step in main.yml BEFORE the Python steps run:
#   sudo apt-get update && sudo apt-get install -y fonts-noto-core
# (free official Ubuntu package -- exact line + where to put it is in the
# chat reply, not repeated here since this .py file can't edit main.yml
# itself). Without that step these paths won't exist on the runner and
# every video render will fail at the ImageFont.truetype() call below.
#
# VERIFIED (Sep 26, in this dev sandbox, not assumed): installed
# fonts-noto-core fresh via apt, confirmed these 4 exact file paths via
# `dpkg -L fonts-noto-core`, then rendered Devanagari conjuncts/matras/
# nukta with Pillow + libraqm and visually confirmed correct shaping
# (जीवन, क्षणिक, ज्ञान, ज़रूर all rendered correctly, not tofu boxes).
FONT_HINDI_SANS_BOLD     = "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf"
FONT_HINDI_SANS_REGULAR  = "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf"
FONT_HINDI_SERIF_BOLD    = "/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Bold.ttf"
FONT_HINDI_SERIF_REGULAR = "/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Regular.ttf"
# NOTE: this free Noto family has NO italic/oblique Devanagari face
# (confirmed via `fc-list | grep -i devanagari` -- only Regular+Bold
# exist for both Sans and Serif). create_reel_video()'s hook segment
# used to always render in FONT_ITALIC; it now always renders in
# FONT_HINDI_SANS_BOLD instead (bold-for-punch rather than italic-for-
# distinction) since there's no italic face to reach for.

# ============================================================
# MULTI-TIER AI CONTENT GENERATOR (Failover Chain)
# ============================================================
# v7.2: "topic" added. It's REQUIRED (not optional) on purpose: build_prompt()
# asks for it as the FIRST key in the JSON, and a model writes JSON in
# order -- so having to state the specific theme first is what makes it
# commit to that theme BEFORE writing the hook and points. If it could
# skip the field, it could skip the theme-first thinking too. A missing/
# empty topic is treated like any other incomplete response: fall through
# to the next AI tier (the existing failover already handles that).
# "topic" is a short theme label, NOT spoken prose, so it is deliberately
# left out of the sentence-completeness check inside
# _validate_content_dict() (same as hook_search_query).
REQUIRED_CONTENT_KEYS = ["topic", "hook", "points", "hook_search_query", "caption"]

def _validate_content_dict(data, subtype: dict = None) -> bool:
    """
    Confirms the AI actually returned every field the rest of the pipeline
    needs. If a key is missing/empty, treat this as a FAILURE of that
    provider (fall through to the next AI tier) instead of crashing later,
    deep inside TTS or video generation, with a confusing KeyError.

    Also checks sentence COMPLETENESS, not just field PRESENCE -- unchanged
    principle from v6.6/v6.7, now applied to the hook, the caption, AND
    all 4 points' text (previously just "reveal" and "caption").

    v7.0 CHANGES (Hindi migration):
    1. NEW structural check: "points" must be a list of EXACTLY 4 items,
       each a dict with non-empty "text" and "search_query" strings. The
       old REQUIRED_CONTENT_KEYS truthiness check alone can't catch a
       malformed points list (e.g. only 3 items, or items missing
       "search_query") since a non-empty list is already truthy -- this
       adds that missing layer explicitly.
    2. The completeness/dangling-sentence check is now HINDI-AWARE, not
       English-aware:
       - Word extraction uses the Devanagari Unicode block (U+0900-U+097F)
         instead of [a-zA-Z] -- the old regex would have matched ZERO
         characters in Hindi text and silently never caught anything.
       - Terminal punctuation now accepts the Hindi danda (।, U+0964) as
         well as ".", "!", "?" -- properly punctuated Hindi very commonly
         ends a sentence with "।" instead of ".", so without this fix
         EVERY correctly-punctuated Hindi point would have wrongly FAILED
         this check and every single generation would have been rejected.
         Verified this is a real, expected Hindi punctuation mark, not an
         edge case to special-case around.
       - DANGLING_LAST_WORDS is now a Hindi connector/postposition list
         instead of an English one (see that set's own comment below for
         an honest note on how exhaustive this can realistically be).

    v6.5-6.6 (still true): this completeness check applies to EVERY field
    unconditionally -- no field gets a pass, matching the loop-trick
    removal principle (still 100% removed, see build_prompt()).
    subtype=None still skips the completeness check (used when a caller
    validates without a subtype in hand, e.g. in isolated tests) -- field
    presence/structure is still checked either way.
    """
    if not (isinstance(data, dict) and all(data.get(k) for k in REQUIRED_CONTENT_KEYS)):
        return False

    # Structural check on "points" -- must be exactly 4 well-formed
    # entries. A wrong count or a malformed entry is treated the same as
    # any other incomplete AI response: fall through to the next tier.
    points = data.get("points")
    if not isinstance(points, list) or len(points) != 4:
        return False
    for point in points:
        if not isinstance(point, dict) or not str(point.get("text", "")).strip() or not str(point.get("search_query", "")).strip():
            return False

    # v7.2: a whitespace-only (or non-string) topic is truthy, so it slips
    # through the key check above -- but it means the model skipped the
    # theme-first step, and it would also put a blank line into the
    # repeat-blocklist. Treat it as an incomplete response.
    topic = data.get("topic")
    if not isinstance(topic, str) or not topic.strip():
        return False

    if subtype is None:
        return True

    # Hindi connector/postposition words that, as the very LAST word of a
    # sentence, usually signal a truncated/dangling clause rather than a
    # real ending -- the Hindi equivalent of the old English
    # because/which/that/... list. HONEST LIMIT: Hindi grammar (lots of
    # short postpositions: को/में/पर/से/के/की/का) makes this harder to
    # enumerate exhaustively than English was -- treat this as a SECOND,
    # secondary layer of defense. The PRIMARY defense is the terminal-
    # punctuation check below (a text that doesn't end in ./!/?/। at all
    # is a much more reliable truncation signal and doesn't depend on
    # this list being complete).
    DANGLING_LAST_WORDS = {
        "क्योंकि", "जो", "जिसे", "जिसका", "जिसकी", "जिसमें", "जिन्हें",
        "अगर", "जब", "जबकि", "चूंकि", "कि", "और", "या",
        "को", "में", "पर", "से", "के", "की", "का", "ने",
    }
    import re
    texts_to_check = [data.get("hook", ""), data.get("caption", "")] + [p.get("text", "") for p in points]
    for text in texts_to_check:
        text = str(text).strip()
        if not text:
            continue
        # Strip a trailing "..." explicitly first -- same signal as before,
        # language-independent.
        if text.endswith("..."):
            return False
        # Devanagari word extraction (U+0900-U+097F) instead of [a-zA-Z] --
        # see docstring note above for why this specific fix matters.
        words = re.findall(r"[\u0900-\u097F']+", text)
        if words and words[-1] in DANGLING_LAST_WORDS:
            return False
        # Terminal punctuation check -- now accepts the Hindi danda (।) as
        # well as ./!/? (see docstring note above).
        if not re.search(r'[.!?।]["\')]?\s*$', text):
            return False

    # v7.3 NEW: repetition guard. Areeb reported TTS audio "repeating" in
    # production (v7.1, the version he actually ran). v7.1 raised
    # CONTENT_TEMPERATURE from 0.7 to 1.0 specifically for catchier
    # phrasing -- higher sampling temperature is a well-documented cause
    # of degenerate repetition loops in LLM generation, and none of the 4
    # AI tiers here set a repetition/frequency penalty. TTS reads back
    # exactly the text it's given, so a repeated clause in the TEXT is
    # exactly what "repeating" audio sounds like -- this catches it here,
    # before it ever reaches a TTS call, regardless of which AI tier
    # produced it. Two independent checks, since "repeating" could mean
    # either (a) the same clause repeated within one segment's own text,
    # or (b) two different segments ending up near-duplicate, which
    # sounds like a repeat when they play back to back.
    def _has_repeated_run(text: str, run_len: int = 4) -> bool:
        # Devanagari word extraction, same regex as the dangling-word
        # check above. A genuine VERBATIM 4-word run appearing twice in a
        # 12-20 word point is a strong signal of a degenerate loop, not
        # normal phrasing -- deliberately using exact-match on whole
        # words (not fuzzy) to avoid false positives on legitimate
        # repeated short words/postpositions.
        words = re.findall(r"[\u0900-\u097F']+", text)
        if len(words) < run_len * 2:
            return False
        seen_runs = set()
        for i in range(len(words) - run_len + 1):
            run = tuple(words[i:i + run_len])
            if run in seen_runs:
                return True
            seen_runs.add(run)
        return False

    for text in texts_to_check:
        if _has_repeated_run(str(text).strip()):
            return False

    # Exact-duplicate check across segments (hook + all 4 points, plus
    # caption) -- normalized whitespace only, not fuzzy, so this can only
    # fire on genuine duplication (e.g. a point accidentally repeating
    # the hook verbatim), never on merely-similar phrasing.
    normalized = [re.sub(r"\s+", " ", str(t).strip()) for t in texts_to_check if str(t).strip()]
    if len(normalized) != len(set(normalized)):
        return False

    return True

def generate_content(subtype: dict, recent_topics: list = None) -> dict:
    """
    v7.2: new optional `recent_topics` (themes already posted, from
    rotation_state.json's history -- see get_recent_topics()) is passed
    straight through to build_prompt() so the model avoids repeating
    them. Nothing else in this function changed -- the 4-tier failover
    below is still fully generic over what build_prompt() returns.

    CHANGED IN v6.3: now takes `subtype` (one of the field dicts from
    FIELDS -- 5 of them as of v7.0, was 9 COLUMNS subtypes pre-v7.0 --
    chosen by the rotation tracker in run() below) instead of using one
    fixed prompt for every post. build_prompt() reads that field's
    content_instruction/voice_register and constructs a prompt specific
    to it -- e.g. "anushasan" gets a blunt discipline-rules prompt,
    "adhyatm" gets a quiet reflective-truth prompt. Everything below this
    line (the actual 4-tier AI failover chain) is UNCHANGED since v6.2 --
    still fully generic over whatever build_prompt()/_validate_content_dict()
    return, so it needed NO changes for the v7.0 Hindi/points-schema
    migration -- and _validate_content_dict() still receives `subtype` so
    it can check sentence-completeness (see that function's docstring for
    the v7.0 Hindi-language fix this now also implements).
    """
    print(f"🧠 Querying AI Chain for {IG_HANDLE} content [{subtype['label']} / {subtype['key']}]...")

    prompt = build_prompt(subtype, recent_topics)

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
                config=types.GenerateContentConfig(temperature=CONTENT_TEMPERATURE)
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
                temperature=CONTENT_TEMPERATURE
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
    v6.7 (still true): generates audio for ONE SEGMENT at a time (hook OR
    one point), not a combined string -- run() calls this once per
    segment (5 times total as of v7.0: hook + 4 points) and
    create_reel_video() is called to match, then all 5 resulting clips
    are concatenated. `segment_label` is used only for clearer log lines
    (e.g. "hook", "point_1".."point_4"), it doesn't change any generation
    logic -- this function was ALREADY generic enough to need no signature
    change for the v7.0 migration.

    v7.0 TTS CHAIN CHANGE (Hindi migration): was a 3-tier chain
    (ElevenLabs -> Groq TTS -> Edge-TTS), now 2 tiers
    (ElevenLabs -> Edge-TTS). VERIFIED (Sep 26, via direct research, not
    assumed): Groq's TTS model (canopylabs/orpheus-v1-english) only
    serves English and Arabic -- there is no Hindi voice for it at all.
    Keeping it as a "tier" for Hindi text would be dead code that always
    silently falls through to Edge-TTS anyway, so it's removed entirely
    rather than left in as a non-functional no-op step. ElevenLabs
    (Tier 1) needed NO change -- it was already calling
    model_id="eleven_multilingual_v2", which already covers Hindi among
    its 29 languages, so the exact same call below already works for
    Hindi text. Edge-TTS (now Tier 2) switches from an English voice to
    hi-IN-MadhurNeural (free, unlimited, no API key). COST NOTE for
    Areeb: ElevenLabs' free tier is ~10 min of audio/month AND licensed
    non-commercial-only -- flagged to him before he chose to keep it as
    Tier 1 anyway; Edge-TTS Hindi is the zero-cost, no-licensing-
    restriction safety net underneath it either way.

    Still applies per-field pacing via build_tts_pacing() -- real rate
    control plus pitch/volume tuning plus comma-based pauses (see that
    function's own docstring -- mechanism unchanged, only the per-register
    values were re-tuned for the 5 new Hindi fields).
    """
    # Defensive check -- even though the caller (run()) always passes a
    # real string, this guards against a future edit accidentally passing
    # None or an empty segment through silently.
    full_text = (text or "").strip()
    if not full_text:
        print(f"❌ FATAL: No {segment_label} text available to speak (empty string).")
        return []

    out_path = f"output/tts_{segment_label}_{int(time.time())}.mp3"

    # Tier 1: ElevenLabs (Hindi via eleven_multilingual_v2 -- unchanged call)
    if ELEVENLABS_API_KEY:
        try:
            print(f"🎙️ [TTS 1/2] Trying ElevenLabs (Hindi) for {segment_label}...")
            from elevenlabs.client import ElevenLabs
            # ElevenLabs' SDK default timeout is 240s -- far too long to
            # wait before failing over to Edge-TTS. Cap it explicitly.
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
            print("⚠️ ElevenLabs returned an empty/too-small file. Moving to Edge-TTS...")
        except Exception as e:
            print(f"⚠️ ElevenLabs failed ({e}). Moving to Edge-TTS...")

    # Tier 2: Edge-TTS (Bulletproof local safety net -- free, no API key
    # needed, unlimited, no licensing restriction). Groq TTS tier REMOVED
    # here in v7.0 -- see docstring above for why (no Hindi voice exists
    # for that model, verified not assumed).
    # Uses build_tts_pacing() for per-field rate + pitch + volume +
    # comma-based pauses (see that function's docstring for why raw SSML
    # <break> tags do NOT work with this library -- verified by reading
    # edge-tts's source, not assumed, including the exact accepted format
    # for each parameter). ElevenLabs tier above takes plain text with no
    # per-call pacing knob in this simple API path, so it's left as raw
    # full_text -- unchanged.
    try:
        print(f"🎙️ [TTS 2/2] Generating fallback via Edge-TTS (Hindi) for {segment_label} (with pacing)...")
        import asyncio
        import edge_tts
        paced_text, rate, pitch, volume = build_tts_pacing(subtype, full_text)
        async def _speak():
            # rate/pitch/volume are all real Communicate() parameters,
            # confirmed against the library's own validation regex in
            # data_classes.py (rate/volume: "[+-]\d+%", pitch: "[+-]\d+Hz") --
            # these apply identically regardless of voice/locale, so no
            # new verification was needed for the Hindi voice switch.
            # paced_text has "..." converted to "," which edge-tts's
            # neural voice genuinely pauses on as normal comma prosody.
            # hi-IN-MadhurNeural (male) is the Hindi voice used here --
            # hi-IN-SwaraNeural (female) is the alternative if Areeb wants
            # to switch, same rate/pitch/volume params work with either.
            communicate = edge_tts.Communicate(
                paced_text, "hi-IN-MadhurNeural",
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
def create_reel_video(text: str, search_query: str, tts_path: str, subtype: dict, segment: str,
                       point_number: int = None, point_total: int = None) -> str:
    """
    v6.7 (still true): renders ONE SEGMENT of the reel at a time as its
    own standalone video clip -- not a combined single scene. Each
    segment gets its OWN background fetch (own search_query) and its OWN
    TTS audio (own tts_path) -- genuinely independent, not shared.

    v7.0 CHANGES (Hindi migration, 5-segment structure):
    - `segment` is now "hook" or "point_1".."point_4" (was "hook" or
      "reveal"). The internal `segment == "hook"` checks below are
      UNCHANGED and still correct -- every non-hook value (all 4 point
      labels) already falls into the same "else" branch that "reveal"
      used to, so no branching logic needed to change, only what gets
      passed in from run().
    - NEW optional `point_number`/`point_total` params (e.g. 1/4, 2/4...)
      -- when point_number is given, a small "बात X/4" progress badge is
      drawn near the top of frame. This is Areeb's explicit "hooked till
      the end" ask: a persistent on-screen counter gives the viewer a
      reason to keep watching for the next number. Left as None for the
      hook segment (no badge on the hook).
    - Font selection now points at the Devanagari fonts (FONT_HINDI_*)
      instead of the Latin DejaVu ones -- see reel_font_map below. The
      hook always renders in FONT_HINDI_SANS_BOLD now (was always
      FONT_ITALIC) since the free Devanagari font family has no italic
      face at all (verified via fc-list, see FONT_HINDI_* constants'
      comment above for the exact check run).

    UNCHANGED FROM v6.6:
    1. BACKGROUND SOURCE + TREATMENT: fetches a real Pexels/Unsplash
       video/image via get_reel_background(), tinted with subtype's brand
       color at subtype["overlay_opacity"]. Bold/graphic fields
       (anushasan/career_paisa/sehat) use a strong tint (~0.68-0.72) so
       the brand color still reads instantly; quieter fields
       (adhyatm/rishtey) use a lighter tint (~0.50-0.60).
    2. TEXT STYLING: colors/fonts pulled from the sub-type dict.
    3. OVERFLOW GUARD: uses PIL's actual multiline_textbbox measurement
       plus anchor-point clamping so long text never escapes the frame --
       this matters for every point now, not just one "reveal" -- a
       truncated point 3 after the hook already built anticipation is a
       worse failure than before.
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

        # Map this field's short font_style name to a real font file --
        # local dict here since this is a single-file script (no separate
        # renderer module to share a FONT_MAP with).
        #
        # v7.0: repointed from the 3 Latin DejaVu fonts to the 4 Devanagari
        # Noto fonts (see FONT_HINDI_* constants' comment for the apt-get
        # requirement + the empirical shaping test behind this choice).
        # FIELDS only actually uses "sans_bold" and "serif_regular" (see
        # FIELDS above), but the old font_style names are still mapped
        # here too (to their closest Devanagari equivalent) so this map
        # doesn't silently break if a field's font_style is hand-edited
        # later to one of the pre-v7.0 names.
        reel_font_map = {
            "sans_bold":              FONT_HINDI_SANS_BOLD,
            "sans_bold_condensed":    FONT_HINDI_SANS_BOLD,
            "sans_regular":           FONT_HINDI_SANS_REGULAR,
            "serif_regular":          FONT_HINDI_SERIF_REGULAR,
            "serif_thin":             FONT_HINDI_SERIF_REGULAR,
            "serif_caption":          FONT_HINDI_SERIF_REGULAR,
            "serif_italic":           FONT_HINDI_SERIF_REGULAR,  # no Devanagari italic exists -- see FONT_HINDI_* comment
            "serif_italic_elegant":   FONT_HINDI_SERIF_REGULAR,  # same fallback, no italic face available
        }
        body_font_path = reel_font_map.get(subtype.get("font_style"), FONT_HINDI_SERIF_REGULAR)

        try:
            # IG_HANDLE ("@brain.blueprints") is Latin script regardless of
            # content language, so the watermark stays on FONT_SANS
            # (DejaVu) deliberately -- unchanged from before.
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
        # v7.0: hook now always uses FONT_HINDI_SANS_BOLD (was always
        # FONT_ITALIC) -- bold-for-punch instead of italic-for-distinction,
        # since the free Devanagari font family has no italic face at all
        # (verified via fc-list, see FONT_HINDI_* constants' comment).
        text_font_path = FONT_HINDI_SANS_BOLD if segment == "hook" else body_font_path

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

        # v7.0 NEW: "बात X/4" progress badge, only for point segments
        # (point_number is None for the hook, so this is skipped for
        # segment 1). Areeb's explicit ask: hook the viewer till the end
        # of the reel -- a persistent on-screen counter gives a concrete
        # reason to keep watching for the next number, the same mechanic
        # that makes numbered listicles retain viewers better than an
        # unnumbered list would. Drawn at y=190, well above the main
        # text's safe area (y=300-1650) -- no collision possible
        # regardless of how tall the point's text block ends up.
        if point_number is not None and point_total is not None:
            try:
                font_badge = ImageFont.truetype(FONT_HINDI_SANS_BOLD, 44)
            except Exception:
                font_badge = font_brand  # graceful fallback -- badge just uses the watermark font if this fails
            badge_text = f"बात {point_number}/{point_total}"
            draw.text((540, 190), badge_text, font=font_badge, fill=subtype.get("accent_color", "#E0C080"), anchor="mm", align="center")

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


def concatenate_reel_segments(segment_paths: list) -> str:
    """
    v6.7 (concept unchanged): stitches independently-rendered segment
    clips into one final reel file, back to back, no overlap, no
    crossfade -- a hard cut, matching Areeb's requirement that only one
    segment's content is ever on screen at a time. Each input clip
    already has its own correct audio (from its own TTS call) baked in
    via create_reel_video()'s CompositeVideoClip(...).set_audio(...)
    step, so concatenation here is audio+video together, not video-only
    with a separate audio merge.

    v7.0 SIGNATURE CHANGE: was (hook_video_path, reveal_video_path) --
    exactly 2 fixed positional args. Now takes `segment_paths: list`, in
    playback order (hook first, then point_1..point_4) -- 5 items as of
    v7.0's structure, but genuinely N-length so this function itself
    doesn't hardcode "5" anywhere; run() below is what decides how many
    segments actually exist. This was necessary because a fixed 2-arg
    signature can't express "hook + 4 points" without either 5 separate
    named parameters (worse) or a list (this).

    Uses moviepy's concatenate_videoclips with method="compose" rather
    than the default "chain" -- "compose" pads any inconsistent frame
    sizing between clips onto a common canvas instead of failing
    outright, which matters here because each segment comes from a
    SEPARATE get_reel_background() fetch that could technically return
    sources with slightly different native aspect ratios before the
    existing resize/crop-to-1080x1920 step in create_reel_video()
    normalizes them -- "compose" is a safety net on top of that
    normalization, not a replacement for it.
    """
    print(f"🔗 Concatenating {len(segment_paths)} segments into final reel...")
    try:
        from moviepy.editor import VideoFileClip, concatenate_videoclips

        clips = [VideoFileClip(p) for p in segment_paths]

        final_clip = concatenate_videoclips(clips, method="compose")
        final_path = f"output/reel_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        # v6.8 FIX (still applies, unchanged): same -movflags +faststart
        # fix as create_reel_video() above, and MORE important here
        # specifically -- this call produces the FINAL file that actually
        # gets uploaded to Instagram (the per-segment files from
        # create_reel_video() are only intermediate inputs to this
        # concatenation step and get deleted afterward in run() on
        # success). concatenate_videoclips() re-encodes rather than just
        # concatenating raw bytes, so this write_videofile call is a
        # completely independent ffmpeg invocation that needs its own
        # explicit flag, not something inherited from the inputs.
        final_clip.write_videofile(
            final_path, fps=24, codec="libx264", audio_codec="aac",
            verbose=False, logger=None,
            ffmpeg_params=["-movflags", "+faststart"],
        )

        total_duration = sum(c.duration for c in clips)
        for c in clips:
            c.close()

        # Same sanity check as create_reel_video's own output check, now
        # SCALED to segment count instead of a fixed 100KB floor -- a real
        # 5-segment reel should be well over 5x the single-segment 50KB
        # floor; a 2-segment test render should still clear 100KB exactly
        # as before. Scaling this way means the check stays meaningful
        # whether segment_paths has 2 items or 5.
        min_expected_bytes = 50_000 * len(segment_paths)
        if not os.path.exists(final_path) or os.path.getsize(final_path) < min_expected_bytes:
            print("❌ Concatenated video file is missing or suspiciously small -- treating as a failed render.")
            return None

        print(f"✅ Final reel assembled: {final_path} ({len(segment_paths)} segments, {total_duration:.1f}s total)")
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

    # ---- pick this run's field from the rotation tracker ----
    # IMPORTANT (unchanged principle from v6.7): rotation_state is loaded
    # and the NEXT pick is computed here, but intentionally NOT SAVED yet.
    # state (the in-memory dict) has already been mutated by
    # pick_next_field_and_advance() to reflect what comes after THIS post
    # -- but the FILE on disk still reflects the position before this run.
    # It only gets written (save_rotation_state) at the very end, and ONLY
    # if the post actually succeeds. This matters because: if this run
    # picks "rishtey" and then TTS or video rendering or the IG publish
    # step fails, "rishtey" never actually got posted -- so the rotation
    # must NOT advance, or the next run would skip straight past it and
    # the 5-field pattern would silently drift off by one forever.
    #
    # v7.0: field (a dict from FIELDS) is still passed as `subtype` to
    # generate_content/generate_tts/create_reel_video below -- see
    # build_prompt()'s docstring for why that parameter name was
    # deliberately left unchanged rather than renamed everywhere.
    state = load_rotation_state()
    field_index, field = pick_next_field_and_advance(state)

    print(f"\n🚀 STARTING WORKFLOW: [REEL] for {IG_HANDLE}")
    print(f"   Field: '{field['key']}' ({field['label']})\n")

    # v7.2: themes already posted (from rotation_state.json's history) go
    # to the model so it doesn't repeat one -- see get_recent_topics().
    recent_topics = get_recent_topics(state)
    data = generate_content(field, recent_topics)
    # The chosen theme is worth seeing in the Actions log: it shows at a
    # glance whether the model actually went specific or drifted back to
    # a generic "4 tips about X" theme.
    print(f"   Theme this run: {data.get('topic', '')}")
    print(f"   Hook: {data.get('hook', '')}\n")

    # v7.0: hashtag map re-keyed from the 9 psychology voice_registers to
    # the 5 Hindi FIELDS voice_registers -- mixing Hindi-content-relevant
    # English/Hinglish tags is standard IG practice (that's genuinely how
    # Hindi content gets tagged/discovered), not an inconsistency.
    base_tags = "#hindimotivation #jeevanmantra #brainblueprints"
    register_tags = {
        "sehat":         "#sehat #fitness #healthtips",
        "rishtey":       "#rishtey #relationshipgoals #hindiquotes",
        "career_paisa":  "#success #career #paisa",
        "anushasan":     "#discipline #selfimprovement #motivation",
        "adhyatm":       "#shanti #spirituality #gyaan",
    }
    extra_tags = register_tags.get(field.get("voice_register", ""), "#hindiquotes")
    caption = f"{data.get('caption', '')}\n\n{base_tags} {extra_tags}"

    os.makedirs("output", exist_ok=True)

    # v7.0 CONTENT STRATEGY CHANGE: hook + 4 points are now FIVE genuinely
    # separate segments -- each with its own audio, own background image,
    # own on-screen text -- concatenated into one final reel (was 2
    # segments/hook+reveal in v6.7). Each of the 10 steps below (hook TTS,
    # hook video, then TTS+video for each of the 4 points) can
    # independently fail; if ANY of them does, the whole run fails and
    # the rotation does NOT advance, same safety property as before, just
    # now checked at 10 points instead of 4.
    segment_video_paths = []

    print("\n--- SEGMENT 1: HOOK ---")
    hook_tts_paths = generate_tts(data.get("hook", ""), field, segment_label="hook")
    if not hook_tts_paths:
        print("❌ FATAL: No usable audio was produced for the HOOK segment.")
        print(f"   -> Rotation NOT advanced (still field '{field['key']}' next run).")
        sys.exit(1)

    hook_video_path = create_reel_video(
        text=data.get("hook", ""),
        search_query=data.get("hook_search_query", ""),
        tts_path=hook_tts_paths[0],
        subtype=field,
        segment="hook",
    )
    if not hook_video_path:
        print("❌ FATAL: HOOK segment video render failed.")
        print(f"   -> Rotation NOT advanced (still field '{field['key']}' next run).")
        sys.exit(1)
    segment_video_paths.append(hook_video_path)

    # v7.0 NEW: loop over the 4 points (was a single fixed "reveal" step
    # in v6.7). _validate_content_dict() already confirmed data["points"]
    # has exactly 4 well-formed entries before generate_content() returned
    # it, so this loop always runs exactly 4 times in practice -- written
    # as a loop over len(data["points"]) rather than a hardcoded range(4)
    # anyway, so it degrades gracefully instead of crashing if that
    # invariant is ever violated.
    points = data.get("points", [])
    for i, point in enumerate(points, start=1):
        print(f"\n--- SEGMENT {i + 1}: POINT {i}/{len(points)} ---")
        point_tts_paths = generate_tts(point.get("text", ""), field, segment_label=f"point_{i}")
        if not point_tts_paths:
            print(f"❌ FATAL: No usable audio was produced for POINT {i}.")
            print(f"   -> Rotation NOT advanced (still field '{field['key']}' next run).")
            sys.exit(1)

        point_video_path = create_reel_video(
            text=point.get("text", ""),
            search_query=point.get("search_query", ""),
            tts_path=point_tts_paths[0],
            subtype=field,
            segment=f"point_{i}",
            point_number=i,
            point_total=len(points),
        )
        if not point_video_path:
            print(f"❌ FATAL: POINT {i} video render failed.")
            print(f"   -> Rotation NOT advanced (still field '{field['key']}' next run).")
            sys.exit(1)
        segment_video_paths.append(point_video_path)

    print("\n--- ASSEMBLING FINAL REEL ---")
    reel_path = concatenate_reel_segments(segment_video_paths)
    if reel_path:
        success = post_to_instagram(reel_path, caption)
        if success:
            # ONLY save the advanced rotation state here, after a confirmed
            # successful publish -- see the big comment above run() for why
            # this ordering is load-bearing, not arbitrary.
            #
            # v7.2: also record THIS run's theme into its history entry (the
            # last one, appended by pick_next_field_and_advance() at the top
            # of run()) so future runs can avoid repeating it -- see
            # get_recent_topics(). Deliberately done here, after a confirmed
            # publish, for the same reason the rotation itself only advances
            # here: a theme that never actually got posted shouldn't be
            # blocklisted.
            if state.get("history"):
                state["history"][-1]["topic"] = data.get("topic", "")
            save_rotation_state(state)
            # Clean up the intermediate per-segment files now that the
            # final concatenated reel has been confirmed published -- these
            # served their purpose as inputs to concatenate_reel_segments()
            # and aren't needed after a successful run. Left in place on
            # FAILURE (no cleanup call in any of the sys.exit(1) branches
            # above) so a failed run's intermediate files are still on disk
            # for debugging in the Actions log/artifact, if needed.
            for leftover in segment_video_paths:
                try:
                    os.remove(leftover)
                except OSError:
                    pass
            next_field_key = FIELDS[state["next_field_index"] % len(FIELDS)]["key"]
            print(f"\n✅ WORKFLOW COMPLETED SUCCESSFULLY! (field '{field['key']}' posted, {len(segment_video_paths)} segments)")
            print(f"   Next run will post: field '{next_field_key}'")
        else:
            print("\n❌ WORKFLOW FAILED at the Instagram publish step -- see the ❌/⚠️ lines above for the exact reason.")
            print(f"   -> Rotation NOT advanced (still field '{field['key']}' next run).")
            sys.exit(1)
    else:
        print("\n❌ WORKFLOW FAILED at final segment concatenation -- see the ❌/⚠️ lines above for the exact reason.")
        print(f"   -> Rotation NOT advanced (still field '{field['key']}' next run).")
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
