"""
Shayari Instagram Automation Bot v2
- Vintage manuscript aesthetic
- Urdu Nastaliq font support
- Daily photo (8 AM IST) + Reel (7 PM IST)
- Runs on GitHub Actions (zero cost)
"""

from google import genai
import requests
import json
import os
import sys
import time
import textwrap
import random
import math
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import base64

# ============================================================
# CONFIGURATION
# ============================================================
GEMINI_API_KEY         = os.environ.get("GEMINI_API_KEY", "")
INSTAGRAM_ACCESS_TOKEN = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
INSTAGRAM_USER_ID      = os.environ.get("INSTAGRAM_USER_ID", "")
IMGBB_API_KEY          = os.environ.get("IMGBB_API_KEY", "")
POST_TYPE              = os.environ.get("POST_TYPE", "photo")  # "photo" or "reel"

# Your Instagram handle
IG_HANDLE = "@ak_apak"

# Font paths (installed by workflow)
FONT_URDU   = "/usr/share/fonts/truetype/noto/NotoNastaliqUrdu-Regular.ttf"
FONT_SERIF  = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
FONT_ITALIC = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf"
FONT_SANS   = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

# ============================================================
# POET SCHEDULE
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
# VINTAGE MANUSCRIPT PALETTES — warm, aged, ink-on-paper feel
# ============================================================
PALETTES = [
    # Aged parchment — warm amber ink
    {"bg": "#f5e6c8", "bg2": "#ede0b5", "text": "#2c1810", "accent": "#8b4513",
     "sub": "#6b3410", "border": "#c9a96e", "ink": "#3d1f0d"},
    # Weathered cream — deep indigo ink
    {"bg": "#f0ead6", "bg2": "#e8dfc4", "text": "#1a1a3e", "accent": "#4a3f8a",
     "sub": "#2d2760", "border": "#9b8cc0", "ink": "#0f0f2e"},
    # Old ivory — forest green ink
    {"bg": "#f2edd8", "bg2": "#eae5c8", "text": "#1a2e1a", "accent": "#2d5a1b",
     "sub": "#1a3a0f", "border": "#7a9e5a", "ink": "#0f1e0f"},
    # Antique white — burgundy ink
    {"bg": "#f4ebe0", "bg2": "#ecdfd0", "text": "#2e0f1a", "accent": "#8b1a2a",
     "sub": "#5a0f1a", "border": "#c07080", "ink": "#1e0810"},
    # Faded sepia — dark coffee ink
    {"bg": "#f0e4c8", "bg2": "#e8dab8", "text": "#1e1208", "accent": "#5c3a1e",
     "sub": "#3a2010", "border": "#a07840", "ink": "#120c04"},
    # Aged vellum — prussian blue ink
    {"bg": "#f3ead5", "bg2": "#ebdfc5", "text": "#0a1a2e", "accent": "#0f3460",
     "sub": "#0a2040", "border": "#4a7ab0", "ink": "#061018"},
    # Worn paper — rust ink
    {"bg": "#f1e8d0", "bg2": "#e9ddc0", "text": "#2a1008", "accent": "#8b3010",
     "sub": "#5a1e08", "border": "#c06040", "ink": "#1a0804"},
    # Cream linen — charcoal ink
    {"bg": "#f2ece0", "bg2": "#eae4d4", "text": "#1a1a1a", "accent": "#3a3a3a",
     "sub": "#555555", "border": "#888888", "ink": "#0a0a0a"},
    # Antique rose — deep plum ink
    {"bg": "#f4e8e0", "bg2": "#ecdcd4", "text": "#2a0a1e", "accent": "#6b1a4a",
     "sub": "#4a0f32", "border": "#b06090", "ink": "#1a0412"},
    # Old gold — dark teal ink
    {"bg": "#f2e8c8", "bg2": "#eaddb8", "text": "#081e1e", "accent": "#1a5a5a",
     "sub": "#0f3a3a", "border": "#509090", "ink": "#041010"},
    # Bleached parchment — mahogany ink
    {"bg": "#f5edd8", "bg2": "#ede3c8", "text": "#1e0e06", "accent": "#6b2010",
     "sub": "#4a1608", "border": "#b07050", "ink": "#140804"},
    # Faded linen — deep violet ink
    {"bg": "#f0eadc", "bg2": "#e8dfcc", "text": "#180a2a", "accent": "#4a1a7a",
     "sub": "#2e0f50", "border": "#8060b0", "ink": "#0e0618"},
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
# STEP 1: Generate Shayari
# ============================================================
def generate_shayari(poet: dict, day_number: int) -> dict:
    client = genai.Client(api_key=GEMINI_API_KEY)

    prompt = f"""You run an Instagram Shayari account dedicated to one poet for 30 days.

Today is Day {day_number} of 30 for: {poet['name']} ({poet['era']})

Tasks:
1. Write an original Shayari (4-6 lines) deeply inspired by {poet['name']}'s style and themes
2. Write it in Roman Urdu/Hindi transliteration
3. Include the original Urdu script version (proper Urdu, right to left)
4. Write a short English translation (1-2 lines)
5. Write an engaging Instagram caption (2-3 sentences) mentioning a real fact about the poet's life connected to this Shayari's theme. End with a question to drive comments.
6. List 3 niche hashtags specific to today's theme (not the poet's name)

Return ONLY valid JSON, no markdown, no explanation:
{{
  "shayari_roman": "line1\\nline2\\nline3\\nline4",
  "shayari_urdu": "...",
  "english_translation": "...",
  "caption": "...",
  "theme_hashtags": ["tag1", "tag2", "tag3"],
  "theme": "love/loss/nature/spirituality/resistance/etc"
}}"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    raw = response.text.strip().replace("```json", "").replace("```", "").strip()
    return json.loads(raw)


# ============================================================
# STEP 2: Draw manuscript texture background
# ============================================================
def draw_manuscript_bg(img: Image.Image, draw: ImageDraw.ImageDraw, palette: dict):
    w, h = img.size

    # Subtle noise texture — aged paper feel
    for _ in range(2000):
        x = random.randint(0, w)
        y = random.randint(0, h)
        r = random.randint(0, 2)
        opacity = random.randint(10, 40)
        # Darker speckles for age spots
        color = tuple(max(0, c - random.randint(10, 30)) for c in ImageDraw.ImageDraw(img).getfill()) if False else (
            int(palette["ink"][1:3], 16),
            int(palette["ink"][3:5], 16),
            int(palette["ink"][5:7], 16),
            opacity
        )
        draw.ellipse([x-r, y-r, x+r, y+r], fill=palette["bg2"])

    # Subtle horizontal lines — like old paper grain
    for y in range(0, h, random.randint(18, 28)):
        alpha = random.randint(5, 20)
        line_color = palette["bg2"]
        draw.line([(0, y), (w, y)], fill=line_color, width=1)


# ============================================================
# STEP 3: Draw ornate manuscript border
# ============================================================
def draw_ornate_border(draw: ImageDraw.ImageDraw, palette: dict, w: int, h: int):
    border_color = palette["border"]
    ink = palette["ink"]

    # Outer frame
    draw.rectangle([30, 30, w-30, h-30], outline=border_color, width=2)
    # Inner frame
    draw.rectangle([45, 45, w-45, h-45], outline=border_color, width=1)
    # Innermost thin line
    draw.rectangle([55, 55, w-55, h-55], outline=palette["sub"], width=1)

    # Corner ornaments — hand-drawn cross pattern
    corners = [(30, 30), (w-30, 30), (30, h-30), (w-30, h-30)]
    for cx, cy in corners:
        # Diamond
        size = 14
        draw.polygon([
            (cx, cy - size), (cx + size, cy),
            (cx, cy + size), (cx - size, cy)
        ], outline=border_color, fill=palette["bg2"])
        # Center dot
        draw.ellipse([cx-3, cy-3, cx+3, cy+3], fill=border_color)
        # Small circles at tips
        for dx, dy in [(0, -size), (size, 0), (0, size), (-size, 0)]:
            draw.ellipse([cx+dx-2, cy+dy-2, cx+dx+2, cy+dy+2], fill=border_color)

    # Side ornaments — middle of each border
    mid_ornaments = [(w//2, 30), (w//2, h-30), (30, h//2), (w-30, h//2)]
    for mx, my in mid_ornaments:
        draw.ellipse([mx-4, my-4, mx+4, my+4], fill=border_color)
        draw.ellipse([mx-8, my-8, mx+8, my+8], outline=border_color, width=1)

    # Top decorative header band
    draw.rectangle([55, 55, w-55, 160], outline=border_color, width=1)

    # Bottom decorative footer band
    draw.rectangle([55, h-160, w-55, h-55], outline=border_color, width=1)

    # Thin divider lines inside header/footer
    draw.line([(80, 100), (w-80, 100)], fill=palette["sub"], width=1)
    draw.line([(80, h-100), (w-80, h-100)], fill=palette["sub"], width=1)


# ============================================================
# STEP 4: Create vintage manuscript image
# ============================================================
def draw_diamond_motif(draw, cx, cy, size, color):
    """Geometric diamond ornament — no special characters needed."""
    draw.polygon([
        (cx, cy - size), (cx + size, cy),
        (cx, cy + size), (cx - size, cy)
    ], outline=color)
    draw.ellipse([cx-2, cy-2, cx+2, cy+2], fill=color)
    for dx, dy in [(0, -size-5), (size+5, 0), (0, size+5), (-size-5, 0)]:
        draw.ellipse([cx+dx-2, cy+dy-2, cx+dx+2, cy+dy+2], fill=color)

def draw_divider_ornament(draw, cx, cy, color):
    """Horizontal divider with central diamond."""
    draw.line([(cx-90, cy), (cx-18, cy)], fill=color, width=1)
    draw.line([(cx+18, cy), (cx+90, cy)], fill=color, width=1)
    draw_diamond_motif(draw, cx, cy, 7, color)

def create_image(shayari_data: dict, poet: dict, day_number: int, palette: dict) -> str:
    W, H = 1080, 1080
    img  = Image.new("RGB", (W, H), color=palette["bg"])
    draw = ImageDraw.Draw(img)

    # Paper texture + ornate border
    draw_manuscript_bg(img, draw, palette)
    draw_ornate_border(draw, palette, W, H)

    # Load fonts
    try:
        font_title = ImageFont.truetype(FONT_SERIF,  32)
        font_day   = ImageFont.truetype(FONT_ITALIC, 19)
        font_main  = ImageFont.truetype(FONT_SERIF,  38)
        font_trans = ImageFont.truetype(FONT_ITALIC, 20)
        font_brand = ImageFont.truetype(FONT_SANS,   17)
    except:
        font_title = font_day = font_main = font_trans = font_brand = ImageFont.load_default()

    try:
        font_urdu = ImageFont.truetype(FONT_URDU, 30)
    except:
        font_urdu = font_trans

    def center(text, y, font, color):
        bbox = draw.textbbox((0, 0), text, font=font)
        tw   = bbox[2] - bbox[0]
        draw.text(((W - tw) / 2, y), text, font=font, fill=color)

    # ── HEADER (y: 60–180) ───────────────────────────────────
    draw_divider_ornament(draw, W//2, 78, palette["border"])
    center(f"-- {poet['name']} --", 103, font_title, palette["accent"])
    center(f"Day {day_number} of 30   .   {poet['era']}", 148, font_day, palette["sub"])
    draw.line([(80, 175), (W-80, 175)], fill=palette["border"], width=1)

    # ── SHAYARI (vertically centered in y: 190–680) ──────────
    lines = shayari_data["shayari_roman"].strip().split("\n")
    all_wrapped = []
    for line in lines:
        wrapped = textwrap.wrap(line.strip(), width=40)
        all_wrapped.extend(wrapped if wrapped else [""])

    line_h  = 52
    zone_top, zone_bot = 190, 680
    total_h = len(all_wrapped) * line_h
    y_pos   = zone_top + max(0, (zone_bot - zone_top - total_h) // 2)

    for wline in all_wrapped:
        center(wline, y_pos, font_main, palette["text"])
        y_pos += line_h

    # ── DIVIDER (y: 695) ─────────────────────────────────────
    draw_divider_ornament(draw, W//2, 700, palette["border"])

    # ── URDU SCRIPT (y: 720–800) ─────────────────────────────
    y_pos = 722
    urdu_text = shayari_data.get("shayari_urdu", "")
    if urdu_text:
        for line in [l.strip() for l in urdu_text.strip().split("\n") if l.strip()][:2]:
            bbox = draw.textbbox((0, 0), line, font=font_urdu)
            tw   = bbox[2] - bbox[0]
            draw.text(((W - tw) / 2, y_pos), line, font=font_urdu, fill=palette["sub"])
            y_pos += 44

    # ── TRANSLATION (y: 810–870) ─────────────────────────────
    y_pos = max(y_pos + 8, 810)
    for line in textwrap.wrap(f'"{shayari_data["english_translation"]}"', width=56):
        center(line, y_pos, font_trans, palette["accent"])
        y_pos += 28

    # ── FOOTER (y: 900–1000) ─────────────────────────────────
    draw.line([(80, 905), (W-80, 905)], fill=palette["border"], width=1)
    draw_divider_ornament(draw, W//2, 935, palette["border"])
    center(IG_HANDLE, 965, font_brand, palette["sub"])

    # ── VIGNETTE — aged paper edges ──────────────────────────
    vignette = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    vdraw    = ImageDraw.Draw(vignette)
    for i in range(50):
        vdraw.rectangle([i, i, W-i, H-i], outline=(0, 0, 0, int(i * 1.4)))
    img = img.convert("RGBA")
    img = Image.alpha_composite(img, vignette)
    img = img.convert("RGB")

    os.makedirs("output", exist_ok=True)
    filename = f"output/shayari_day{day_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    img.save(filename, "JPEG", quality=95)
    print(f"✅ Image saved: {filename}")
    return filename


# ============================================================
# STEP 5: Create Reel video from image
# ============================================================
def create_reel(image_path: str) -> str:
    try:
        from moviepy.editor import ImageClip, CompositeVideoClip
        import numpy as np

        duration = 15  # seconds

        # Ken Burns zoom effect
        def zoom_effect(t):
            zoom = 1 + 0.04 * (t / duration)  # subtle 4% zoom over 15s
            return zoom

        clip = ImageClip(image_path, duration=duration)
        W, H = clip.size

        def make_frame(t):
            zoom = zoom_effect(t)
            frame = clip.get_frame(t)
            frame_img = Image.fromarray(frame)
            new_w = int(W * zoom)
            new_h = int(H * zoom)
            frame_img = frame_img.resize((new_w, new_h), Image.LANCZOS)
            # Center crop back to original size
            left = (new_w - W) // 2
            top  = (new_h - H) // 2
            frame_img = frame_img.crop((left, top, left + W, top + H))
            return np.array(frame_img)

        final = clip.fl(lambda gf, t: make_frame(t), apply_to=['mask'])
        reel_path = image_path.replace(".jpg", "_reel.mp4")
        final.write_videofile(
            reel_path,
            fps=24,
            codec="libx264",
            audio=False,
            verbose=False,
            logger=None
        )
        print(f"✅ Reel saved: {reel_path}")
        return reel_path
    except Exception as e:
        print(f"❌ Reel creation failed: {e}")
        return None


# ============================================================
# STEP 6: Upload image to imgbb
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
# STEP 7: Post photo to Instagram
# ============================================================
def post_photo(image_url: str, shayari_data: dict, poet: dict) -> bool:
    poet_tags   = POET_HASHTAGS.get(poet["name"], [])
    all_tags    = BASE_HASHTAGS + poet_tags + shayari_data.get("theme_hashtags", [])
    hashtag_str = " ".join([f"#{t}" for t in all_tags[:10]])
    caption     = f"{shayari_data['caption']}\n\n{hashtag_str}"

    container = requests.post(
        f"https://graph.instagram.com/v21.0/{INSTAGRAM_USER_ID}/media",
        data={"image_url": image_url, "caption": caption, "access_token": INSTAGRAM_ACCESS_TOKEN}
    ).json()

    if "id" not in container:
        print(f"❌ Container error: {container}")
        return False

    print(f"✅ Container: {container['id']}")
    time.sleep(5)

    publish = requests.post(
        f"https://graph.instagram.com/v21.0/{INSTAGRAM_USER_ID}/media_publish",
        data={"creation_id": container["id"], "access_token": INSTAGRAM_ACCESS_TOKEN}
    ).json()

    if "id" in publish:
        print(f"🎉 Photo posted! ID: {publish['id']}")
        return True

    print(f"❌ Publish error: {publish}")
    return False


# ============================================================
# STEP 8: Post Reel to Instagram
# ============================================================
def post_reel(video_path: str, shayari_data: dict, poet: dict) -> bool:
    # Upload video to imgbb as file
    with open(video_path, "rb") as f:
        video_data = base64.b64encode(f.read()).decode("utf-8")

    # Upload to imgbb
    result = requests.post(
        "https://api.imgbb.com/1/upload",
        data={"key": IMGBB_API_KEY, "image": video_data}
    ).json()

    if not result.get("success"):
        print(f"❌ Video upload failed: {result}")
        return False

    video_url = result["data"]["url"]

    poet_tags   = POET_HASHTAGS.get(poet["name"], [])
    all_tags    = BASE_HASHTAGS + poet_tags + shayari_data.get("theme_hashtags", [])
    hashtag_str = " ".join([f"#{t}" for t in all_tags[:10]])
    caption     = f"{shayari_data['caption']}\n\n{hashtag_str}"

    container = requests.post(
        f"https://graph.instagram.com/v21.0/{INSTAGRAM_USER_ID}/media",
        data={
            "video_url": video_url,
            "media_type": "REELS",
            "caption": caption,
            "access_token": INSTAGRAM_ACCESS_TOKEN
        }
    ).json()

    if "id" not in container:
        print(f"❌ Reel container error: {container}")
        return False

    print(f"✅ Reel container: {container['id']}")

    # Wait for video processing
    for _ in range(10):
        time.sleep(10)
        status = requests.get(
            f"https://graph.instagram.com/v21.0/{container['id']}",
            params={"fields": "status_code", "access_token": INSTAGRAM_ACCESS_TOKEN}
        ).json()
        print(f"   Status: {status.get('status_code')}")
        if status.get("status_code") == "FINISHED":
            break

    publish = requests.post(
        f"https://graph.instagram.com/v21.0/{INSTAGRAM_USER_ID}/media_publish",
        data={"creation_id": container["id"], "access_token": INSTAGRAM_ACCESS_TOKEN}
    ).json()

    if "id" in publish:
        print(f"🎉 Reel posted! ID: {publish['id']}")
        return True

    print(f"❌ Reel publish error: {publish}")
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
    print(f"🌙 Shayari Bot v2 — {datetime.now().strftime('%Y-%m-%d %H:%M')} — {POST_TYPE.upper()}")
    print(f"{'='*50}")

    p          = load_progress()
    poet_index = p["poet_index"] % len(POET_SCHEDULE)
    day        = p["day"]
    poet       = POET_SCHEDULE[poet_index]
    palette    = PALETTES[poet_index % len(PALETTES)]

    print(f"📖 {poet['name']} | Day {day}/30 | Posting: {POST_TYPE}")

    # Generate Shayari
    print("✍️  Generating Shayari...")
    shayari_data = generate_shayari(poet, day)
    print(f"   Theme: {shayari_data['theme']}")

    # Create image
    print("🎨 Creating image...")
    image_path = create_image(shayari_data, poet, day, palette)

    if POST_TYPE == "photo":
        # Upload and post photo
        print("☁️  Uploading image...")
        image_url = upload_image(image_path)
        print("📸 Posting photo...")
        success = post_photo(image_url, shayari_data, poet)

    elif POST_TYPE == "reel":
        # Create and post reel
        print("🎬 Creating Reel...")
        reel_path = create_reel(image_path)
        if reel_path:
            print("📱 Posting Reel...")
            success = post_reel(reel_path, shayari_data, poet)
        else:
            # Fallback to photo if reel creation fails
            print("⚠️  Reel failed, falling back to photo...")
            image_url = upload_image(image_path)
            success = post_photo(image_url, shayari_data, poet)
    else:
        print(f"❌ Unknown POST_TYPE: {POST_TYPE}")
        sys.exit(1)

    if success:
        # Only advance day counter after photo post (not reel — same day)
        if POST_TYPE == "photo":
            p["total_posts"] += 1
            if day >= 30:
                p["day"] = 1
                p["poet_index"] += 1
                print(f"🎊 30 days of {poet['name']} done! Next poet up.")
            else:
                p["day"] = day + 1
            save_progress(p)
        print(f"✅ Done! Total posts: {p['total_posts']}")
    else:
        print("❌ Failed.")
        sys.exit(1)


if __name__ == "__main__":
    run()
