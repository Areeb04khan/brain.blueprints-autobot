# CONTEXT.md
## Instagram Content Automation Platform
### Last Updated: March 2026 | Owner: Areeb Khan (@Areeb04khan)

---

## WHAT IS THIS PROJECT?

Two separate but related things:

### 1. Personal Shayari Bot (LIVE & RUNNING)
A fully automated Instagram bot for the account `@ak_apak` that:
- Posts **1 photo daily at 8:00 AM IST**
- Posts **1 Reel daily at 7:00 PM IST**
- Quotes real, authentic Shayari from classical and contemporary Urdu/Hindi poets
- Generates emotion-matched dark visual images
- Uses Edge TTS for voiceover + royalty-free background music
- Runs entirely on **GitHub Actions** (zero cost, zero maintenance)
- Repo: `github.com/Areeb04khan/shayari-bot` (private)

### 2. Web App Platform (IN DEVELOPMENT)
A web application that lets anyone automate their Instagram content.
- Users describe their niche via chat
- AI generates and posts content automatically
- No technical knowledge required
- Invite-only during testing phase
- Repo: TBD (new private repo on different GitHub account)

---

## SHAYARI BOT — COMPLETE TECHNICAL DETAILS

### GitHub Repo
- Account: `Areeb04khan`
- Repo: `shayari-bot` (private)
- Branch: `master`

### Files Structure
```
shayari-bot/
├── poster.py              # Main bot — all logic lives here
├── requirements.txt       # Python dependencies
├── progress.json          # Tracks current poet + day (cached by GitHub Actions)
├── music/                 # 45 royalty-free MP3 tracks for Reel background music
├── .github/
│   └── workflows/
│       ├── main.yaml          # Daily photo (8AM IST) + Reel (7PM IST)
│       └── token_reminder.yml # Creates GitHub Issue every 55 days for token renewal
└── CONTEXT.md             # This file
```

### GitHub Secrets (ALL REQUIRED)
| Secret Name | What It Is |
|---|---|
| `GEMINI_API_KEY` | Google AI Studio free API key |
| `INSTAGRAM_ACCESS_TOKEN` | Instagram Graph API token (expires every 60 days) |
| `INSTAGRAM_USER_ID` | `17841432775374724` (ak_apak's Instagram user ID) |
| `IMGBB_API_KEY` | imgbb.com free image hosting API key |

### Workflow Schedule
```yaml
- cron: '30 2 * * *'   # 8:00 AM IST — posts photo
- cron: '30 13 * * *'  # 7:00 PM IST — posts reel
```

### How POST_TYPE is Determined
The workflow checks the UTC hour to decide photo vs reel:
```bash
elif [ "$(date -u +%H)" -le "04" ]; then
  echo "type=photo"
else
  echo "type=reel"
fi
```
**Known bug:** This check uses `"02"` instead of `-le "04"` — needs fixing. When fixed, photo posts in the 2-4 AM UTC window (8-10 AM IST) and reel posts any other time.

### Content Pipeline (poster.py)
```
generate_content()     — Gemini 2.5 Flash generates real Shayari
      ↓
create_photo_image()   — PIL creates 1080x1080 dark themed image
create_reel_image()    — PIL creates 1080x1920 dark themed image
      ↓
generate_tts()         — Edge TTS reads sher aloud (random Hindi/Urdu voice)
get_random_music()     — Picks random track from music/ folder
create_reel_video()    — moviepy combines image + TTS + music with Ken Burns zoom
      ↓
upload_image()         — imgbb.com for photos
upload_video_to_catbox() — catbox.moe for reel videos
      ↓
post_photo()           — Instagram Graph API v21.0
upload_video_to_instagram() — Instagram Graph API v21.0 (REELS media type)
```

### Gemini Prompt Strategy
- Requests REAL, AUTHENTIC shers — not AI generated
- Detects emotion from: ishq, dard, intezaar, yaad, tanhai, gussa, falsafa, umeed, zindagi, maut
- Suggests dark color palette based on emotion
- Generates hook-first caption with tag trigger at the end
- Format rotates: one-liner / couplet / longer sher based on day number

### Emotion → Visual Palette
Each emotion maps to a unique dark color scheme:
- ishq: `#1a0010` (deep maroon)
- dard: `#0a0a1a` (dark navy)
- tanhai: `#060d0d` (dark teal)
- intezaar: `#0f0f0f` (charcoal)
- gussa: `#1a0500` (dark ember)
- falsafa: `#080818` (deep indigo)
- umeed: `#060f06` (dark forest)
- yaad: `#120c04` (dark sepia)
- zindagi: `#0a0a14` (dark slate)
- maut: `#050505` (near black)

### Poet Schedule (30 days each)
```python
POET_SCHEDULE = [
    {"name": "Mirza Ghalib",    "era": "1797-1869"},  # Day 1-30
    {"name": "Mir Taqi Mir",    "era": "1723-1810"},  # Day 31-60
    {"name": "Allama Iqbal",    "era": "1877-1938"},  # Day 61-90
    {"name": "Faiz Ahmed Faiz", "era": "1911-1984"},  # Day 91-120
    {"name": "Ahmad Faraz",     "era": "1931-2008"},  # Day 121-150
    {"name": "Parveen Shakir",  "era": "1952-1994"},  # Day 151-180
    {"name": "Sahir Ludhianvi", "era": "1921-1980"},  # Day 181-210
    {"name": "Gulzar",          "era": "1934-"    },  # Day 211-240
    {"name": "Rahat Indori",    "era": "1950-2020"},  # Day 241-270
    {"name": "Habib Jalib",     "era": "1928-1993"},  # Day 271-300
    {"name": "Josh Malihabadi", "era": "1898-1982"},  # Day 301-330
    {"name": "Wasi Shah",       "era": "1977-"    },  # Day 331-360
]
```

### Known Issues / Pending Fixes
1. **Workflow timing bug** — `"02"` needs to change to `-le "04"` in main.yaml post type detection
2. **TTS pronunciation** — Edge TTS still mispronounces some Roman Urdu words. Fix: pass `sher_urdu` (Urdu script) to TTS instead of `sher_roman`. Need to add `sher_urdu` back to Gemini prompt output.
3. **Contemporary poets** — Need to add more poets to POET_SCHEDULE: Javed Akhtar, Kumar Vishwas, Munawwar Rana, Bashir Badr, Nida Fazli, Anwar Masood, Wasi Shah (already there)

### Maintenance Schedule
| Task | Frequency | How |
|---|---|---|
| Renew Instagram Access Token | Every 60 days | Meta Developer → ShayariBot app → Generate token |
| Check GitHub Actions | Weekly | Actions tab — all should be green |
| Check Instagram Insights | Weekly | Best performing content |
| Verify poet switched | Every 30 days | Check Instagram profile |

### Token Renewal Steps
1. Login to friend's Facebook account (the Meta Developer account)
2. Go to developers.facebook.com
3. Open ShayariBot app
4. Go to Use Cases → Instagram API → API setup with Instagram login
5. Click "Generate token" next to ak_apak
6. Copy token
7. Go to GitHub repo Areeb04khan/shayari-bot → Settings → Secrets → Actions
8. Update INSTAGRAM_ACCESS_TOKEN

---

## WEB APP PLATFORM — REQUIREMENTS SUMMARY

### Tech Stack
- **Frontend:** React + Tailwind CSS → Vercel (free)
- **Backend:** Python FastAPI → Render.com (free tier)
- **Database:** PostgreSQL via Supabase (free tier)
- **Auth:** Google OAuth via Supabase
- **Email:** Resend.com (free: 3,000/month)
- **Scheduler:** APScheduler (in-process, inside FastAPI)
- **AI:** Gemini (free users' own key) / Claude (premium, owner's key)
- **TTS:** Edge TTS (free, no key needed)
- **Music:** Pre-downloaded royalty-free MP3s in repo

### Security Requirements
- AES-256 encryption for all API keys and Instagram tokens in DB
- Google SSO only — no passwords
- JWT sessions expire 24 hours
- HTTPS enforced everywhere
- Private GitHub repo always
- Invite-only during testing
- Rate limit: max 2 posts/day per user

### Freemium Model
- Free: User's own Gemini key, photos only, 3 themes
- Premium: Claude via owner's key, photos + reels, all themes, TBD price

### MVP Features
- Google SSO login
- Invite-only whitelist
- Conversational onboarding chat (niche, language, theme, schedule)
- Instagram OAuth connection
- Content generation (Gemini)
- Test post preview
- Manual + automatic posting
- Basic dashboard
- Failure notifications (user + owner)
- Token renewal reminder at day 50
- Terms of Service + Privacy Policy pages

### NOT in MVP
- Claude premium tier
- Payment system
- Analytics
- Multiple Instagram accounts
- Hindi UI
- Mobile app

### Database Tables
- `users` — google_id, email, name, tier, is_active
- `instagram_connections` — user_id, ig_user_id, access_token (encrypted), expires_at
- `user_config` — user_id, niche, language, theme, photo_time, reel_time, posting_mode, gemini_key (encrypted)
- `posts` — user_id, type, status, error_message, posted_at
- `error_logs` — user_id, error_type, message, stack_trace

---

## DOCUMENTS STATUS

| Document | Status |
|---|---|
| Requirements Document (.docx) | ✅ Done |
| CONTEXT.md (this file) | ✅ Done |
| Technical Architecture Doc | ⏳ To Do |
| Developer Setup Guide | ⏳ To Do |
| Deployment Guide | ⏳ To Do |
| API Documentation | ⏳ To Do |
| Environment Variables Guide | ⏳ To Do |
| User Guide | ⏳ To Do |
| Terms of Service | ⏳ To Do |
| Privacy Policy | ⏳ To Do |
| Security Policy | ⏳ To Do |
| CHANGELOG.md | ⏳ To Do |

---

## HOW TO USE THIS FILE WITH AI (Claude)

At the start of any new Claude session, paste this file and say:
**"Read this CONTEXT.md and continue working on my project."**

Claude will instantly have full context of everything — no re-explaining needed.

Keep this file updated as the project evolves. Add new decisions, fixes, and changes at the bottom under a dated section.

---

## CHANGE LOG

### March 2026 — Initial Setup
- Shayari bot built and deployed on GitHub Actions
- Photo + Reel posting working
- Edge TTS + music mixing implemented
- catbox.moe for video hosting
- Token renewal reminder workflow added
- Web app requirements gathered and documented
- Tech stack decided: FastAPI + React + Supabase + Vercel + Render
