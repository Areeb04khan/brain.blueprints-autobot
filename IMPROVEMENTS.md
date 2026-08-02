# Brain Blueprints Bot v6.3 - Content & Format Improvements

## What Changed

### 1. **Three-Column Visual Layout** (Major)
**Before:** Single column of text centered on a dark background. Looked like a generic quote graphic.

**After:** Three side-by-side columns, each representing a different angle/lens on ONE core psychological concept. Like a comparison table.

**Visual Structure:**
```
┌─────────────────────────────────────────────────────────┐
│                   DOMINANCE SIGNALS                      │
├─────────────────┬─────────────────┬─────────────────────┤
│ SUBMISSIVE      │ DOMINANT        │ MASTER              │
│                 │                 │                     │
│ Downward gaze   │ Steady gaze     │ Relaxed posture    │
│ Open palms      │ Controlled tone │ Comfortable pause  │
│                 │                 │                     │
│ Nervous         │ Boardroom       │ Executive          │
│ interviews      │ meetings        │ presence           │
├─────────────────┼─────────────────┼─────────────────────┤
│        @brain.blueprints                                │
└─────────────────────────────────────────────────────────┘
```

**Why this matters:**
- **Visually organized:** Easier to scan, more professional
- **Educational depth:** Shows progression/contrast instead of isolated facts
- **Higher retention:** People remember comparisons better than standalone statements
- **More engaging:** The golden dividers + color contrast = higher visual interest
- **Meme-able:** People want to repost it because it's actually useful

---

### 2. **Higher-Quality Content Generation** (Major)
**Before:** Generic 3-sentence psychology tips that could apply to anyone/anything.
```
"Lower your tone at the end of sentences instead of raising it. Never break eye contact 
first during silence. This is why you need these tricks..."
```
**After:** Deep, multi-angle education on ONE specific behavioral concept.
```
Column 1: "Submissive Signal — Downward gaze and open palms — Visible in nervous interviews"
Column 2: "Dominant Signal — Chin up, steady breathing, controlled eye contact — Boardroom settings"
Column 3: "Master Signal — Relaxed posture, comfortable silence, unhurried speech — Executive presence"
```

**Content rules enforced by the AI prompt:**
1. **Three distinct angles** - not three random facts, but three lenses on the same behavior
2. **Specific, observable details** - not vague ("shows respect") but concrete ("downward gaze")
3. **Real-world context** - not just theory, but where you'd actually see this (job interviews, boardrooms, etc.)
4. **Progression** - each column builds on the last, showing escalation or different contexts
5. **Educational value** - something you could actually use to read people better

**Quality check:** If any AI provider returns incomplete JSON or missing fields, it's treated as a **failure of that provider** and falls through to the next tier (Gemini → OpenRouter → Groq → NVIDIA). This means you'll never get a half-baked response—you get the best available, or you get nothing (and retry later).

---

### 3. **Natural-Sounding Speech (SSML Prosody)** (Major)
**Before:** Robotic monotone. Every sentence at the same speed, pitch, volume. Sounds like a GPS.
```
[Monotone]: "Watch how dominance is expressed in three ways. First, the submissive signal..."
```

**After:** Human-sounding narration with intentional pauses, pitch variation, and pace control.
```
[Natural]: 🎙️ [Slow, authoritative] "Watch how dominance is expressed in three ways."
          🎙️ [Pause 400ms]
          🎙️ [Slower, lower pitch] "First, the submissive signal."
          🎙️ [Pause 300ms]
          🎙️ [Normal pace] "Notice the downward gaze and open palms."
          [etc.]
```

**How it works (SSML = Speech Synthesis Markup Language):**
- `<prosody rate="0.85">` = slow down to 85% speed (lets important stuff sink in)
- `<prosody pitch="-5%">` = lower pitch (sounds more authoritative/serious)
- `<break time="400ms"/>` = pause for 400 milliseconds (natural breathing room)

**Strategy by sentence type:**
- **Intro/headers** ("First, the submissive signal") → Slow (0.85x), lower pitch (-5%) → 400ms pause
  - Makes the listener sit up and pay attention
- **Details/observations** ("Notice the downward gaze") → Normal-slow (0.9x) → 300ms pause
  - Gives enough time to visualize
- **Real-world context** ("Visible in nervous interviews") → Slightly faster (1.0x) → 250ms pause
  - Keeps flow going
- **Conclusions** → Slow (0.85x), authoritative pitch → 400ms pause
  - Lets the insight land

**Why this matters:**
- People focus better when speech isn't monotone (proven by cognitive psych research)
- Pauses = breathing room = easier to follow
- Pitch variation = emotional engagement (not boring)
- Humans DO this naturally when explaining something important—the bot now does too

**Cost:** Zero. SSML is a free feature of ElevenLabs, Groq TTS, and Edge-TTS.

---

### 4. **Improved Narration Script** (Major)
**Before:** Random sentence order, no structure, no clear progression.

**After:** Clear three-part structure with smooth transitions:
```
1. [SETUP] "Watch how dominance is expressed in three ways."
   [PAUSE]
2. [ANGLE 1] "First, the submissive signal. [Details]. [Real-world example]."
   [PAUSE]
3. [ANGLE 2] "Second, the dominant signal. [Details]. [Real-world example]."
   [PAUSE]
4. [ANGLE 3] "Third, the master signal. [Details]. [Real-world example]."
   [PAUSE]
5. [CONCLUSION] "Master this and you unlock real social power."
```

The AI is explicitly told to:
- Use "First, Second, Third" structure (guides listener through three columns)
- Match narration to the visuals (audio and video together tell the story)
- Keep it 12-15 seconds (long enough to be interesting, short enough for Instagram's audience attention span)
- Use simple, direct language (no fancy prose—clarity wins)
- NO all-caps, NO excessive punctuation (it breaks SSML prosody)

---

### 5. **Backend Improvements** (Invisible, but important)

**Script validation:** The AI-generated script is now validated for completeness before it reaches TTS. If it's missing required fields, that AI provider is marked as failed, and we move to the next one. This prevents crashes deep in the rendering pipeline.

**Audio file validation:** Generated audio files are checked to make sure they're real audio (>1KB) before being used. A corrupted/truncated file from a flaky TTS provider is rejected and falls through to the next tier.

**Video file validation:** Same logic for the rendered video. A video <50KB is clearly not a real 15-30 second reel and is rejected.

---

## What You'll See (In Your Reels)

### Visual Changes
- **Before:** Centered text, one idea, generic vibe
- **After:** Three-column layout, organized progression, professional education look

### Audio Changes
- **Before:** Monotone robot voice
- **After:** Natural speech with pauses and emphasis, sounds like someone explaining something in person

### Content Quality
- **Before:** Surface-level psychology tips that sound made up
- **After:** Specific, behavioral, real-world applicable insights

### Engagement (Expected)
- **Saves:** Higher (people want to reference this specific framework)
- **Shares:** Higher (it's a useful comparison, not just a quote)
- **Watch-through:** Higher (visual + audio structure keeps attention)
- **Comments:** Higher (specific content invites discussion: "I see this at work all the time")

---

## Cost

**₹0 added cost.**

- SSML is a free feature of your existing TTS providers
- No new APIs or services
- Only existing code is the layout logic (PIL drawing, no external dependencies)

---

## How It Works (Technical Details)

### Content Generation Pipeline
```
🧠 AI Prompt (high-quality, three-column structure)
  ↓
  [Gemini] → if incomplete, fail to →
  [OpenRouter] → if incomplete, fail to →
  [Groq] → if incomplete, fail to →
  [NVIDIA NIM]
  ↓
  Validation: all 7 required fields present? all non-empty?
  ↓
  Output: structured JSON with three columns
```

### TTS Pipeline
```
Narration Script (plain text)
  ↓
  _wrap_script_in_ssml() → converts to SSML with <prosody> and <break> tags
  ↓
  [ElevenLabs] → if fails/too small, fall to →
  [Groq TTS] → if fails/too small, fall to →
  [Edge-TTS] → guaranteed to work (free, local-ish)
  ↓
  Validate: audio file >1KB?
  ↓
  Output: MP3 with natural pacing
```

### Video Rendering Pipeline
```
Background (Pexels video / Unsplash image / plain color)
  ↓
  + Text overlay (three-column layout, 1080x1920)
  ↓
  + Audio (narration)
  ↓
  moviepy renders to MP4
  ↓
  Validate: video file >50KB?
  ↓
  Output: ready for Instagram
```

---

## What You Need to Do

**Nothing.** Just replace `poster.py` with the new version. The next scheduled run will use the new format.

The YAML file is unchanged (same dependencies, same schedule).

---

## FAQ

**Q: Will my old followers understand the new format?**
A: Yes. It's actually easier to understand—a clear comparison is more intuitive than a random tip.

**Q: Does this cost more per run?**
A: No. Same AI calls, same TTS calls, same media hosts. Just better organized.

**Q: What if the AI generates weird/low-quality content?**
A: The prompt is very specific about what makes good three-column content. Gemini/Groq usually nail it on the first try. If you ever get bad content, you can regenerate immediately via `workflow_dispatch` from the GitHub Actions tab (no code change needed).

**Q: Can I customize the colors/fonts?**
A: Yes. Look for these lines in `create_reel_video()`:
  - `fill="#FFD700"` (title color)
  - `fill="#FF6B9D"` (column angle names)
  - `fill="#E0E0E0"` (details)
  - `fill="#A0D8A0"` (examples with 💡)
  - `font_header = ImageFont.truetype(FONT_SANS, 32)` (sizes)

**Q: The speech sounds robotic/too slow?**
A: Edit the `_wrap_script_in_ssml()` function:
  - Change `rate="0.85"` to `rate="0.95"` for faster
  - Change `pitch="-5%"` to `pitch="0%"` for neutral pitch
  - Change `break time="400ms"` to `break time="200ms"` for shorter pauses
  
  Experiment and re-run `workflow_dispatch` to hear the changes.

**Q: Can I go back to the old format?**
A: Yes, revert to the v6.2 poster.py from git history. But you won't want to—this version is better.

---

## Summary

Your bot now generates **educational, visually organized, professionally-narrated content** instead of generic psychology tips. Each reel is a mini-lesson with three perspectives on one behavioral truth, natural speech, and a layout that looks good on mobile.

This is a significant content quality jump with zero added cost.
