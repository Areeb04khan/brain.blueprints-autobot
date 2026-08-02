# Quick Customization Guide

All changes go in `poster.py`. Find the section, edit, commit, and the next `workflow_dispatch` run will use your changes.

---

## Speech Speed & Prosody (TTS)

**File:** `poster.py`, function `_wrap_script_in_ssml()`

### Speech too slow?
```python
# OLD (current):
ssml += f'<s><prosody rate="0.85" pitch="-5%">{sentence}</prosody></s>'

# FASTER:
ssml += f'<s><prosody rate="0.95" pitch="-5%">{sentence}</prosody></s>'
```

**Rate scale:**
- `0.7` = very slow (like explaining something complex)
- `0.85` = moderate (current default, good for learning content)
- `0.95` = natural/conversational
- `1.0` = normal TTS speed (slightly robotic, no adjustment)
- `1.1` = fast/energetic
- `1.2` = very fast (use for transitions only)

### Speech too high/low pitch?
```python
# OLD (current):
pitch="-5%"

# Options:
pitch="0%"       # neutral/normal pitch
pitch="-10%"     # lower (more authoritative)
pitch="+10%"     # higher (more expressive/energetic)
```

### Pauses too long/short?
```python
# OLD (current):
ssml += '<break time="400ms"/>'

# Shorter pauses:
ssml += '<break time="200ms"/>'

# Longer pauses:
ssml += '<break time="600ms"/>'
```

**Pause timing:**
- `150-200ms` = barely noticeable, quick pacing
- `300-400ms` = natural conversational pause
- `600-800ms` = emphasis/dramatic pause

---

## Visual Layout (Colors, Fonts, Sizing)

**File:** `poster.py`, function `create_reel_video()`

### Main Title Color
```python
# OLD (current):
draw.text((540, 80), main_title, font=font_header, fill="#FFD700", anchor="mm", align="center")
                                                       # ^^^^^^
                                                      # golden

# Change to:
fill="#FF1493"    # Deep pink
fill="#00FF00"    # Lime green
fill="#FFFFFF"    # White
fill="#FF6B9D"    # Magenta
```

### Column Divider Color/Thickness
```python
# OLD (current):
draw.line([(divider_x, 120), (divider_x, 1750)], fill=(180, 140, 60), width=3)
                                                      #RGB values    width^

# Thicker dividers:
width=5

# Different color (RGB):
fill=(255, 215, 0)      # Gold
fill=(255, 20, 147)     # Deep pink
fill=(100, 149, 237)    # Cornflower blue
fill=(50, 205, 50)      # Lime green
```

### Column Angle Names (e.g., "Submissive", "Dominant")
```python
# OLD (current):
draw.text((x_center, y_pos), angle_name, font=font_subtitle, fill="#FF6B9D", anchor="mm", align="center")
                                                                  # ^^^^^^
                                                                 # magenta

# Change color:
fill="#FFD700"    # Gold (same as title)
fill="#FFFFFF"    # White
fill="#00FF00"    # Green
```

### Detail Text (behavior descriptions)
```python
# OLD (current):
draw.text((x_center, y_pos), detail_wrapped, font=font_body, fill="#E0E0E0", anchor="mm", align="center")
                                                                # ^^^^^^
                                                              # light gray

# Change color:
fill="#FFFFFF"    # White (brighter)
fill="#CCCCCC"    # Medium gray (darker)
fill="#FFFF00"    # Yellow (high contrast)
```

### Example Text (the 💡 bullet points)
```python
# OLD (current):
draw.text((x_center, y_pos), f"💡 {example_wrapped}", font=font_body, fill="#A0D8A0", anchor="mm", align="center")
                                                                          # ^^^^^^
                                                                         # green

# Change color:
fill="#FF9999"    # Light red (warning/important)
fill="#99CCFF"    # Light blue (cool/info)
fill="#FFCC99"    # Light orange (highlight)
fill="#FFFFFF"    # White (neutral)
```

### Font Sizes
```python
# OLD (current):
font_header = ImageFont.truetype(FONT_SANS, 32)      # main title
font_title = ImageFont.truetype(FONT_SANS, 28)       # column labels
font_subtitle = ImageFont.truetype(FONT_SANS, 20)    # angle names
font_body = ImageFont.truetype(FONT_SANS, 18)        # details & examples
font_brand = ImageFont.truetype(FONT_SANS, 24)       # @brain.blueprints

# Bigger:
font_header = ImageFont.truetype(FONT_SANS, 40)      # make title bigger
font_subtitle = ImageFont.truetype(FONT_SANS, 24)    # make angle names bigger

# Smaller:
font_body = ImageFont.truetype(FONT_SANS, 16)        # fit more text
```

### Background Darkness
```python
# OLD (current) - darkens background video by 70%:
bg_clip = bg_clip.fl_image(lambda image: (image * 0.30).astype(np.uint8))
                                           # 0.30 means 30% brightness ^

# Less dark (brighter background):
bg_clip = bg_clip.fl_image(lambda image: (image * 0.50).astype(np.uint8))
                                           # 0.50 = 50% brightness

# Very dark:
bg_clip = bg_clip.fl_image(lambda image: (image * 0.20).astype(np.uint8))
                                           # 0.20 = 20% brightness (very dark)
```

---

## Content Prompt (What the AI Generates)

**File:** `poster.py`, function `generate_content()`

The `prompt` variable is what tells the AI what to generate. It's long and specific. Here's what you can customize:

### Topic Focus
Currently: "behavioral psychologist and social strategist"

```python
# Change to:
# "You are an expert neuroscientist..."
# "You are a master of persuasion..."
# "You are a body language expert..."
```

### Content Theme
Currently: Focused on dominance signals, social hierarchy, reading people

```python
# Change the example in the prompt from:
"title": "Core concept in 2-3 words (e.g., 'Dominance Signals', 'Micro-Expressions', 'Social Proof')"

# To other topics:
# 'Manipulation Tactics', 'Memory Tricks', 'Sleep Science', 'Decision Making', etc.
```

### Script Length
Currently: "A 12-15 second script"

```python
# Make longer:
"A 20-25 second script"

# Make shorter:
"An 8-10 second script"
```

### Tone
Currently: Educational, specific, no fluff

```python
# Add this line to the prompt if you want:
"Make it more entertaining and humorous while staying educational."
# OR
"Make it more serious and authoritative."
# OR
"Make it more casual and conversational."
```

---

## Keyboard Shortcut Reference

**To test your changes:**

1. Edit `poster.py`
2. Commit and push to GitHub
3. Go to GitHub Actions tab → "Brain Blueprints Reel Automation" → "Run workflow"
4. Click "Run workflow" → it runs immediately with your changes
5. Check the log to see how your changes look

No need to wait for the scheduled runs (7 AM, 2 PM, 10 PM) — you can test instantly.

---

## Common Tweaks (Copy-Paste Ready)

### Make everything brighter/whiter text
```python
# Change these lines (search for `fill="#` in create_reel_video):
fill="#FF6B9D"   →  fill="#FFFFFF"      # angle names: magenta → white
fill="#E0E0E0"   →  fill="#FFFFFF"      # details: light gray → white
fill="#A0D8A0"   →  fill="#FFFFFF"      # examples: green → white
```

### Make speech slower and more authoritative
```python
# In _wrap_script_in_ssml(), change:
rate="0.85"  →  rate="0.75"   # slower
pitch="-5%"  →  pitch="-15%"  # lower voice
```

### Bigger title, smaller details
```python
# In create_reel_video():
font_header = ImageFont.truetype(FONT_SANS, 32)  →  40
font_body = ImageFont.truetype(FONT_SANS, 18)    →  16
```

### More contrast (darker background + whiter text)
```python
# Old background darkening line:
bg_clip = bg_clip.fl_image(lambda image: (image * 0.30).astype(np.uint8))

# Change to (even darker):
bg_clip = bg_clip.fl_image(lambda image: (image * 0.15).astype(np.uint8))

# And change text colors to all white:
fill="#FFFFFF"   # for all text elements
```

---

## Testing Without Running the Full Workflow

If you want to test just the SSML generation:

```bash
# In a Python shell with poster.py loaded:
import sys
sys.path.insert(0, '/path/to/repo')
from poster import _wrap_script_in_ssml

script = "Watch how this works. First, the basic level. Details here. Example here."
ssml = _wrap_script_in_ssml(script)
print(ssml)
# Look for <prosody> tags and <break> pauses
```

If you want to test the three-column layout rendering (without TTS/video):

```bash
# Just look at the generated PNG overlay file in the output/ directory
# After a run completes, check: output/overlay_*.png
```

---

## Colors Cheat Sheet

**Web Color Names (copy-paste as `fill="NAME"`:**
```
#FFFFFF  - White
#000000  - Black
#FFD700  - Gold
#FF6B9D  - Magenta/Pink
#A0D8A0  - Light green
#E0E0E0  - Light gray
#FF1493  - Deep pink
#00FF00  - Lime green
#FF9999  - Light red
#99CCFF  - Light blue
#FFCC99  - Light orange
#FFD700  - Golden
#C0C0C0  - Silver
```

**Or use RGB tuples (copy-paste as `fill=(R,G,B)`:**
```
(255, 255, 255)  - White
(0, 0, 0)        - Black
(255, 215, 0)    - Gold
(255, 20, 147)   - Deep pink
(100, 149, 237)  - Cornflower blue
(50, 205, 50)    - Lime green
(255, 200, 124)  - Light orange
```

---

## Still Stuck?

The code has comments explaining every section. Search for:
- `# Color:` → look for fill= changes
- `# Font:` → look for font= size changes
- `# SSML:` → look for prosody/break changes
- `# Prompt:` → look for AI instruction changes

Good luck! 🎨
