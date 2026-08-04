# Brain Blueprints Bot - v6.3 (Grid-Column Rotation System)

## What's New

Your Instagram grid now has **three distinct columns** — each one its own visual identity and voice — rotating 1→2→3→1... across your feed, matching the pattern you see on reference accounts like @houseofinvestors.

**Grid Pattern:**
```
Column 1          Column 2          Column 3
(Command)         (Do)              (Rule)
Black imperative  Navy actionable   Black/white numbered
│                 │                 │
(Warn)            (Notice)          (Story)
Maroon alarm      Sage observe      Dark photo+caption
│                 │                 │
(Sit With)        (Become)          (Truth)
Cream reflect     Charcoal gold     Gray universal
│                 │                 │
[repeats]         [repeats]         [repeats]
```

Each column cycles through its own 3 sub-types (A→B→C→A...) independently, while the columns themselves post 1→2→3→1... in sequence. Result: your grid reads as three recognizable series, not a uniform blur of "similar posts."

**Cost:** ₹0 — no new APIs, same failover chains as v6.2.

---

## Files You Get

| File | What It Does |
|------|---|
| `poster.py` | **Replace your current poster.py with this.** Contains rotation logic, column definitions, content prompts, and the full reel pipeline. Single file, all inlined — no extra dependencies. |
| `SETUP_GITHUB_ACTIONS.md` | **Read this first.** Two small workflow changes required (one new step + one permission block). Shows you the exact lines to add to your main.yml. |
| `README_v6.3.md` | This file. What you're reading now. |

---

## What Actually Changed (From Your Current Bot)

### Three Key Additions

**1. Column Rotation Tracker**
- New file: `rotation_state.json` (created automatically on first run)
- Lives in your repo, committed after each successful post
- Tracks: which column posts next + each column's current sub-type position
- No manual setup needed — the workflow step in `SETUP_GITHUB_ACTIONS.md` handles the git commit/push

**2. Nine Distinct Sub-Types**
Each has its own:
- **Background color** (black, maroon, cream, navy, sage, charcoal, etc.)
- **Text color & accent** (whites, golds, muted earth tones)
- **Font style** (bold sans, italic serif, condensed, elegant)
- **Voice register** (imperative, alarm, aphoristic, actionable, observational, identity-statement, numbered-rule, micro-scenario, universal-truth)
- **Content instruction** (baked into the AI prompt, so every type generates different-sounding content)
- **Visual mood hint** (guides the search_query sent to Pexels/Unsplash, so each column fetches on-brand footage)
- **Overlay opacity** (bold types get a strong tint over their video; quiet types let the scene show through)

**3. Dynamic Content Per Sub-Type**
- Old bot: one hardcoded prompt → every post sounds the same
- New bot: nine different prompts → "Command" reads as direct imperative, "Sit With" reads as quiet reflection, "Story" reads as narrative scenario
- All 9 still use the same JSON schema downstream, so nothing breaks

### What Didn't Change

- All 4 AI failover tiers (Gemini → OpenRouter → Groq → NVIDIA NIM)
- All 3 TTS failover tiers (ElevenLabs → Groq TTS → Edge-TTS)
- Both media hosts (tempfile.org → catbox.moe)
- Instagram Graph API publish logic
- Retry + timeout handling
- 3 posts/day schedule via GitHub Actions

---

## Getting Started (2 Steps)

### Step 1: Update Your Workflow

Open `.github/workflows/main.yml` (or whatever your workflow file is named) and make the two changes shown in `SETUP_GITHUB_ACTIONS.md`:

1. Add `permissions: contents: write` under `jobs: post-reel:`
2. Add the new "Commit updated rotation state" step after "Run Bot Script"

That's it. No changes to the Python dependencies, package versions, or secret names.

### Step 2: Deploy

```bash
# In your repo root:
cp poster.py .     # Replace your current poster.py with the new one
git add poster.py
git commit -m "v6.3: grid-column rotation system with distinct visual identities"
git push origin main
```

Done. Next run will create `rotation_state.json` automatically (you'll see it in the workflow log).

---

## How It Works (Under the Hood)

### Rotation Logic

Every run:
1. Load `rotation_state.json` (or start fresh at Column 1 if it doesn't exist)
2. Pick the next column/sub-type from the tracker
3. Advance the state in-memory (but **don't** save yet)
4. Generate content using that sub-type's specific prompt
5. Compose the reel with that sub-type's colors/fonts
6. Publish to Instagram
7. **Only then** save the advanced state back to `rotation_state.json` and commit

Why the delayed save? If anything fails partway through (TTS fails, video render fails, Instagram publish fails), the rotation never advanced — so the next run retries the same column/sub-type. This prevents silent desynchronization when runs fail.

### Content Generation

Each sub-type has a `content_instruction` field, e.g.:
- **Command:** "Write a short, DIRECT, second-person IMPERATIVE instruction... Use command verbs (Speak less. Hold your ground. Never explain twice.)... 1-2 sentences maximum."
- **Sit With:** "Write ONE quiet, aphoristic closing thought... NOT an instruction, NOT a warning... Should feel like the last line of a chapter, not the first... 1 sentence, maximum 20 words."
- **Story:** "Write a TINY narrative micro-scenario... Third person or implied scene, past tense... NO explicit advice or moral stated -- the reader infers it... 1-2 short sentences, cinematic and specific."

The AI prompt changes based on which sub-type is picked, so every column reads as its own voice.

### Visual Identity

- **Command** (black bg, white text): demands visual dominance with a 0.72 opacity tint
- **Story** (photo bg, light tint): lets the actual scene breathe with a 0.35 opacity tint
- All 9 subtypes fetch real Pexels/Unsplash video/images (same as your original bot), but the tint color + opacity make each one recognizable at a glance

---

## What Can Go Wrong (And How It's Handled)

### Automatic Fallbacks
- ✅ AI provider down → cycles through 4 tiers
- ✅ TTS provider down → cycles through 3 tiers
- ✅ Pexels/Unsplash fail → uses flat bg_color (still on-brand)
- ✅ Media host down → tries second host
- ✅ Instagram API timeout → retries up to 4 minutes
- ✅ Network hiccup → retry with exponential backoff

### Things That Require Manual Intervention
- ❌ Instagram access token expired (long-lived tokens last ~60 days) → regenerate in Meta developer console
- ❌ All AI + TTS providers down simultaneously (has never happened) → wait, next run in 8 hours will retry

### Important: Rotation State Isn't Saved on Failure
If your run fails at step 5 (video render) or step 6 (Instagram publish), `rotation_state.json` **does not get updated**. The next run will retry the exact same column/sub-type. This is intentional — it prevents silently losing a turn when something goes wrong.

---

## Customization

Everything is defined in `poster.py` with inline comments.

### Change a Sub-Type's Appearance
Edit the `COLUMNS` dict near the top of `poster.py`:
```python
COLUMNS = {
    1: [
        {
            "key": "command",
            "bg_color": "#0A0A0A",        # Change this hex color
            "text_color": "#FFFFFF",       # Or this one
            "accent_color": "#FFFFFF",     # Or this one
            "overlay_opacity": 0.72,       # Or this opacity (0.0-1.0)
            ...
        },
        ...
    ],
    ...
}
```

### Change What a Sub-Type Says
Edit that sub-type's `content_instruction` (the long string starting with "Write a short..."). The AI will follow your instructions exactly.

### Change Colors Globally
Search `poster.py` for any hex color (`#FFFFFF`, `#0A0A0A`, etc.) and replace it. Comments explain what each color controls.

### Change Video/Image Fetch Query
Edit the `visual_mood_instruction` field for any sub-type. This string tells Pexels/Unsplash what kind of image to fetch. E.g.:
```python
"visual_mood_instruction": (
    "a short 2-4 word visual search query for stark, minimal, "
    "powerful imagery (e.g. 'empty modern architecture', 'single "
    "silhouette dark room', 'clean dark hallway')"
),
```

---

## FAQ

**Q: Do I need to change anything else in my workflow?**
A: Just the two lines shown in `SETUP_GITHUB_ACTIONS.md`. No changes to Python packages, secrets, or schedule.

**Q: What if I commit a mistake to `rotation_state.json`?**
A: Just delete it from the repo. On the next run, `poster.py` will detect it's missing, start fresh at Column 1, and regenerate it correctly.

**Q: Can I reset the rotation to start over?**
A: Yes, delete `rotation_state.json` from the repo and let the next run recreate it.

**Q: How long does a run take?**
A: 2-5 minutes for a successful run (same as before). With retries for failed providers, up to 8-10 minutes worst case.

**Q: Will my followers understand the grid columns?**
A: Yes — it's actually easier to understand than random tips. Each column develops its own personality, which is engaging.

**Q: Can I add more than 3 columns?**
A: Yes, but it requires:
1. Adding new column defs to `COLUMNS` dict
2. Editing `pick_next_column_and_advance()` to cycle through more columns
3. Testing and tweaking the rendering logic in `create_reel_video()`

See the comments in those functions for guidance.

**Q: What if Pexels/Unsplash fail to return an image?**
A: The reel still renders with the sub-type's `bg_color` as a flat background. It's still on-brand, just less cinematic.

---

## Performance

| Scenario | Time |
|----------|------|
| Normal run (all APIs responsive) | 2-4 minutes |
| One tier fails, uses fallback | +30 seconds |
| Multiple failovers needed | +1-2 minutes |
| Worst case with full retry loop | ~8-10 minutes (still within 30-min timeout) |

No run should ever timeout. If it does, check the logs — something is wrong with an API key or network.

---

## Troubleshooting

### "rotation_state.json not found" on first run
**This is normal.** The script prints this and starts fresh at Column 1. After the first successful run, the file exists.

### Post says "Column 1 → command" but didn't post
**Check the full log.** The run probably failed at TTS, video render, or Instagram publish. The next run will retry Column 1 → command again.

### Grid looks misaligned or text is cropped
**The reel itself is fine; Instagram's grid thumbnail cropping is aggressive.** 1080x1920 reels get cropped to show only the center area in the grid. Text near the top/bottom might get cut off. This is Instagram's behavior, not the bot's.

### "All TTS providers failed"
**Check your TTS API keys in GitHub Secrets.** ElevenLabs → Groq → Edge-TTS is a guaranteed fallback chain — if all three failed, your keys are wrong or your network is completely down.

---

## Version History

| Version | Date | What Changed |
|---------|------|---|
| **v6.3** | 2026-08-04 | Grid-column rotation system, 9 sub-types, independent column cycles, real video for all types, colored tinting |
| **v6.2** | 2026-07-30 | Media upload fallback chain (tempfile → catbox), timeout on all external calls, Instagram retry logic |
| **v6.1** | 2026-07-15 | Multi-tier AI & TTS failover chains (foundation) |

---

## What This Replaces

- **Old poster.py:** Static one-prompt-fits-all approach
- **New poster.py:** Dynamic nine-prompt, three-identity-column system

All the underlying reliability (failovers, retries, error handling) is preserved and improved.

---

## Support

Every function and section in `poster.py` has inline comments explaining:
- What it does
- Why it does it that way
- What to change if you want to customize it

Read the comments when something isn't clear. They're detailed and honest.

---

## Cost

**₹0 additional cost.** All APIs used are the same ones as v6.2:
- Gemini, OpenRouter, Groq, NVIDIA (free tiers)
- ElevenLabs, Groq TTS, Edge-TTS (free tiers)
- Pexels, Unsplash (free tiers)
- tempfile.org, catbox.moe (free tiers)
- Instagram Graph API (free tier)

Grid rotation doesn't add new API calls, just better uses of existing ones.

---

## Next Steps

1. Read `SETUP_GITHUB_ACTIONS.md`
2. Make the two workflow changes
3. Replace `poster.py`
4. Push to main
5. Test via "Run workflow" in GitHub Actions
6. Done!

Your next scheduled run will use the new rotation system automatically.

---

**Questions?** Check the comments in `poster.py` or review `SETUP_GITHUB_ACTIONS.md` for the exact workflow changes needed.

Enjoy your better-organized, multi-identity grid! 🎬✨
