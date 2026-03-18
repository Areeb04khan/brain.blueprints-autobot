"""
Shayari Instagram Bot v3
- Real, authentic Shayari quoted from original poets
- Emotion-driven dark visual themes
- Hook-first captions designed for engagement
- Google TTS for Reel voiceover
- Photo at 8 AM IST, Reel at 7 PM IST via GitHub Actions
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
GOOGLE_TTS_API_KEY     = ""  # Not needed — using Edge TTS (free)
POST_TYPE              = os.environ.get("POST_TYPE", "photo")
IG_HANDLE              = "@ak_apak"

# Font paths
FONT_URDU   = "/usr/share/fonts/truetype/noto/NotoNastaliqUrdu-Regular.ttf"
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
# FORMAT ROTATION
# ============================================================
FORMAT_MAP = {
    1:"couplet", 2:"one-liner", 3:"couplet", 4:"longer", 5:"couplet",
    6:"one-liner", 7:"longer", 8:"couplet", 9:"one-liner", 10:"couplet",
    11:"longer", 12:"couplet", 13:"one-liner", 14:"longer", 15:"couplet",
    16:"one-liner", 17:"couplet", 18:"longer", 19:"couplet", 20:"one-liner",
    21:"longer", 22:"couplet", 23:"one-liner", 24:"couplet", 25:"longer",
    26:"couplet", 27:"one-liner", 28:"longer", 29:"couplet", 30:"one-liner",
}

def get_format(day): return FORMAT_MAP.get(day, "couplet")

# ============================================================
# EMOTION PALETTES — all dark backgrounds
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
    "Aaj ke waqt mein bhi kitna sach lagta hai yeh — sochna.",
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
3. Roman Urdu transliteration only of the sher
4. Original Urdu script of the sher only
5. English translation: MAX 1 LINE. Poetic, not literal.
6. Source collection if known (e.g. Diwan-e-Ghalib)

EMOTION: pick one from [ishq, dard, intezaar, yaad, tanhai, gussa, falsafa, umeed, zindagi, maut]

COLORS (dark backgrounds only):
bg_color: very dark hex matching emotion
text_color: soft light hex for readability
accent_color: vivid accent hex

CAPTION — engineered for maximum engagement:
Line 1 - HOOK: Start mid-thought, never start with poet name. Create instant curiosity.
Line 2-3 - STORY: Real intimate fact about poet's life tied to this sher. Like a secret.
Line 4 - GHAZAL: If from a ghazal, include 2-3 more real couplets labeled clearly.
Line 5 - TAG TRIGGER (copy exactly): "{tag_trigger}"

Return ONLY valid JSON, no markdown:
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
    raw = response.text.strip().replace("```json","").replace("```","").strip()
    return json.loads(raw)


# ============================================================
# STEP 2: Border
# ============================================================
def draw_border(draw, p, W, H):
    draw.rectangle([20,20,W-20,H-20], outline=p["border"], width=2)
    draw.rectangle([32,32,W-32,H-32], outline=p["border"], width=1)
    draw.rectangle([40,40,W-40,H-40], outline=p["accent"], width=1)
    for cx,cy in [(20,20),(W-20,20),(20,H-20),(W-20,H-20)]:
        s=10
        draw.polygon([(cx,cy-s),(cx+s,cy),(cx,cy+s),(cx-s,cy)],fill=p["accent"])
        draw.ellipse([cx-3,cy-3,cx+3,cy+3],fill=p["border"])
    for mx,my in [(W//2,20),(W//2,H-20),(20,H//2),(W-20,H//2)]:
        draw.ellipse([mx-4,my-4,mx+4,my+4],fill=p["border"])
    draw.rectangle([40,40,W-40,170],outline=p["border"],width=1)
    draw.rectangle([40,H-170,W-40,H-40],outline=p["border"],width=1)
    draw.line([(65,110),(W-65,110)],fill=p["border"],width=1)
    draw.line([(65,H-110),(W-65,H-110)],fill=p["border"],width=1)


# ============================================================
# STEP 3: Divider ornament
# ============================================================
def draw_divider(draw, cx, cy, color, w=100):
    draw.line([(cx-w,cy),(cx-14,cy)],fill=color,width=1)
    draw.line([(cx+14,cy),(cx+w,cy)],fill=color,width=1)
    s=7
    draw.polygon([(cx,cy-s),(cx+s,cy),(cx,cy+s),(cx-s,cy)],outline=color)
    draw.ellipse([cx-2,cy-2,cx+2,cy+2],fill=color)


# ============================================================
# STEP 4: Create image
# ============================================================
def create_image(data: dict, poet: dict, day: int) -> str:
    W, H    = 1080, 1080
    emotion = data.get("emotion","dard").lower()
    palette = dict(EMOTION_PALETTES.get(emotion, DEFAULT_PALETTE))

    # Allow Gemini color overrides
    for key, field in [("bg","bg_color"),("text","text_color"),("accent","accent_color")]:
        v = data.get(field,"")
        if v and v.startswith("#") and len(v)==7:
            palette[key] = v

    img  = Image.new("RGB",(W,H),color=palette["bg"])
    draw = ImageDraw.Draw(img)

    # Subtle noise texture
    ink = tuple(int(palette["accent"][i:i+2],16) for i in (1,3,5))
    for _ in range(600):
        x,y = random.randint(0,W), random.randint(0,H)
        r   = random.randint(0,1)
        draw.ellipse([x-r,y-r,x+r,y+r], fill=(*ink, random.randint(4,15)))

    draw_border(draw, palette, W, H)

    # Fonts
    try:
        font_poet  = ImageFont.truetype(FONT_SERIF, 28)
        font_day   = ImageFont.truetype(FONT_ITALIC,17)
        font_trans = ImageFont.truetype(FONT_ITALIC,18)
        font_brand = ImageFont.truetype(FONT_SANS,  16)
        font_src   = ImageFont.truetype(FONT_ITALIC,15)
    except:
        font_poet=font_day=font_trans=font_brand=font_src=ImageFont.load_default()

    try:    font_urdu = ImageFont.truetype(FONT_URDU, 32)
    except: font_urdu = font_trans

    fmt = data.get("format","couplet")
    fs  = 48 if fmt=="one-liner" else (42 if fmt=="couplet" else 36)
    try:    font_sher = ImageFont.truetype(FONT_SERIF, fs)
    except: font_sher = font_poet

    def center(text, y, font, color):
        bbox = draw.textbbox((0,0),text,font=font)
        tw   = bbox[2]-bbox[0]
        draw.text(((W-tw)/2, y), text, font=font, fill=color)

    # HEADER
    draw_divider(draw, W//2, 65, palette["accent"], 60)
    center(f"-- {poet['name']} --", 85, font_poet, palette["accent"])
    center(f"Day {day} of 30   .   {poet['era']}", 128, font_day, palette["sub"])
    draw.line([(65,162),(W-65,162)], fill=palette["border"], width=1)

    # ROMAN SHER — zone 178–560 (40%)
    lines       = data["sher_roman"].strip().split("\n")
    all_wrapped = []
    for line in lines:
        w2 = textwrap.wrap(line.strip(), width=38)
        all_wrapped.extend(w2 if w2 else [""])

    line_h  = int(fs*1.35)
    total_h = len(all_wrapped)*line_h
    y_pos   = 178 + max(0,(382-total_h)//2)
    for wline in all_wrapped:
        center(wline, y_pos, font_sher, palette["text"])
        y_pos += line_h

    # DIVIDER 1
    draw_divider(draw, W//2, 572, palette["accent"])

    # URDU SCRIPT — zone 585–755 (30%)
    urdu = data.get("sher_urdu","")
    if urdu:
        ul      = [l.strip() for l in urdu.strip().split("\n") if l.strip()][:4]
        ulh     = min(46, 170//max(len(ul),1))
        total_u = len(ul)*ulh
        y_pos   = 585+max(0,(170-total_u)//2)
        for line in ul:
            bbox = draw.textbbox((0,0),line,font=font_urdu)
            tw   = bbox[2]-bbox[0]
            draw.text(((W-tw)/2,y_pos),line,font=font_urdu,fill=palette["sub"])
            y_pos += ulh

    # DIVIDER 2
    draw_divider(draw, W//2, 762, palette["accent"])

    # ENGLISH TRANSLATION — zone 775–890 (30%)
    trans   = f'"{data["english_translation"]}"'
    tlines  = textwrap.wrap(trans, width=54)
    tlh     = 26
    total_t = len(tlines)*tlh
    y_pos   = 778+max(0,(112-total_t)//2)
    for line in tlines:
        center(line, y_pos, font_trans, palette["accent"])
        y_pos += tlh

    src = data.get("source","")
    if src and src.lower()!="unknown":
        center(f"-- {src}", y_pos+6, font_src, palette["sub"])

    # FOOTER
    draw.line([(65,908),(W-65,908)],fill=palette["border"],width=1)
    draw_divider(draw, W//2, 935, palette["accent"], 60)
    center(IG_HANDLE, 962, font_brand, palette["sub"])

    # VIGNETTE
    vig  = Image.new("RGBA",(W,H),(0,0,0,0))
    vd   = ImageDraw.Draw(vig)
    for i in range(80):
        vd.rectangle([i,i,W-i,H-i],outline=(0,0,0,int(i*1.8)))
    img = img.convert("RGBA")
    img = Image.alpha_composite(img,vig)
    img = img.convert("RGB")

    os.makedirs("output",exist_ok=True)
    filename = f"output/shayari_day{day}_{emotion}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    img.save(filename,"JPEG",quality=95)
    print(f"✅ Image: {filename} | Emotion: {emotion} | Format: {fmt}")
    return filename


# ============================================================
# STEP 5: Edge TTS (free, no API key needed)
# ============================================================
def generate_tts(text: str, output_path: str) -> bool:
    try:
        import asyncio
        import edge_tts

        # Best Urdu/Hindi male voice available in Edge TTS
        VOICE = "ur-PK-AsadNeural"  # Urdu male — deep and clear

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
# STEP 6: Create Reel
# ============================================================
def create_reel(image_path: str, audio_path: str) -> str:
    try:
        from moviepy.editor import ImageClip, AudioFileClip
        import numpy as np

        audio    = AudioFileClip(audio_path)
        duration = min(audio.duration+2, 30)
        clip     = ImageClip(image_path, duration=duration)
        W, H     = clip.size

        def make_frame(t):
            zoom = 1+0.05*(t/duration)
            f    = clip.get_frame(t)
            from PIL import Image as PI
            fi   = PI.fromarray(f)
            nw,nh= int(W*zoom),int(H*zoom)
            fi   = fi.resize((nw,nh),PI.LANCZOS)
            l,tp = (nw-W)//2,(nh-H)//2
            fi   = fi.crop((l,tp,l+W,tp+H))
            return np.array(fi)

        video     = clip.fl(lambda gf,t: make_frame(t)).set_audio(audio)
        reel_path = image_path.replace(".jpg","_reel.mp4")
        video.write_videofile(reel_path,fps=24,codec="libx264",
                              audio_codec="aac",verbose=False,logger=None)
        print(f"✅ Reel: {reel_path}")
        return reel_path
    except Exception as e:
        print(f"❌ Reel failed: {e}")
        return None


# ============================================================
# STEP 7: Upload to imgbb
# ============================================================
def upload_image(path: str) -> str:
    with open(path,"rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    result = requests.post("https://api.imgbb.com/1/upload",
                           data={"key":IMGBB_API_KEY,"image":data}).json()
    if result.get("success"):
        url = result["data"]["url"]
        print(f"✅ Uploaded: {url}")
        return url
    raise Exception(f"imgbb failed: {result}")


# ============================================================
# STEP 8: Build caption
# ============================================================
def build_caption(data: dict, poet: dict) -> str:
    poet_tags  = POET_HASHTAGS.get(poet["name"],[])
    extra_tags = data.get("extra_hashtags",[])
    all_tags   = BASE_HASHTAGS + poet_tags[:2] + extra_tags[:1]
    hashtags   = " ".join([f"#{t}" for t in all_tags[:9]])
    return f"{data['caption']}\n\n{hashtags}"


# ============================================================
# STEP 9: Post photo
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
# STEP 10: Post Reel
# ============================================================
def post_reel(video_path: str, caption: str) -> bool:
    with open(video_path,"rb") as f:
        vdata = base64.b64encode(f.read()).decode("utf-8")
    result = requests.post("https://api.imgbb.com/1/upload",
                           data={"key":IMGBB_API_KEY,"image":vdata}).json()
    if not result.get("success"):
        print(f"❌ Video upload: {result}")
        return False
    video_url = result["data"]["url"]
    container = requests.post(
        f"https://graph.instagram.com/v21.0/{INSTAGRAM_USER_ID}/media",
        data={"video_url":video_url,"media_type":"REELS",
              "caption":caption,"access_token":INSTAGRAM_ACCESS_TOKEN}
    ).json()
    if "id" not in container:
        print(f"❌ Reel container: {container}")
        return False
    print(f"✅ Reel container: {container['id']}")
    for _ in range(12):
        time.sleep(10)
        status = requests.get(
            f"https://graph.instagram.com/v21.0/{container['id']}",
            params={"fields":"status_code","access_token":INSTAGRAM_ACCESS_TOKEN}
        ).json()
        sc = status.get("status_code")
        print(f"   Processing: {sc}")
        if sc=="FINISHED": break
    publish = requests.post(
        f"https://graph.instagram.com/v21.0/{INSTAGRAM_USER_ID}/media_publish",
        data={"creation_id":container["id"],"access_token":INSTAGRAM_ACCESS_TOKEN}
    ).json()
    if "id" in publish:
        print(f"🎉 Reel posted! {publish['id']}")
        return True
    print(f"❌ Reel publish: {publish}")
    return False


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
    print(f"Shayari Bot v3 -- {datetime.now().strftime('%Y-%m-%d %H:%M')} -- {POST_TYPE.upper()}")
    print(f"{'='*55}")

    p          = load_progress()
    poet_index = p["poet_index"] % len(POET_SCHEDULE)
    day        = p["day"]
    poet       = POET_SCHEDULE[poet_index]

    print(f"Poet: {poet['name']} | Day {day}/30 | Format: {get_format(day)} | Type: {POST_TYPE}")

    print("Generating authentic Shayari...")
    data    = generate_content(poet, day)
    print(f"   Emotion: {data.get('emotion')} | Source: {data.get('source')}")

    print("Creating image...")
    image_path = create_image(data, poet, day)
    caption    = build_caption(data, poet)

    if POST_TYPE == "photo":
        image_url = upload_image(image_path)
        success   = post_photo(image_url, caption)

    elif POST_TYPE == "reel":
        tts_text   = f"{data['sher_roman']}\n\n{data['english_translation']}"
        audio_path = image_path.replace(".jpg",".mp3")

        print("Generating TTS voiceover...")
        has_audio = generate_tts(tts_text, audio_path)

        if has_audio:
            print("Creating Reel with voiceover...")
            reel_path = create_reel(image_path, audio_path)
        else:
            print("No TTS key -- creating silent Reel via ffmpeg...")
            reel_path = image_path.replace(".jpg","_reel.mp4")
            os.system(f'ffmpeg -loop 1 -i "{image_path}" -t 15 -vf "scale=1080:1080" -c:v libx264 -pix_fmt yuv420p "{reel_path}" -y -loglevel error')

        if reel_path and os.path.exists(reel_path):
            success = post_reel(reel_path, caption)
        else:
            print("Reel failed -- falling back to photo...")
            image_url = upload_image(image_path)
            success   = post_photo(image_url, caption)
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
