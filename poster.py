"""
Shayari Instagram Bot v4
- Real authentic Shayari
- Emotion-driven dark visuals
- 1:1 (1080x1080) for photos, 16:9 (1080x1920) for Reels
- Instagram rupload API for video (no third-party hosting)
- Edge TTS for voiceover (free, no API key)
- No Urdu script on image — Roman + English only
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

# ============================================================
# CONFIGURATION
# ============================================================
GEMINI_API_KEY         = os.environ.get("GEMINI_API_KEY", "")
INSTAGRAM_ACCESS_TOKEN = os.environ.get("INSTAGRAM_ACCESS_TOKEN", "")
INSTAGRAM_USER_ID      = os.environ.get("INSTAGRAM_USER_ID", "")
IMGBB_API_KEY          = os.environ.get("IMGBB_API_KEY", "")
POST_TYPE              = os.environ.get("POST_TYPE", "photo")
IG_HANDLE              = "@ak_apak"

# Font paths
FONT_SERIF  = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"
FONT_ITALIC = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf"
FONT_SANS   = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

# ============================================================
# POET SCHEDULE
# ============================================================
POET_SCHEDULE = [
    {"name": "Mirza Ghalib",    "era": "1797-1869"},
    {"name": "Mir Taqi Mir",    "era": "1723-1810"},
    {"name": "Allama Iqbal",    "era": "1877-1938"},
    {"name": "Faiz Ahmed Faiz", "era": "1911-1984"},
    {"name": "Ahmad Faraz",     "era": "1931-2008"},
    {"name": "Parveen Shakir",  "era": "1952-1994"},
    {"name": "Sahir Ludhianvi", "era": "1921-1980"},
    {"name": "Gulzar",          "era": "1934-"    },
    {"name": "Rahat Indori",    "era": "1950-2020"},
    {"name": "Habib Jalib",     "era": "1928-1993"},
    {"name": "Josh Malihabadi", "era": "1898-1982"},
    {"name": "Wasi Shah",       "era": "1977-"    },
]

# ============================================================
# FORMAT ROTATION — 2x one-liner, 3x couplet, 2x longer per week
# ============================================================
FORMAT_MAP = {
    1:"couplet",   2:"one-liner", 3:"couplet",  4:"longer",   5:"couplet",
    6:"one-liner", 7:"longer",    8:"couplet",  9:"one-liner",10:"couplet",
    11:"longer",   12:"couplet",  13:"one-liner",14:"longer",  15:"couplet",
    16:"one-liner",17:"couplet",  18:"longer",   19:"couplet", 20:"one-liner",
    21:"longer",   22:"couplet",  23:"one-liner",24:"couplet", 25:"longer",
    26:"couplet",  27:"one-liner",28:"longer",   29:"couplet", 30:"one-liner",
}
def get_format(day): return FORMAT_MAP.get(day, "couplet")

# ============================================================
# EMOTION PALETTES — all dark
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
    "Mirza Ghalib":    ["mirzaghalib","ghalib","ghalibishayari"],
    "Faiz Ahmed Faiz": ["faizahmedfaiz","faizshayari","faiz"],
    "Allama Iqbal":    ["allamaiqbal","iqbal","iqbalshayari"],
    "Mir Taqi Mir":    ["mirtaqimir","mir","klassicalurdu"],
    "Ahmad Faraz":     ["ahmadfaraz","faraz","farazshayari"],
    "Parveen Shakir":  ["parveenshakir","shakir","urdupoetess"],
    "Sahir Ludhianvi": ["sahirludhianvi","sahir","sahirshayari"],
    "Gulzar":          ["gulzar","gulzarshayari","gulzarsahab"],
    "Rahat Indori":    ["rahatindori","rahat","rahatshayari"],
    "Habib Jalib":     ["habibjalib","jalib","jalibshayari"],
    "Wasi Shah":       ["wasishah","wasi","modernurdu"],
    "Josh Malihabadi": ["joshmalihabadi","josh","joshpoetry"],
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
# STEP 1: Generate content
# ============================================================
def generate_content(poet: dict, day: int) -> dict:
    client      = genai.Client(api_key=GEMINI_API_KEY)
    fmt         = get_format(day)
    tag_trigger = TAG_TRIGGERS[day % len(TAG_TRIGGERS)]

    prompt = f"""You run a premium Instagram Shayari account dedicating 30 days to one poet.
Today is Day {day} of 30 for: {poet['name']} ({poet['era']})

RULES:
1. Quote a REAL, AUTHENTIC sher by {poet['name']} — NOT AI generated, NOT paraphrased.
2. Format today: {fmt}
   one-liner = 1 misra only
   couplet = exactly 2 lines
   longer = 4-6 lines from a real ghazal/nazm
3. Roman Urdu transliteration of the sher only
4. English translation: MAX 1 LINE. Poetic, not literal.
5. Source collection if known (e.g. Diwan-e-Ghalib)

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

Return ONLY valid JSON, no markdown:
{{
  "sher_roman": "...",
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
    raw = response.text.strip().replace("```json","").replace("```","").strip()
    return json.loads(raw)


# ============================================================
# HELPERS: Border + Divider + Texture
# ============================================================
def draw_border(draw, p, W, H):
    draw.rectangle([20,20,W-20,H-20], outline=p["border"], width=2)
    draw.rectangle([32,32,W-32,H-32], outline=p["border"], width=1)
    draw.rectangle([40,40,W-40,H-40], outline=p["accent"],  width=1)
    for cx,cy in [(20,20),(W-20,20),(20,H-20),(W-20,H-20)]:
        s=10
        draw.polygon([(cx,cy-s),(cx+s,cy),(cx,cy+s),(cx-s,cy)], fill=p["accent"])
        draw.ellipse([cx-3,cy-3,cx+3,cy+3], fill=p["border"])
    for mx,my in [(W//2,20),(W//2,H-20),(20,H//2),(W-20,H//2)]:
        draw.ellipse([mx-4,my-4,mx+4,my+4], fill=p["border"])

def draw_divider(draw, cx, cy, color, w=100):
    draw.line([(cx-w,cy),(cx-14,cy)], fill=color, width=1)
    draw.line([(cx+14,cy),(cx+w,cy)], fill=color, width=1)
    s=7
    draw.polygon([(cx,cy-s),(cx+s,cy),(cx,cy+s),(cx-s,cy)], outline=color)
    draw.ellipse([cx-2,cy-2,cx+2,cy+2], fill=color)

def add_texture(draw, W, H, accent):
    ink = tuple(int(accent[i:i+2],16) for i in (1,3,5))
    for _ in range(600):
        x,y = random.randint(0,W), random.randint(0,H)
        r   = random.randint(0,1)
        draw.ellipse([x-r,y-r,x+r,y+r], fill=(*ink, random.randint(4,14)))


# ============================================================
# STEP 2: Create 1:1 photo image (1080x1080)
# ============================================================
def create_photo_image(data: dict, poet: dict, day: int) -> str:
    W, H    = 1080, 1080
    emotion = data.get("emotion","dard").lower()
    palette = dict(EMOTION_PALETTES.get(emotion, DEFAULT_PALETTE))
    for key,field in [("bg","bg_color"),("text","text_color"),("accent","accent_color")]:
        v = data.get(field,"")
        if v and v.startswith("#") and len(v)==7:
            palette[key] = v

    img  = Image.new("RGB",(W,H), color=palette["bg"])
    draw = ImageDraw.Draw(img)
    add_texture(draw, W, H, palette["accent"])
    draw_border(draw, palette, W, H)

    # Fonts
    try:
        font_poet  = ImageFont.truetype(FONT_SERIF,  28)
        font_day   = ImageFont.truetype(FONT_ITALIC, 17)
        font_trans = ImageFont.truetype(FONT_ITALIC, 19)
        font_brand = ImageFont.truetype(FONT_SANS,   16)
        font_src   = ImageFont.truetype(FONT_ITALIC, 15)
    except:
        font_poet=font_day=font_trans=font_brand=font_src=ImageFont.load_default()

    fmt = data.get("format","couplet")
    fs  = 50 if fmt=="one-liner" else (44 if fmt=="couplet" else 38)
    try:    font_sher = ImageFont.truetype(FONT_SERIF, fs)
    except: font_sher = font_poet

    def center(text, y, font, color):
        bbox = draw.textbbox((0,0),text,font=font)
        tw   = bbox[2]-bbox[0]
        draw.text(((W-tw)/2,y), text, font=font, fill=color)

    # HEADER
    draw_divider(draw, W//2, 65, palette["accent"], 60)
    center(f"-- {poet['name']} --", 85, font_poet, palette["accent"])
    center(f"Day {day} of 30   .   {poet['era']}", 128, font_day, palette["sub"])
    draw.line([(65,162),(W-65,162)], fill=palette["border"], width=1)

    # ROMAN SHER — zone 178–720 (60% of content)
    lines       = data["sher_roman"].strip().split("\n")
    all_wrapped = []
    for line in lines:
        w2 = textwrap.wrap(line.strip(), width=36)
        all_wrapped.extend(w2 if w2 else [""])

    line_h  = int(fs*1.38)
    total_h = len(all_wrapped)*line_h
    y_pos   = 178 + max(0,(542-total_h)//2)
    for wline in all_wrapped:
        center(wline, y_pos, font_sher, palette["text"])
        y_pos += line_h

    # DIVIDER
    div_y = max(y_pos+20, 730)
    draw_divider(draw, W//2, div_y, palette["accent"])

    # ENGLISH TRANSLATION — zone below divider to 890
    trans   = f'"{data["english_translation"]}"'
    tlines  = textwrap.wrap(trans, width=54)
    tlh     = 27
    total_t = len(tlines)*tlh
    y_pos   = div_y+20 + max(0,(130-total_t)//2)
    for line in tlines:
        center(line, y_pos, font_trans, palette["accent"])
        y_pos += tlh

    src = data.get("source","")
    if src and src.lower() not in ("unknown",""):
        center(f"-- {src}", y_pos+6, font_src, palette["sub"])

    # FOOTER
    draw.line([(65,908),(W-65,908)], fill=palette["border"], width=1)
    draw_divider(draw, W//2, 935, palette["accent"], 60)
    center(IG_HANDLE, 962, font_brand, palette["sub"])

    # VIGNETTE
    vig  = Image.new("RGBA",(W,H),(0,0,0,0))
    vd   = ImageDraw.Draw(vig)
    for i in range(80):
        vd.rectangle([i,i,W-i,H-i], outline=(0,0,0,int(i*1.8)))
    img = img.convert("RGBA")
    img = Image.alpha_composite(img, vig)
    img = img.convert("RGB")

    os.makedirs("output", exist_ok=True)
    fname = f"output/photo_day{day}_{emotion}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    img.save(fname, "JPEG", quality=95)
    print(f"✅ Photo image: {fname}")
    return fname


# ============================================================
# STEP 3: Create 16:9 reel image (1080x1920)
# ============================================================
def create_reel_image(data: dict, poet: dict, day: int) -> str:
    W, H    = 1080, 1920
    emotion = data.get("emotion","dard").lower()
    palette = dict(EMOTION_PALETTES.get(emotion, DEFAULT_PALETTE))
    for key,field in [("bg","bg_color"),("text","text_color"),("accent","accent_color")]:
        v = data.get(field,"")
        if v and v.startswith("#") and len(v)==7:
            palette[key] = v

    img  = Image.new("RGB",(W,H), color=palette["bg"])
    draw = ImageDraw.Draw(img)
    add_texture(draw, W, H, palette["accent"])
    draw_border(draw, palette, W, H)

    # Fonts — slightly larger for 16:9 tall canvas
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

    # HEADER
    draw_divider(draw, W//2, 100, palette["accent"], 80)
    center(f"-- {poet['name']} --", 130, font_poet, palette["accent"])
    center(f"Day {day} of 30   .   {poet['era']}", 185, font_day, palette["sub"])
    draw.line([(80,225),(W-80,225)], fill=palette["border"], width=1)

    # ROMAN SHER — vertically centered in middle zone
    lines       = data["sher_roman"].strip().split("\n")
    all_wrapped = []
    for line in lines:
        w2 = textwrap.wrap(line.strip(), width=34)
        all_wrapped.extend(w2 if w2 else [""])

    line_h  = int(fs*1.4)
    total_h = len(all_wrapped)*line_h
    # Center in zone 300–1400
    y_pos   = 300 + max(0,(1100-total_h)//2)
    for wline in all_wrapped:
        center(wline, y_pos, font_sher, palette["text"])
        y_pos += line_h

    # DIVIDER
    div_y = max(y_pos+40, 1430)
    draw_divider(draw, W//2, div_y, palette["accent"], 120)

    # ENGLISH TRANSLATION
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

    # FOOTER
    draw.line([(80,H-160),(W-80,H-160)], fill=palette["border"], width=1)
    draw_divider(draw, W//2, H-125, palette["accent"], 80)
    center(IG_HANDLE, H-85, font_brand, palette["sub"])

    # VIGNETTE
    vig = Image.new("RGBA",(W,H),(0,0,0,0))
    vd  = ImageDraw.Draw(vig)
    for i in range(80):
        vd.rectangle([i,i,W-i,H-i], outline=(0,0,0,int(i*1.8)))
    img = img.convert("RGBA")
    img = Image.alpha_composite(img, vig)
    img = img.convert("RGB")

    os.makedirs("output", exist_ok=True)
    fname = f"output/reel_day{day}_{emotion}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    img.save(fname, "JPEG", quality=95)
    print(f"✅ Reel image: {fname}")
    return fname


# ============================================================
# STEP 4: Edge TTS voiceover
# ============================================================
def generate_tts(text: str, output_path: str) -> bool:
    try:
        import asyncio
        import edge_tts
        VOICE = "hi-IN-FarhanNeural"

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
# STEP 5: Create Reel video — Ken Burns + TTS voice + music
# ============================================================
def get_random_music() -> str:
    """Pick a random track from the music/ folder."""
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
    try:
        from moviepy.editor import ImageClip, AudioFileClip, CompositeAudioClip
        import numpy as np

        # Load TTS voice
        tts_audio = AudioFileClip(tts_path)
        duration  = min(tts_audio.duration + 2, 59)

        # Load and mix background music
        music_path = get_random_music()
        if music_path:
            music = AudioFileClip(music_path).subclip(0, duration)
            music = music.volumex(0.18)          # Music at 18% volume
            tts_audio = tts_audio.volumex(1.0)   # Voice at full volume
            final_audio = CompositeAudioClip([music, tts_audio])
        else:
            final_audio = tts_audio

        # Ken Burns zoom on image
        clip = ImageClip(image_path, duration=duration)
        W, H = clip.size

        def make_frame(t):
            zoom  = 1 + 0.04*(t/duration)
            frame = clip.get_frame(t)
            from PIL import Image as PI
            fi    = PI.fromarray(frame)
            nw,nh = int(W*zoom), int(H*zoom)
            fi    = fi.resize((nw,nh), PI.LANCZOS)
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
# STEP 6: Upload image to imgbb (photos only)
# ============================================================
def upload_image(path: str) -> str:
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
# STEP 7: Upload video to catbox.moe + post as Reel
# ============================================================
def upload_video_to_catbox(video_path: str) -> str:
    """Upload video to catbox.moe and return public URL."""
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
    # Upload to catbox.moe for public URL
    print("☁️  Uploading video to catbox.moe...")
    video_url = upload_video_to_catbox(video_path)

    # Create media container
    container = requests.post(
        f"https://graph.instagram.com/v21.0/{INSTAGRAM_USER_ID}/media",
        data={
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "access_token": INSTAGRAM_ACCESS_TOKEN,
        }
    ).json()

    if "id" not in container:
        print(f"❌ Reel container: {container}")
        return False

    print(f"✅ Reel container: {container['id']}")

    # Step 4: Wait for processing
    for attempt in range(15):
        time.sleep(10)
        status = requests.get(
            f"https://graph.instagram.com/v21.0/{container['id']}",
            params={"fields":"status_code","access_token":INSTAGRAM_ACCESS_TOKEN}
        ).json()
        sc = status.get("status_code","")
        print(f"   [{attempt+1}] Status: {sc}")
        if sc == "FINISHED":
            break
        if sc == "ERROR":
            print(f"❌ Processing error: {status}")
            return False

    # Step 5: Publish
    publish = requests.post(
        f"https://graph.instagram.com/v21.0/{INSTAGRAM_USER_ID}/media_publish",
        data={
            "creation_id": container["id"],
            "access_token": INSTAGRAM_ACCESS_TOKEN,
        }
    ).json()

    if "id" in publish:
        print(f"🎉 Reel posted! {publish['id']}")
        return True

    print(f"❌ Reel publish: {publish}")
    return False


# ============================================================
# STEP 8: Post photo
# ============================================================
def post_photo(image_url: str, caption: str) -> bool:
    container = requests.post(
        f"https://graph.instagram.com/v21.0/{INSTAGRAM_USER_ID}/media",
        data={"image_url":image_url,"caption":caption,
              "access_token":INSTAGRAM_ACCESS_TOKEN}
    ).json()
    if "id" not in container:
        print(f"❌ Container: {container}")
        return False
    print(f"✅ Container: {container['id']}")
    time.sleep(5)
    publish = requests.post(
        f"https://graph.instagram.com/v21.0/{INSTAGRAM_USER_ID}/media_publish",
        data={"creation_id":container["id"],"access_token":INSTAGRAM_ACCESS_TOKEN}
    ).json()
    if "id" in publish:
        print(f"🎉 Photo posted! {publish['id']}")
        return True
    print(f"❌ Publish: {publish}")
    return False


# ============================================================
# STEP 9: Build caption
# ============================================================
def build_caption(data: dict, poet: dict) -> str:
    poet_tags  = POET_HASHTAGS.get(poet["name"],[])
    extra_tags = data.get("extra_hashtags",[])
    all_tags   = BASE_HASHTAGS + poet_tags[:2] + extra_tags[:1]
    hashtags   = " ".join([f"#{t}" for t in all_tags[:9]])
    return f"{data['caption']}\n\n{hashtags}"


# ============================================================
# PROGRESS
# ============================================================
def load_progress():
    if os.path.exists("progress.json"):
        with open("progress.json") as f: return json.load(f)
    return {"poet_index":0,"day":1,"total_posts":0}

def save_progress(p):
    with open("progress.json","w") as f: json.dump(p,f,indent=2)


# ============================================================
# MAIN
# ============================================================
def run():
    print(f"\n{'='*55}")
    print(f"Shayari Bot v4 -- {datetime.now().strftime('%Y-%m-%d %H:%M')} -- {POST_TYPE.upper()}")
    print(f"{'='*55}")

    p          = load_progress()
    poet_index = p["poet_index"] % len(POET_SCHEDULE)
    day        = p["day"]
    poet       = POET_SCHEDULE[poet_index]

    print(f"Poet: {poet['name']} | Day {day}/30 | Format: {get_format(day)} | Type: {POST_TYPE}")

    print("Generating authentic Shayari...")
    data    = generate_content(poet, day)
    caption = build_caption(data, poet)
    print(f"   Emotion: {data.get('emotion')} | Source: {data.get('source')}")

    if POST_TYPE == "photo":
        print("Creating 1:1 photo image...")
        image_path = create_photo_image(data, poet, day)
        image_url  = upload_image(image_path)
        success    = post_photo(image_url, caption)

    elif POST_TYPE == "reel":
        print("Creating 16:9 reel image...")
        reel_image = create_reel_image(data, poet, day)

        tts_text = data['sher_roman']
        audio_path = reel_image.replace(".jpg",".mp3")

        print("Generating TTS voiceover...")
        has_audio = generate_tts(tts_text, audio_path)

        if has_audio:
            print("Creating Reel video...")
            reel_path = create_reel_video(reel_image, audio_path)
        else:
            print("TTS failed -- creating silent Reel via ffmpeg...")
            reel_path = reel_image.replace(".jpg","_reel.mp4")
            os.system(
                f'ffmpeg -loop 1 -i "{reel_image}" -t 15 '
                f'-vf "scale=1080:1920" -c:v libx264 -pix_fmt yuv420p '
                f'"{reel_path}" -y -loglevel error'
            )

        if reel_path and os.path.exists(reel_path):
            success = upload_video_to_instagram(reel_path, caption)
        else:
            print("Reel failed -- falling back to photo...")
            image_path = create_photo_image(data, poet, day)
            image_url  = upload_image(image_path)
            success    = post_photo(image_url, caption)
    else:
        print(f"Unknown POST_TYPE: {POST_TYPE}")
        sys.exit(1)

    if success:
        if POST_TYPE == "photo":
            p["total_posts"] += 1
            if day >= 30:
                p["day"] = 1
                p["poet_index"] += 1
                print(f"30 days of {poet['name']} complete!")
            else:
                p["day"] = day+1
            save_progress(p)
        print(f"Done! Total posts: {p['total_posts']}")
    else:
        print("Failed.")
        sys.exit(1)

if __name__ == "__main__":
    run()
