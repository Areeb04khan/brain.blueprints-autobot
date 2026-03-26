"""
Shayari Instagram Bot v4.2
- Real authentic Shayari
- Emotion-driven dark visuals
- 1:1 (1080x1080) for photos, 9:16 (1080x1920) for Reels
- catbox.moe for video hosting
- Edge TTS for voiceover (free, no API key)
- No Urdu script on image — Roman + English only

FIXES in v4.2:
1. Duplicate shayari fix — photo saves generated content to progress.json,
   reel loads and reuses it instead of calling Gemini again. Same sher, same
   caption for both posts of the same day.
2. Posting time fix — post type is no longer detected from the clock (unreliable
   due to GitHub Actions queue delays). Each cron trigger now sets POST_TYPE
   explicitly in the workflow via separate jobs. Clock detection removed entirely.
3. Format updated — "one-liner" renamed to "four-liner" everywhere (prompt + map).
"""

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
import base64

# How many times to retry on transient failures before giving up
MAX_RETRIES = 3
RETRY_DELAY = 3600  # 1 hour in seconds

def is_retryable_error(e):
    """Returns True for network/server errors worth retrying, False for code bugs."""
    msg = str(e).lower()
    return any(k in msg for k in [
        "503", "unavailable", "timeout", "connection",
        "temporarily", "rate limit", "internal error",
        "catbox", "upload failed"
    ])

# ============================================================
# CONFIGURATION — all values come from GitHub Actions secrets
# ============================================================
GEMINI_API_KEY         = os.environ.get("GEMINI_API_KEY", "")
INSTAGRAM_ACCESS_TOKEN = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
INSTAGRAM_USER_ID      = os.environ.get("INSTAGRAM_USER_ID", "")
IMGBB_API_KEY          = os.environ.get("IMGBB_API_KEY", "")
POST_TYPE              = os.environ.get("POST_TYPE", "photo")  # "photo" or "reel"
IG_HANDLE              = "@ak_apak"

# DejaVu fonts — installed via apt-get in the workflow
FONT_SERIF  = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
FONT_ITALIC = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf"
FONT_SANS   = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

# ============================================================
# POET SCHEDULE — 30 days per poet, cycles through all poets
# ============================================================
# ============================================================
# POET SCHEDULE — 1 poet per day, cycles through entire list
# Mix of prominent (for traction) + lesser-known (for discovery)
# Categories: Classical Urdu, Freedom era, Bollywood, Modern,
#             Hindi poets, and obscure/rare voices
# Add new poets freely at the bottom — the bot picks up automatically
# ============================================================
POET_SCHEDULE = [
    # ── CLASSICAL URDU (pre-1900) ──────────────────────────────
    {"name": "Mirza Ghalib",          "era": "1797-1869"},  # most followed
    {"name": "Mir Taqi Mir",          "era": "1723-1810"},  # Khuda-e-Sukhan
    {"name": "Mir Dard",              "era": "1721-1785"},  # Sufi mysticism
    {"name": "Sauda",                 "era": "1713-1781"},  # satirical genius
    {"name": "Insha Allah Khan Insha","era": "1756-1817"},  # witty & playful
    {"name": "Momin Khan Momin",      "era": "1800-1852"},  # romantic rival of Ghalib
    {"name": "Zauq",                  "era": "1788-1854"},  # royal court poet
    {"name": "Dagh Dehlvi",           "era": "1831-1905"},  # last Mughal-era master
    {"name": "Amir Minai",            "era": "1828-1900"},  # mushaira favourite
    {"name": "Ameer Khusrau",         "era": "1253-1325"},  # Sufi, oldest voice

    # ── FREEDOM ERA & PROGRESSIVE (1900-1960) ──────────────────
    {"name": "Allama Iqbal",          "era": "1877-1938"},  # Shikwa, Jawab-e-Shikwa
    {"name": "Faiz Ahmed Faiz",       "era": "1911-1984"},  # resistance poetry
    {"name": "Habib Jalib",           "era": "1928-1993"},  # voice of the oppressed
    {"name": "Josh Malihabadi",       "era": "1898-1982"},  # Shair-e-Inquilab
    {"name": "Firaq Gorakhpuri",      "era": "1896-1982"},  # Sahitya Akademi winner
    {"name": "Jigar Moradabadi",      "era": "1890-1960"},  # Ishq aur Masti
    {"name": "Fani Badayuni",         "era": "1879-1941"},  # profound pessimism
    {"name": "Hasrat Mohani",         "era": "1875-1951"},  # coined Inquilab Zindabad
    {"name": "Asrar ul Haq Majaz",    "era": "1911-1955"},  # Awaara, tragic life
    {"name": "Ali Sardar Jafri",      "era": "1913-2000"},  # progressive movement
    {"name": "Kaifi Azmi",            "era": "1919-2002"},  # poet + activist
    {"name": "Jan Nisar Akhtar",      "era": "1914-1976"},  # lyrical depth
    {"name": "Makhdoom Mohiuddin",    "era": "1908-1969"},  # Telugu-Urdu voice
    {"name": "Sahir Ludhianvi",       "era": "1921-1980"},  # Bollywood immortal

    # ── BOLLYWOOD LYRICISTS ─────────────────────────────────────
    {"name": "Gulzar",                "era": "1934-"    },  # still writing
    {"name": "Javed Akhtar",          "era": "1945-"    },  # Sholay to today
    {"name": "Shailendra",            "era": "1923-1966"},  # Awaara Hoon
    {"name": "Majrooh Sultanpuri",    "era": "1919-2000"},  # longest career
    {"name": "Shakeel Badayuni",      "era": "1916-1970"},  # Mughal-e-Azam
    {"name": "Anand Bakshi",          "era": "1930-2002"},  # everyman's poet

    # ── MODERN URDU (post-1947) ─────────────────────────────────
    {"name": "Ahmad Faraz",           "era": "1931-2008"},  # Ranjish hi sahi
    {"name": "Parveen Shakir",        "era": "1952-1994"},  # feminist voice
    {"name": "Munir Niazi",           "era": "1928-2006"},  # minimalist mystic
    {"name": "Qateel Shifai",         "era": "1919-2001"},  # Hum tere shahar mein
    {"name": "Ibn-e-Insha",           "era": "1927-1978"},  # satirical & lyrical
    {"name": "Zehra Nigah",           "era": "1936-"    },  # finest living poet
    {"name": "Amjad Islam Amjad",     "era": "1944-"    },  # Urdu TV & poetry
    {"name": "Iftikhar Arif",         "era": "1944-"    },  # mystical depth
    {"name": "Kishwar Naheed",        "era": "1940-"    },  # feminist resistance
    {"name": "Sara Shagufta",         "era": "1954-1984"},  # raw, tragic, real
    {"name": "Fehmida Riaz",          "era": "1946-2018"},  # bold feminist
    {"name": "Nasir Kazmi",           "era": "1925-1972"},  # grief & longing
    {"name": "Mustafa Zaidi",         "era": "1930-1970"},  # Kohsar mein ek Sholay
    {"name": "Faraz",                 "era": "1931-2008"},  # alias for Ahmad Faraz

    # ── CONTEMPORARY (living / recent) ─────────────────────────
    {"name": "Rahat Indori",          "era": "1950-2020"},  # viral mushaira king
    {"name": "Wasi Shah",             "era": "1977-"    },  # modern romance
    {"name": "Bashir Badr",           "era": "1935-"    },  # simplest deepest
    {"name": "Munawwar Rana",         "era": "1952-2024"},  # Maa poetry
    {"name": "Nida Fazli",            "era": "1938-2016"},  # Dushman na kare
    {"name": "Anwar Masood",          "era": "1935-"    },  # Punjabi-Urdu wit
    {"name": "Jaun Elia",             "era": "1931-2002"},  # nihilistic legend
    {"name": "Piyush Mishra",         "era": "1963-"    },  # theatre to films
    {"name": "Irshad Kamil",          "era": "1972-"    },  # Rockstar, Tamasha
    {"name": "Swanand Kirkire",       "era": "1973-"    },  # Lagaan to Barfi
    {"name": "Prasoon Joshi",         "era": "1971-"    },  # Rang De Basanti

    # ── HINDI POETS ────────────────────────────────────────────
    {"name": "Kumar Vishwas",         "era": "1970-"    },  # viral Hindi shayar
    {"name": "Harivansh Rai Bachchan","era": "1907-2003"},  # Madhushala
    {"name": "Mahadevi Varma",        "era": "1907-1987"},  # Chhayavaad icon
    {"name": "Suryakant Tripathi Nirala","era":"1899-1961"},# rebel of Hindi poetry
    {"name": "Sumitranandan Pant",    "era": "1900-1977"},  # nature & beauty
    {"name": "Ramdhari Singh Dinkar", "era": "1908-1974"},  # Rashmirathi, Kurukshetra
    {"name": "Shyam Narayan Pandey",  "era": "1907-1991"},  # Haldighati epic
    {"name": "Dushyant Kumar",        "era": "1933-1975"},  # Hindi ghazal pioneer
    {"name": "Gopaldas Neeraj",       "era": "1925-2018"},  # Ae Bhai Zara
    {"name": "Kunwar Narayan",        "era": "1927-2017"},  # Jnanpith winner
    {"name": "Kedarnath Singh",       "era": "1934-2018"},  # Sahitya Akademi
    {"name": "Manglesh Dabral",       "era": "1948-2020"},  # working-class voice

    # ── OBSCURE & RARE VOICES ───────────────────────────────────
    {"name": "Meer Anees",            "era": "1803-1874"},  # marsiya master
    {"name": "Mirza Dabeer",          "era": "1803-1875"},  # rival of Anees
    {"name": "Hafeez Jalandhari",     "era": "1900-1982"},  # wrote Pak anthem
    {"name": "Noon Meem Rashid",      "era": "1910-1975"},  # modernist rebel
    {"name": "Meeraji",               "era": "1912-1949"},  # avant-garde outsider
    {"name": "Majid Amjad",           "era": "1914-1974"},  # unrecognised master
    {"name": "Ahmed Nadeem Qasmi",    "era": "1916-2006"},  # short story + poetry
    {"name": "Saadat Hasan Manto",    "era": "1912-1955"},  # prose-poet of pain
    {"name": "Kaifi Dehlvi",          "era": "1860-1955"},  # late classical
    {"name": "Brij Narayan Chakbast", "era": "1882-1926"},  # nationalist Urdu
    {"name": "Seemab Akbarabadi",     "era": "1882-1951"},  # prolific ghazals
    {"name": "Jigarr Badayuni",       "era": "1880-1940"},  # mystical obscure
    {"name": "Himayat Ali Shair",     "era": "1926-2011"},  # Pakistani modernist
    {"name": "Ahmad Mushtaq",         "era": "1934-"    },  # quiet genius
    {"name": "Zafar Iqbal",           "era": "1933-"    },  # experimental ghazal
    {"name": "Shahryar",              "era": "1936-2012"},  # Umrao Jaan, Gaman
    {"name": "Jamiluddin Aali",       "era": "1926-2015"},  # Jeevey Jeevey Pak
    {"name": "Sufi Tabassum",         "era": "1899-1978"},  # children + deep Urdu
]

# ============================================================
# FORMAT SELECTION — weighted random per run
# Bias: four-liner (40%) and longer (35%) dominate.
# Couplet (20%) occasional. One-liner (5%) only for truly
# self-sufficient, iconic single-line shers.
# No FORMAT_MAP needed — format picked fresh each run.
# ============================================================
import random as _random

FORMAT_WEIGHTS = [
    ("four-liner", 40),  # 4 lines — most common, fits image well
    ("longer",     35),  # 6-8 lines from a real ghazal/nazm
    ("couplet",    20),  # 2 lines — used occasionally
    ("one-liner",   5),  # 1 misra — ONLY for iconic self-sufficient lines
]

def get_format(_day=None):
    """Pick a format randomly with weighted bias toward four-liner and longer."""
    formats, weights = zip(*FORMAT_WEIGHTS)
    return _random.choices(formats, weights=weights, k=1)[0]

# ============================================================
# EMOTION → DARK COLOR PALETTES
# bg=background, text=sher text, accent=highlights, sub=secondary, border=frame
# ============================================================
EMOTION_PALETTES = {
    "ishq":     {"bg":"#1a0010","text":"#f5c6d0","accent":"#e8587a","sub":"#b03060","border":"#8b1a3a"},
    "dard":     {"bg":"#0a0a1a","text":"#c8d4e8","accent":"#7090d0","sub":"#405080","border":"#2a3a6a"},
    "tanhai":   {"bg":"#060d0d","text":"#b8d8d8","accent":"#40a0a0","sub":"#206060","border":"#104040"},
    "intezaar": {"bg":"#0f0f0f","text":"#e0d8c8","accent":"#c8a860","sub":"#806030","border":"#503810"},
    "gussa":    {"bg":"#1a0500","text":"#f0c8a0","accent":"#e06020","sub":"#903010","border":"#601800"},
    "falsafa":  {"bg":"#080818","text":"#d0c8e8","accent":"#9070c0","sub":"#504080","border":"#302060"},
    "umeed":    {"bg":"#060f06","text":"#c0e0c0","accent":"#50b050","sub":"#306030","border":"#184018"},
    "yaad":     {"bg":"#120c04","text":"#e8d8b0","accent":"#c09040","sub":"#806020","border":"#503810"},
    "zindagi":  {"bg":"#0a0a14","text":"#d0d0e8","accent":"#8080c0","sub":"#404080","border":"#202050"},
    "maut":     {"bg":"#050505","text":"#c0c0c0","accent":"#808080","sub":"#404040","border":"#202020"},
}
DEFAULT_PALETTE = EMOTION_PALETTES["dard"]

# ============================================================
# HASHTAGS
# ============================================================
BASE_HASHTAGS = ["shayari","urdupoetry","hindishayari",
                 "shayarilover","urdushayari","shayarioftheday"]

POET_HASHTAGS = {
    "Mirza Ghalib":       ["mirzaghalib","ghalib","ghalibishayari"],
    "Faiz Ahmed Faiz":    ["faizahmedfaiz","faizshayari","faiz"],
    "Allama Iqbal":       ["allamaiqbal","iqbal","iqbalshayari"],
    "Mir Taqi Mir":       ["mirtaqimir","mir","klassicalurdu"],
    "Ahmad Faraz":        ["ahmadfaraz","faraz","farazshayari"],
    "Parveen Shakir":     ["parveenshakir","shakir","urdupoetess"],
    "Sahir Ludhianvi":    ["sahirludhianvi","sahir","sahirshayari"],
    "Gulzar":             ["gulzar","gulzarshayari","gulzarsahab"],
    "Rahat Indori":       ["rahatindori","rahat","rahatshayari"],
    "Habib Jalib":        ["habibjalib","jalib","jalibshayari"],
    "Wasi Shah":          ["wasishah","wasi","modernurdu"],
    "Josh Malihabadi":    ["joshmalihabadi","josh","joshpoetry"],
    "Javed Akhtar":       ["javedakhtar","javed","javedakhtarshayari"],
    "Kumar Vishwas":      ["kumarvishwas","kumar","vishwasshayari"],
    "Munawwar Rana":      ["munawwarrana","rana","munawwarshayari"],
    "Bashir Badr":        ["bashirbadr","badr","bashirbadrsher"],
    "Nida Fazli":         ["nidafazli","fazli","nidafazlisher"],
    "Anwar Masood":       ["anwarmasood","masood","anwarmasoodshayari"],
    "Amjad Islam Amjad":  ["amjadislamamjad","amjad","amjadshayari"],
    "Zehra Nigah":        ["zehranigah","nigah","zehranigahpoetry"],
}

TAG_TRIGGERS = [
    "Kise tag karoge jo yeh dard samajhta ho?",
    "Aapki zindagi mein kab aaya tha aisa waqt?",
    "Pehli baar padhke kya feel hua? Comments mein batao.",
    "Yeh sher kisi ko dedicate karna chahte ho?",
    "Kaun sa lafz sabse zyada dil ko chhu gaya?",
    "Aaj ke waqt mein bhi kitna sach lagta hai — sochna.",
]


# ============================================================
# STEP 1: Generate Shayari content via Gemini
# ============================================================
def generate_content(poet: dict, fmt: str) -> dict:
    client      = genai.Client(api_key=GEMINI_API_KEY)
    tag_trigger = TAG_TRIGGERS[_random.randint(0, len(TAG_TRIGGERS)-1)]

    prompt = f"""You run a premium Instagram Shayari account dedicating 30 days to one poet.
Today's poet: {poet['name']} ({poet['era']})

RULES:
1. Quote a REAL, AUTHENTIC sher by {poet['name']} — NOT AI generated, NOT paraphrased.
   It must be verifiable — from a known diwan, collection, or mushaira recording.
2. Format today: {fmt}
   one-liner  = 1 misra ONLY — use this ONLY if the line is completely self-sufficient
                and iconic on its own. Do NOT force it for ordinary lines.
   four-liner = exactly 4 lines (2 back-to-back couplets from the same ghazal)
   couplet    = exactly 2 lines (one complete sher)
   longer     = 6-8 lines from a real ghazal/nazm (3-4 connected couplets)
   IMAGE RULE: Total Roman Urdu lines must stay under 8. If the sher is longer,
               pick a shorter extract. Do NOT let text overflow the image.
3. Roman Urdu transliteration of the sher only (for sher_roman)
4. Urdu script of the sher (for sher_urdu — used for TTS pronunciation)
5. English translation: MAX 1 LINE. Poetic, not literal.
6. Source collection if known (e.g. Diwan-e-Ghalib)

EMOTION: pick one from [ishq, dard, intezaar, yaad, tanhai, gussa, falsafa, umeed, zindagi, maut]

COLORS (dark backgrounds only):
bg_color: very dark hex matching emotion
text_color: soft light hex
accent_color: vivid accent hex

CAPTION:
Line 1 - HOOK: Start mid-thought, never start with poet name. Instant curiosity.
Line 2-3 - STORY: Real intimate fact about poet's life tied to this sher.
Line 4 - GHAZAL: If from ghazal, include 2-3 more real couplets labeled clearly.
Line 5 - TAG TRIGGER (copy exactly): "{tag_trigger}"

Return ONLY valid JSON, no markdown, no backticks:
{{
  "sher_roman": "...",
  "sher_urdu": "...",
  "english_translation": "...",
  "source": "...",
  "emotion": "...",
  "bg_color": "#...",
  "text_color": "#...",
  "accent_color": "#...",
  "format": "{fmt}",
  "caption": "...",
  "extra_hashtags": ["tag1","tag2","tag3"]
}}"""

    response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    # Strip any markdown code fences Gemini might wrap around JSON
    raw = response.text.strip().replace("```json","").replace("```","").strip()
    return json.loads(raw)


# ============================================================
# HELPERS: decorative border, divider diamond, and dot texture
# ============================================================
def draw_border(draw, p, W, H):
    """Three nested rectangles with diamond corner ornaments."""
    draw.rectangle([20,20,W-20,H-20], outline=p["border"], width=2)
    draw.rectangle([32,32,W-32,H-32], outline=p["border"], width=1)
    draw.rectangle([40,40,W-40,H-40], outline=p["accent"],  width=1)
    # Diamond ornaments at each corner
    for cx,cy in [(20,20),(W-20,20),(20,H-20),(W-20,H-20)]:
        s=10
        draw.polygon([(cx,cy-s),(cx+s,cy),(cx,cy+s),(cx-s,cy)], fill=p["accent"])
        draw.ellipse([cx-3,cy-3,cx+3,cy+3], fill=p["border"])
    # Mid-edge dots
    for mx,my in [(W//2,20),(W//2,H-20),(20,H//2),(W-20,H//2)]:
        draw.ellipse([mx-4,my-4,mx+4,my+4], fill=p["border"])

def draw_divider(draw, cx, cy, color, w=100):
    """Horizontal lines with a central diamond — used between sher and translation."""
    draw.line([(cx-w,cy),(cx-14,cy)], fill=color, width=1)
    draw.line([(cx+14,cy),(cx+w,cy)], fill=color, width=1)
    s=7
    draw.polygon([(cx,cy-s),(cx+s,cy),(cx,cy+s),(cx-s,cy)], outline=color)
    draw.ellipse([cx-2,cy-2,cx+2,cy+2], fill=color)

def add_texture(draw, W, H, accent):
    """Scattered tiny dots for grain/depth effect on dark backgrounds."""
    # Parse accent hex to RGB
    ink = tuple(int(accent[i:i+2],16) for i in (1,3,5))
    for _ in range(600):
        x,y = random.randint(0,W), random.randint(0,H)
        r   = random.randint(0,1)
        # Low alpha dots (4-14) for subtle texture
        draw.ellipse([x-r,y-r,x+r,y+r], fill=(*ink, random.randint(4,14)))


# ============================================================
# STEP 2: Create 1:1 photo image (1080x1080)
# ============================================================
def create_photo_image(data: dict, poet: dict) -> str:
    W, H    = 1080, 1080
    emotion = data.get("emotion","dard").lower()

    # Start from preset palette, then override with Gemini's suggested colors
    palette = dict(EMOTION_PALETTES.get(emotion, DEFAULT_PALETTE))
    for key,field in [("bg","bg_color"),("text","text_color"),("accent","accent_color")]:
        v = data.get(field,"")
        if v and v.startswith("#") and len(v)==7:
            palette[key] = v

    img  = Image.new("RGB",(W,H), color=palette["bg"])
    draw = ImageDraw.Draw(img, "RGBA")  # RGBA mode needed for alpha texture dots
    add_texture(draw, W, H, palette["accent"])
    draw_border(draw, palette, W, H)

    # Load fonts — fall back to default if font files missing
    try:
        font_poet  = ImageFont.truetype(FONT_SERIF,  28)
        font_day   = ImageFont.truetype(FONT_ITALIC, 17)
        font_trans = ImageFont.truetype(FONT_ITALIC, 19)
        font_brand = ImageFont.truetype(FONT_SANS,   16)
        font_src   = ImageFont.truetype(FONT_ITALIC, 15)
    except:
        font_poet=font_day=font_trans=font_brand=font_src=ImageFont.load_default()

    # Sher font size varies by format
    fmt = data.get("format","couplet")
    fs  = 50 if fmt=="one-liner" else (44 if fmt=="couplet" else 38)
    try:    font_sher = ImageFont.truetype(FONT_SERIF, fs)
    except: font_sher = font_poet

    def center(text, y, font, color):
        """Draw text horizontally centered at y position."""
        bbox = draw.textbbox((0,0),text,font=font)
        tw   = bbox[2]-bbox[0]
        draw.text(((W-tw)/2,y), text, font=font, fill=color)

    # --- HEADER SECTION ---
    draw_divider(draw, W//2, 65, palette["accent"], 60)
    center(f"-- {poet['name']} --", 85, font_poet, palette["accent"])
    center(poet["era"], 128, font_day, palette["sub"])
    draw.line([(65,162),(W-65,162)], fill=palette["border"], width=1)

    # --- SHER SECTION — centered vertically in zone 178–720 ---
    lines       = data["sher_roman"].strip().split("\n")
    all_wrapped = []
    for line in lines:
        # Wrap long lines at 36 chars to fit within border
        w2 = textwrap.wrap(line.strip(), width=36)
        all_wrapped.extend(w2 if w2 else [""])  # empty string preserves blank lines

    line_h  = int(fs*1.38)
    total_h = len(all_wrapped)*line_h
    y_pos   = 178 + max(0,(542-total_h)//2)  # vertical center in sher zone
    for wline in all_wrapped:
        center(wline, y_pos, font_sher, palette["text"])
        y_pos += line_h

    # --- DIVIDER between sher and translation ---
    div_y = max(y_pos+20, 730)
    draw_divider(draw, W//2, div_y, palette["accent"])

    # --- TRANSLATION SECTION ---
    trans   = f'"{data["english_translation"]}"'
    tlines  = textwrap.wrap(trans, width=54)
    tlh     = 27
    total_t = len(tlines)*tlh
    y_pos   = div_y+20 + max(0,(130-total_t)//2)
    for line in tlines:
        center(line, y_pos, font_trans, palette["accent"])
        y_pos += tlh

    # Source attribution (e.g. "-- Diwan-e-Ghalib")
    src = data.get("source","")
    if src and src.lower() not in ("unknown",""):
        center(f"-- {src}", y_pos+6, font_src, palette["sub"])

    # --- FOOTER ---
    draw.line([(65,908),(W-65,908)], fill=palette["border"], width=1)
    draw_divider(draw, W//2, 935, palette["accent"], 60)
    center(IG_HANDLE, 962, font_brand, palette["sub"])

    # --- VIGNETTE — dark edges fade inward for cinematic look ---
    vig  = Image.new("RGBA",(W,H),(0,0,0,0))
    vd   = ImageDraw.Draw(vig)
    for i in range(80):
        vd.rectangle([i,i,W-i,H-i], outline=(0,0,0,int(i*1.8)))
    img = img.convert("RGBA")
    img = Image.alpha_composite(img, vig)
    img = img.convert("RGB")

    os.makedirs("output", exist_ok=True)
    fname = f"output/photo_{emotion}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    img.save(fname, "JPEG", quality=95)
    print(f"✅ Photo image: {fname}")
    return fname


# ============================================================
# STEP 3: Create 9:16 reel image (1080x1920)
# ============================================================
def create_reel_image(data: dict, poet: dict) -> str:
    W, H    = 1080, 1920
    emotion = data.get("emotion","dard").lower()
    palette = dict(EMOTION_PALETTES.get(emotion, DEFAULT_PALETTE))
    for key,field in [("bg","bg_color"),("text","text_color"),("accent","accent_color")]:
        v = data.get(field,"")
        if v and v.startswith("#") and len(v)==7:
            palette[key] = v

    img  = Image.new("RGB",(W,H), color=palette["bg"])
    draw = ImageDraw.Draw(img, "RGBA")
    add_texture(draw, W, H, palette["accent"])
    draw_border(draw, palette, W, H)

    # Slightly larger fonts for the taller canvas
    try:
        font_poet  = ImageFont.truetype(FONT_SERIF,  34)
        font_day   = ImageFont.truetype(FONT_ITALIC, 22)
        font_trans = ImageFont.truetype(FONT_ITALIC, 24)
        font_brand = ImageFont.truetype(FONT_SANS,   20)
        font_src   = ImageFont.truetype(FONT_ITALIC, 19)
    except:
        font_poet=font_day=font_trans=font_brand=font_src=ImageFont.load_default()

    fmt = data.get("format","couplet")
    fs  = 62 if fmt=="one-liner" else (54 if fmt=="couplet" else 46)
    try:    font_sher = ImageFont.truetype(FONT_SERIF, fs)
    except: font_sher = font_poet

    def center(text, y, font, color):
        bbox = draw.textbbox((0,0),text,font=font)
        tw   = bbox[2]-bbox[0]
        draw.text(((W-tw)/2,y), text, font=font, fill=color)

    # --- HEADER ---
    draw_divider(draw, W//2, 100, palette["accent"], 80)
    center(f"-- {poet['name']} --", 130, font_poet, palette["accent"])
    center(poet["era"], 185, font_day, palette["sub"])
    draw.line([(80,225),(W-80,225)], fill=palette["border"], width=1)

    # --- SHER — vertically centered in zone 300–1400 ---
    lines       = data["sher_roman"].strip().split("\n")
    all_wrapped = []
    for line in lines:
        w2 = textwrap.wrap(line.strip(), width=34)
        all_wrapped.extend(w2 if w2 else [""])

    line_h  = int(fs*1.4)
    total_h = len(all_wrapped)*line_h
    y_pos   = 300 + max(0,(1100-total_h)//2)
    for wline in all_wrapped:
        center(wline, y_pos, font_sher, palette["text"])
        y_pos += line_h

    # --- DIVIDER ---
    div_y = max(y_pos+40, 1430)
    draw_divider(draw, W//2, div_y, palette["accent"], 120)

    # --- TRANSLATION ---
    trans   = f'"{data["english_translation"]}"'
    tlines  = textwrap.wrap(trans, width=46)
    tlh     = 34
    total_t = len(tlines)*tlh
    y_pos   = div_y+30 + max(0,(200-total_t)//2)
    for line in tlines:
        center(line, y_pos, font_trans, palette["accent"])
        y_pos += tlh

    src = data.get("source","")
    if src and src.lower() not in ("unknown",""):
        center(f"-- {src}", y_pos+10, font_src, palette["sub"])

    # --- FOOTER ---
    draw.line([(80,H-160),(W-80,H-160)], fill=palette["border"], width=1)
    draw_divider(draw, W//2, H-125, palette["accent"], 80)
    center(IG_HANDLE, H-85, font_brand, palette["sub"])

    # --- VIGNETTE ---
    vig = Image.new("RGBA",(W,H),(0,0,0,0))
    vd  = ImageDraw.Draw(vig)
    for i in range(80):
        vd.rectangle([i,i,W-i,H-i], outline=(0,0,0,int(i*1.8)))
    img = img.convert("RGBA")
    img = Image.alpha_composite(img, vig)
    img = img.convert("RGB")

    os.makedirs("output", exist_ok=True)
    fname = f"output/reel_{emotion}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    img.save(fname, "JPEG", quality=95)
    print(f"✅ Reel image: {fname}")
    return fname


# ============================================================
# STEP 4: Edge TTS voiceover — uses Urdu script for pronunciation
# ============================================================
def generate_tts(text: str, output_path: str) -> bool:
    """
    FIX: Now receives sher_urdu (Urdu script) instead of sher_roman.
    Edge TTS pronounces Urdu script far more accurately than Roman transliteration.
    Voice: ur-PK-AsadNeural — male Urdu voice, -15% rate for poetry pacing.
    """
    try:
        import asyncio
        import edge_tts
        VOICE = "ur-PK-AsadNeural"

        async def _speak():
            communicate = edge_tts.Communicate(text, VOICE, rate="-15%", pitch="-5Hz")
            await communicate.save(output_path)

        asyncio.run(_speak())
        print(f"✅ TTS: {output_path}")
        return True
    except Exception as e:
        print(f"❌ TTS error: {e}")
        return False


# ============================================================
# STEP 5: Reel video — Ken Burns zoom + TTS voice + music
# ============================================================
def get_random_music() -> str:
    """Pick a random royalty-free MP3 from the music/ folder."""
    music_dir = "music"
    if not os.path.exists(music_dir):
        return None
    tracks = [f for f in os.listdir(music_dir) if f.endswith(".mp3")]
    if not tracks:
        return None
    chosen = random.choice(tracks)
    print(f"🎵 Music: {chosen}")
    return os.path.join(music_dir, chosen)


def create_reel_video(image_path: str, tts_path: str) -> str:
    """
    Combines the reel image + TTS audio + background music into an MP4.
    Ken Burns effect: slow 4% zoom over the clip duration.
    Music is mixed at 18% volume under the voice.
    """
    try:
        from moviepy.editor import ImageClip, AudioFileClip, CompositeAudioClip
        import numpy as np

        # TTS audio drives the video duration (capped at 59s for Instagram)
        tts_audio = AudioFileClip(tts_path)
        duration  = min(tts_audio.duration + 2, 59)

        # Mix background music under voice
        music_path = get_random_music()
        if music_path:
            music       = AudioFileClip(music_path).subclip(0, duration)
            music       = music.volumex(0.18)        # 18% — subtle background
            tts_audio   = tts_audio.volumex(1.0)     # 100% — voice is primary
            final_audio = CompositeAudioClip([music, tts_audio])
        else:
            final_audio = tts_audio

        # Slow Ken Burns zoom: starts at 100%, ends at 104%
        clip = ImageClip(image_path, duration=duration)
        W, H = clip.size

        def make_frame(t):
            zoom  = 1 + 0.04*(t/duration)  # linear zoom from 1.0 to 1.04
            frame = clip.get_frame(t)
            from PIL import Image as PI
            fi    = PI.fromarray(frame)
            nw,nh = int(W*zoom), int(H*zoom)
            fi    = fi.resize((nw,nh), PI.LANCZOS)
            # Crop back to original size from center
            l,tp  = (nw-W)//2, (nh-H)//2
            fi    = fi.crop((l,tp,l+W,tp+H))
            return np.array(fi)

        video     = clip.fl(lambda gf,t: make_frame(t)).set_audio(final_audio)
        reel_path = image_path.replace(".jpg","_reel.mp4")
        video.write_videofile(
            reel_path, fps=24, codec="libx264",
            audio_codec="aac", verbose=False, logger=None
        )
        print(f"✅ Reel video: {reel_path}")
        return reel_path
    except Exception as e:
        print(f"❌ Reel video failed: {e}")
        return None


# ============================================================
# STEP 6: Upload image to imgbb (photos only — free hosting)
# ============================================================
def upload_image(path: str) -> str:
    """Uploads JPEG to imgbb.com and returns public URL for Instagram API."""
    with open(path,"rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    result = requests.post(
        "https://api.imgbb.com/1/upload",
        data={"key":IMGBB_API_KEY,"image":data}
    ).json()
    if result.get("success"):
        url = result["data"]["url"]
        print(f"✅ Uploaded: {url}")
        return url
    raise Exception(f"imgbb failed: {result}")


# ============================================================
# STEP 7: Upload video to catbox.moe + post as Instagram Reel
# ============================================================
def upload_video_to_catbox(video_path: str) -> str:
    """
    Uploads MP4 to catbox.moe (free, anonymous) and returns public HTTPS URL.
    Instagram's Graph API requires a publicly accessible video URL.
    """
    with open(video_path,"rb") as f:
        result = requests.post(
            "https://catbox.moe/user/api.php",
            data={"reqtype": "fileupload", "userhash": ""},
            files={"fileToUpload": f}
        )
    url = result.text.strip()
    if url.startswith("https://"):
        print(f"✅ Video hosted: {url}")
        return url
    raise Exception(f"catbox upload failed: {result.text}")


def upload_video_to_instagram(video_path: str, caption: str) -> bool:
    """
    3-step Instagram Reels upload:
    1. Upload MP4 to catbox.moe for public URL
    2. Create media container (Instagram processes video asynchronously)
    3. Poll for FINISHED status, then publish
    """
    print("☁️  Uploading video to catbox.moe...")
    video_url = upload_video_to_catbox(video_path)

    # Step 1: Create Reels media container
    container = requests.post(
        f"https://graph.instagram.com/v21.0/{INSTAGRAM_USER_ID}/media",
        data={
            "media_type":   "REELS",
            "video_url":    video_url,
            "caption":      caption,
            "access_token": INSTAGRAM_ACCESS_TOKEN,
        }
    ).json()

    if "id" not in container:
        print(f"❌ Reel container failed: {container}")
        return False

    print(f"✅ Reel container created: {container['id']}")

    # Step 2: Poll for processing completion (up to 15 x 10s = 150s)
    for attempt in range(15):
        time.sleep(10)
        status = requests.get(
            f"https://graph.instagram.com/v21.0/{container['id']}",
            params={"fields":"status_code","access_token":INSTAGRAM_ACCESS_TOKEN}
        ).json()
        sc = status.get("status_code","")
        print(f"   [{attempt+1}/15] Status: {sc}")
        if sc == "FINISHED":
            break
        if sc == "ERROR":
            print(f"❌ Instagram processing error: {status}")
            return False

    # Step 3: Publish the processed container
    publish = requests.post(
        f"https://graph.instagram.com/v21.0/{INSTAGRAM_USER_ID}/media_publish",
        data={
            "creation_id":  container["id"],
            "access_token": INSTAGRAM_ACCESS_TOKEN,
        }
    ).json()

    if "id" in publish:
        print(f"🎉 Reel posted! ID: {publish['id']}")
        return True

    print(f"❌ Reel publish failed: {publish}")
    return False


# ============================================================
# STEP 8: Post photo via Instagram Graph API
# ============================================================
def post_photo(image_url: str, caption: str) -> bool:
    """
    2-step photo upload:
    1. Create media container with image URL
    2. Publish container
    """
    container = requests.post(
        f"https://graph.instagram.com/v21.0/{INSTAGRAM_USER_ID}/media",
        data={
            "image_url":    image_url,
            "caption":      caption,
            "access_token": INSTAGRAM_ACCESS_TOKEN
        }
    ).json()
    if "id" not in container:
        print(f"❌ Container failed: {container}")
        return False
    print(f"✅ Container: {container['id']}")
    time.sleep(5)  # Brief wait before publishing
    publish = requests.post(
        f"https://graph.instagram.com/v21.0/{INSTAGRAM_USER_ID}/media_publish",
        data={
            "creation_id":  container["id"],
            "access_token": INSTAGRAM_ACCESS_TOKEN
        }
    ).json()
    if "id" in publish:
        print(f"🎉 Photo posted! ID: {publish['id']}")
        return True
    print(f"❌ Publish failed: {publish}")
    return False


# ============================================================
# STEP 9: Build Instagram caption with hashtags + disclaimer
# ============================================================
def build_caption(data: dict, poet: dict) -> str:
    poet_tags  = POET_HASHTAGS.get(poet["name"],[])
    extra_tags = data.get("extra_hashtags",[])
    # Max 9 hashtags: 6 base + 2 poet-specific + 1 AI-suggested
    all_tags   = BASE_HASHTAGS + poet_tags[:2] + extra_tags[:1]
    hashtags   = " ".join([f"#{t}" for t in all_tags[:9]])
    disclaimer = "⚠️ No copyright infringement intended. All rights belong to the original poet/publisher. Shared for cultural & educational purposes only."
    return f"{data['caption']}\n\n{hashtags}\n\n{disclaimer}"


# ============================================================
# PROGRESS TRACKING — persisted in progress.json (committed to repo)
# ============================================================
def load_progress() -> dict:
    """
    Loads progress.json. If file doesn't exist (fresh clone), returns defaults.
    setdefault() ensures old progress.json files without new fields still work.
    """
    if os.path.exists("progress.json"):
        with open("progress.json") as f:
            data = json.load(f)
    else:
        data = {"poet_index":0, "total_posts":0}

    # FIX: Ensure new fields always exist — prevents KeyError on old progress.json
    data.setdefault("last_post_date", "")
    data.setdefault("last_post_type", "")
    data.setdefault("status", "")

    return data


def save_progress(p: dict):
    """Writes full progress dict to progress.json. Always writes ALL fields."""
    with open("progress.json","w") as f:
        json.dump(p, f, indent=2)


def already_posted_today(post_type: str) -> bool:
    """
    Duplicate-post guard: returns True if we already successfully posted
    this post_type today (based on UTC date in progress.json).
    Prevents double-posts if the workflow is manually re-triggered.
    """
    p     = load_progress()
    today = datetime.utcnow().strftime("%Y-%m-%d")
    return (
        p.get("last_post_date") == today and
        p.get("last_post_type") == post_type and
        p.get("status")         == "success"
    )


# ============================================================
# MAIN RUN LOGIC
# ============================================================
def run():
    print(f"\n{'='*55}")
    print(f"Shayari Bot v4.2 | {datetime.now().strftime('%Y-%m-%d %H:%M')} | {POST_TYPE.upper()}")
    print(f"{'='*55}")

    p          = load_progress()
    poet_index = p["poet_index"] % len(POET_SCHEDULE)
    poet       = POET_SCHEDULE[poet_index]
    fmt        = get_format()  # weighted random format for today

    print(f"Poet: {poet['name']} ({poet['era']}) | Format: {fmt} | Type: {POST_TYPE}")

    # --- GENERATE OR LOAD CONTENT ---
    # FIX: Reel reuses the same content generated by the morning photo post.
    # This prevents Gemini generating a different sher for the reel.
    # Photo saves "today_content" to progress.json after posting.
    # Reel loads it: same sher, same caption, different visual (9:16 vs 1:1).
    # Fallback: if today_content missing, generate fresh (reel triggered manually).
    if POST_TYPE == "reel" and p.get("today_content"):
        print("Loading today's sher from photo post (reusing for reel)...")
        data = p["today_content"]
    else:
        print("Generating authentic Shayari via Gemini...")
        data = generate_content(poet, fmt)

    caption = build_caption(data, poet)
    print(f"   Emotion: {data.get('emotion')} | Source: {data.get('source','unknown')}")
    print(f"   Sher (Roman): {data.get('sher_roman','')[:60]}...")

    # --- POST PHOTO ---
    if POST_TYPE == "photo":
        print("Creating 1:1 photo image (1080x1080)...")
        image_path = create_photo_image(data, poet)
        image_url  = upload_image(image_path)
        success    = post_photo(image_url, caption)

    # --- POST REEL ---
    elif POST_TYPE == "reel":
        print("Creating 9:16 reel image (1080x1920)...")
        reel_image = create_reel_image(data, poet)

        # FIX: Use sher_urdu for TTS — correct pronunciation vs Roman transliteration
        tts_text   = data.get("sher_urdu") or data["sher_roman"]
        audio_path = reel_image.replace(".jpg", ".mp3")

        print("Generating TTS voiceover (Urdu script)...")
        has_audio = generate_tts(tts_text, audio_path)

        if has_audio:
            print("Creating Reel video (Ken Burns + music)...")
            reel_path = create_reel_video(reel_image, audio_path)
        else:
            # Fallback: silent 15-second video via ffmpeg
            print("TTS failed — creating silent Reel via ffmpeg...")
            reel_path = reel_image.replace(".jpg","_reel.mp4")
            os.system(
                f'ffmpeg -loop 1 -i "{reel_image}" -t 15 '
                f'-vf "scale=1080:1920" -c:v libx264 -pix_fmt yuv420p '
                f'"{reel_path}" -y -loglevel error'
            )

        if reel_path and os.path.exists(reel_path):
            success = upload_video_to_instagram(reel_path, caption)
        else:
            # Final fallback: post as photo if video creation fails entirely
            print("⚠️  Reel failed — falling back to photo post...")
            image_path = create_photo_image(data, poet)
            image_url  = upload_image(image_path)
            success    = post_photo(image_url, caption)

    else:
        print(f"❌ Unknown POST_TYPE: '{POST_TYPE}' — expected 'photo' or 'reel'")
        sys.exit(1)

    # --- UPDATE PROGRESS ON SUCCESS ---
    if success:
        today = datetime.utcnow().strftime("%Y-%m-%d")

        p["total_posts"]    += 1
        p["last_post_date"]  = today
        p["last_post_type"]  = POST_TYPE
        p["status"]          = "success"

        if POST_TYPE == "photo":
            # Save today's generated content so the reel can reuse it later
            # Without this, evening reel generates a fresh sher = duplicate day
            p["today_content"] = data

            # Photo advances to next poet (1 poet per day now)
            p["poet_index"] += 1
            next_poet = POET_SCHEDULE[p["poet_index"] % len(POET_SCHEDULE)]
            print(f"Moving to next poet: {next_poet['name']}")

        else:  # reel
            # Reel does NOT advance the day — same day as the morning photo
            # Clear today_content after reel so tomorrow starts fresh
            p["today_content"] = None

        save_progress(p)
        print(f"\u2705 Progress saved. Total posts: {p['total_posts']}")
    else:
        print("\u274c Post failed.")
        sys.exit(1)
        print("❌ Post failed.")
        sys.exit(1)


# ============================================================
# ENTRY POINT — retry wrapper around run()
# ============================================================
def main():
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"\n{'='*30}")
            print(f"Attempt {attempt}/{MAX_RETRIES}")
            print(f"{'='*30}")

            # Duplicate-post guard — skip if already posted today
            if already_posted_today(POST_TYPE):
                print(f"⚠️  Already posted {POST_TYPE} today (UTC). Skipping.")
                return

            run()  # <-- all the work happens here

            # FIX: mark_post_success() removed — progress is saved inside run()
            # Previously, run() saved progress AND main() called mark_post_success()
            # which saved again — redundant and caused issues if run() raised after save

            print("✅ Completed successfully.")
            return

        except Exception as e:
            print(f"❌ Attempt {attempt} failed")
            print(f"   Error type: {type(e).__name__}")
            print(f"   Error: {e}")

            if attempt < MAX_RETRIES and is_retryable_error(e):
                print(f"⏳ Retrying in {RETRY_DELAY//60} minutes...")
                time.sleep(RETRY_DELAY)
            else:
                print("🚫 Max retries reached or non-retryable error. Exiting.")
                sys.exit(1)


if __name__ == "__main__":
    main()