"""
Shayari Instagram Automation Bot
- Generates daily Shayari using Google Gemini API
- Creates beautiful 1080x1080 images
- Posts to Instagram via Graph API
- Designed to run on GitHub Actions (zero cost)
"""

from google import genai
from google.genai import types
import requests
import json
import os
import sys
import time
import textwrap
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import base64

# ============================================================
# CONFIGURATION — reads from environment variables (GitHub Secrets)
# ============================================================
GEMINI_API_KEY         = os.environ.get("GEMINI_API_KEY", "")
INSTAGRAM_ACCESS_TOKEN = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
INSTAGRAM_USER_ID      = os.environ.get("INSTAGRAM_USER_ID", "")
IMGBB_API_KEY          = os.environ.get("IMGBB_API_KEY", "")

# ============================================================
# POET SCHEDULE — 30 days each
# ============================================================
POET_SCHEDULE = [
    {"name": "Mirza Ghalib",    "era": "1797–1869"},
    {"name": "Faiz Ahmed Faiz", "era": "1911–1984"},
    {"name": "Allama Iqbal",    "era": "1877–1938"},
    {"name": "Mir Taqi Mir",    "era": "1723–1810"},
    {"name": "Ahmad Faraz",     "era": "1931–2008"},
    {"name": "Parveen Shakir",  "era": "1952–1994"},
    {"name": "Sahir Ludhianvi", "era": "1921–1980"},
    {"name": "Gulzar",          "era": "1934–"    },
    {"name": "Rahat Indori",    "era": "1950–2020"},
    {"name": "Habib Jalib",     "era": "1928–1993"},
    {"name": "Wasi Shah",       "era": "1977–"    },
    {"name": "Josh Malihabadi", "era": "1898–1982"},
]

# ============================================================
# COLOR PALETTES — one per poet
# ============================================================
PALETTES = [
    {"bg": "#120a1e", "text": "#f5e6c8", "accent": "#c9a96e", "sub": "#7a5c35"},
    {"bg": "#0b1a0b", "text": "#e8f5e9", "accent": "#81c784", "sub": "#388e3c"},
    {"bg": "#1a0a0e", "text": "#fce4ec", "accent": "#f48fb1", "sub": "#c2185b"},
    {"bg": "#08081a", "text": "#e3f2fd", "accent": "#90caf9", "sub": "#1565c0"},
    {"bg": "#1a1200", "text": "#fff8e1", "accent": "#ffd54f", "sub": "#e65100"},
    {"bg": "#0f0f0f", "text": "#f0f0f0", "accent": "#bdbdbd", "sub": "#616161"},
    {"bg": "#1a0f05", "text": "#fbe9e7", "accent": "#ff8a65", "sub": "#bf360c"},
    {"bg": "#04080f", "text": "#e0f7fa", "accent": "#4dd0e1", "sub": "#006064"},
    {"bg": "#100518", "text": "#f3e5f5", "accent": "#ce93d8", "sub": "#6a1b9a"},
    {"bg": "#0a1a10", "text": "#e8f5e9", "accent": "#a5d6a7", "sub": "#2e7d32"},
    {"bg": "#1a1010", "text": "#fff3e0", "accent": "#ffb74d", "sub": "#e65100"},
    {"bg": "#0a0a14", "text": "#ede7f6", "accent": "#9575cd", "sub": "#4527a0"},
]

# ============================================================
# HASHTAGS
# ============================================================
BASE_HASHTAGS = [
    "shayari", "urdupoetry", "hindishayari",
    "shayarilover", "urdushayari", "poetrycommunity",
    "shayarioftheday", "instashayari",
]

POET_HASHTAGS = {
    "Mirza Ghalib":    ["mirzaghalib", "ghalib", "ghalibishayari"],
    "Faiz Ahmed Faiz": ["faizahmedfaiz", "faizshayari", "faiz"],
    "Allama Iqbal":    ["allamaiqbal", "iqbal", "iqbalshayari"],
    "Mir Taqi Mir":    ["mirtaqimir", "mir", "klassicalurdu"],
    "Ahmad Faraz":     ["ahmadfaraz", "faraz", "farazshayari"],
    "Parveen Shakir":  ["parveenshakir", "shakir", "urdupoetess"],
    "Sahir Ludhianvi": ["sahirludhianvi", "sahir", "sahirshayari"],
    "Gulzar":          ["gulzar", "gulzarshayari", "gulzarsahab"],
    "Rahat Indori":    ["rahatindori", "rahat", "rahatshayari"],
    "Habib Jalib":     ["habibjalib", "jalib", "jalibshayari"],
    "Wasi Shah":       ["wasishah", "wasi", "modernurdu"],
    "Josh Malihabadi": ["joshmalihabadi", "josh", "joshpoetry"],
}


# ============================================================
# STEP 1: Generate Shayari using Gemini
# ============================================================
def generate_shayari(poet: dict, day_number: int) -> dict:
    client = genai.Client(api_key=GEMINI_API_KEY)

    prompt = f"""You run an Instagram Shayari account dedicated to one poet for 30 days.

Today is Day {day_number} of 30 for: {poet['name']} ({poet['era']})

Tasks:
1. Write an original Shayari (4-6 lines) deeply inspired by {poet['name']}'s style and themes
2. Write it in Roman Urdu/Hindi transliteration
3. Include the original Urdu/Hindi script version
4. Write a short English translation (1-2 lines)
5. Write an engaging Instagram caption (2-3 sentences) mentioning a real fact about the poet's life connected to this Shayari's theme. End with a question to drive comments.
6. List 3 niche hashtags specific to today's theme (not the poet's name)

Return ONLY valid JSON, no markdown, no explanation:
{{
  "shayari_roman": "line1\\nline2\\nline3\\nline4",
  "shayari_script": "...",
  "english_translation": "...",
  "caption": "...",
  "theme_hashtags": ["tag1", "tag2", "tag3"],
  "theme": "love/loss/nature/spirituality/resistance/etc"
}}"""

    response = client.models.generate_content(
        model="gemini-1.5-flash",
        contents=prompt
    )
    raw = response.text.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(raw)


# ============================================================
# STEP 2: Create beautiful image
# ============================================================
def create_image(shayari_data: dict, poet: dict, day_number: int, palette: dict) -> str:
    img  = Image.new("RGB", (1080, 1080), color=palette["bg"])
    draw = ImageDraw.Draw(img)

    # Corner ornaments
    for x, y in [(60, 60), (1020, 60), (60, 1020), (1020, 1020)]:
        draw.ellipse([x-4, y-4, x+4, y+4], fill=palette["accent"])
        draw.ellipse([x-22, y-22, x+22, y+22], outline=palette["accent"], width=1)
        draw.ellipse([x-38, y-38, x+38, y+38], outline=palette["sub"], width=1)

    # Decorative lines
    draw.line([(100, 130), (980, 130)], fill=palette["accent"], width=1)
    draw.line([(100, 950), (980, 950)], fill=palette["accent"], width=1)

    # Load fonts (GitHub Actions uses Ubuntu — these fonts are available)
    try:
        font_poet   = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", 32)
        font_day    = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
        font_main   = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", 44)
        font_script = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf", 26)
        font_trans  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
        font_brand  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
    except:
        font_poet = font_day = font_main = font_script = font_trans = font_brand = ImageFont.load_default()

    def center(text, y, font, color):
        bbox = draw.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
        draw.text(((1080 - w) / 2, y), text, font=font, fill=color)

    # Poet name and day
    center(f"— {poet['name']} —", 150, font_poet, palette["accent"])
    center(f"Day {day_number} of 30  ·  {poet['era']}", 200, font_day, palette["sub"])

    # Main Shayari
    lines = shayari_data["shayari_roman"].strip().split("\n")
    y_pos = 300
    for line in lines:
        for wline in textwrap.wrap(line.strip(), width=36):
            center(wline, y_pos, font_main, palette["text"])
            y_pos += 62
    y_pos += 20

    # Divider
    draw.line([(250, y_pos), (830, y_pos)], fill=palette["sub"], width=1)
    y_pos += 25

    # Script version
    for line in textwrap.wrap(shayari_data["shayari_script"], width=42)[:2]:
        center(line, y_pos, font_script, palette["sub"])
        y_pos += 38
    y_pos += 10

    # English translation
    for line in textwrap.wrap(f'"{shayari_data["english_translation"]}"', width=52):
        center(line, y_pos, font_trans, palette["accent"])
        y_pos += 30

    # Brand handle
    center("@YourInstagramHandle", 970, font_brand, palette["sub"])

    os.makedirs("output", exist_ok=True)
    filename = f"output/shayari_day{day_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    img.save(filename, "JPEG", quality=95)
    print(f"✅ Image saved: {filename}")
    return filename


# ============================================================
# STEP 3: Upload to imgbb
# ============================================================
def upload_image(image_path: str) -> str:
    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")
    result = requests.post(
        "https://api.imgbb.com/1/upload",
        data={"key": IMGBB_API_KEY, "image": image_data}
    ).json()
    if result.get("success"):
        url = result["data"]["url"]
        print(f"✅ Uploaded: {url}")
        return url
    raise Exception(f"imgbb failed: {result}")


# ============================================================
# STEP 4: Post to Instagram
# ============================================================
def post_to_instagram(image_url: str, shayari_data: dict, poet: dict) -> bool:
    poet_tags   = POET_HASHTAGS.get(poet["name"], [])
    all_tags    = BASE_HASHTAGS + poet_tags + shayari_data.get("theme_hashtags", [])
    hashtag_str = " ".join([f"#{t}" for t in all_tags[:10]])
    caption     = f"{shayari_data['caption']}\n\n{hashtag_str}"

    container = requests.post(
        f"https://graph.facebook.com/v18.0/{INSTAGRAM_USER_ID}/media",
        data={"image_url": image_url, "caption": caption, "access_token": INSTAGRAM_ACCESS_TOKEN}
    ).json()

    if "id" not in container:
        print(f"❌ Container error: {container}")
        return False

    print(f"✅ Container: {container['id']}")
    time.sleep(5)

    publish = requests.post(
        f"https://graph.facebook.com/v18.0/{INSTAGRAM_USER_ID}/media_publish",
        data={"creation_id": container["id"], "access_token": INSTAGRAM_ACCESS_TOKEN}
    ).json()

    if "id" in publish:
        print(f"🎉 Posted! ID: {publish['id']}")
        return True

    print(f"❌ Publish error: {publish}")
    return False


# ============================================================
# PROGRESS TRACKING
# ============================================================
def load_progress() -> dict:
    if os.path.exists("progress.json"):
        with open("progress.json") as f:
            return json.load(f)
    return {"poet_index": 0, "day": 1, "total_posts": 0}


def save_progress(p: dict):
    with open("progress.json", "w") as f:
        json.dump(p, f, indent=2)


# ============================================================
# MAIN
# ============================================================
def run():
    print(f"\n{'='*50}")
    print(f"🌙 Shayari Bot — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*50}")

    p          = load_progress()
    poet_index = p["poet_index"] % len(POET_SCHEDULE)
    day        = p["day"]
    poet       = POET_SCHEDULE[poet_index]
    palette    = PALETTES[poet_index % len(PALETTES)]

    print(f"📖 {poet['name']} | Day {day}/30")

    print("✍️  Generating Shayari...")
    shayari_data = generate_shayari(poet, day)
    print(f"   Theme: {shayari_data['theme']}")

    print("🎨 Creating image...")
    image_path = create_image(shayari_data, poet, day, palette)

    print("☁️  Uploading...")
    image_url = upload_image(image_path)

    print("📱 Posting...")
    success = post_to_instagram(image_url, shayari_data, poet)

    if success:
        p["total_posts"] += 1
        if day >= 30:
            p["day"] = 1
            p["poet_index"] += 1
            print(f"🎊 30 days of {poet['name']} done! Next poet up.")
        else:
            p["day"] = day + 1
        save_progress(p)
        print(f"✅ Total posts: {p['total_posts']}")
    else:
        print("❌ Failed. Will retry tomorrow.")
        sys.exit(1)


if __name__ == "__main__":
    run()
