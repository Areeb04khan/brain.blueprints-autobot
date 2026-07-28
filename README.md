
<div align="center">

# ✦ Instagram Shayari Bot v5.5 ✦

### A cinematic, retention-focused, fully automated poetry publishing engine.

![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-Automated-2088FF?style=for-the-badge&logo=github-actions&logoColor=white)
![Gemini](https://img.shields.io/badge/Gemini_2.5_Flash-AI_Content-8E75B2?style=for-the-badge&logo=google&logoColor=white)
![Pexels](https://img.shields.io/badge/Pexels-Video_&_Photo-05A081?style=for-the-badge)
![Unsplash](https://img.shields.io/badge/Unsplash-HD_Photos-000000?style=for-the-badge&logo=unsplash&logoColor=white)
![Instagram](https://img.shields.io/badge/Instagram-Graph_API-E4405F?style=for-the-badge&logo=instagram&logoColor=white)
![License](https://img.shields.io/badge/License-Attribution_Required-black?style=for-the-badge)

**Generate. Design. Host. Publish. Repeat.**

Turn a GitHub repository into an autonomous publishing studio that runs 100% on free APIs to curate poetry, fetch aesthetic stock media, synthesize voiceovers, edit Reels, and publish directly to Instagram.

</div>

---

## 🌙 What Makes Version 5.5 Different

Unlike simple text-posting scripts, this bot builds high-retention Instagram media designed for maximum reach, shares, and saves:

| Layer | Technology | Function |
|---|---|---|
| 🧠 **Content Brain** | Gemini 2.5 Flash | Generates authentic Shayari, Roman Urdu, Urdu script, English translations, and visual search terms. |
| 🖼️ **Photo Engine** | Unsplash + Pexels API | Fetches aesthetic high-res photography with translucent dark overlays for legibility. |
| 🎬 **Reel Studio** | Pexels + Unsplash + MoviePy | Composites 4K vertical motion video clips with timed text overlays and background music. |
| 🎙️ **Voice Layer** | Edge-TTS (`ur-PK-AsadNeural`) | Synthesizes realistic Urdu pronunciation for video narration. |
| 🔄 **Cross-Fallback** | Dual-Engine Architecture | Automatically fails over between Unsplash and Pexels if any API limit or network error occurs. |
| ☁️ **Media Bridge** | TempFile / Cloudinary | Serves temporary or permanent public URLs for Instagram Graph API ingestion. |
| 📡 **Publisher** | Instagram Graph API | Automates container creation, video processing status polling, and direct publishing. |
| 🕰️ **Scheduler** | GitHub Actions | Runs completely hands-free on daily crons. |

---

## 🧩 System Blueprint

```mermaid
flowchart TD
    A["GitHub Actions Schedule / Manual Run"] --> B{"POST_TYPE"}
    B -->|photo| C["Fetch Unsplash / Pexels Photo"]
    B -->|reel| D["Fetch Pexels / Unsplash Vertical Video"]
    C --> E["Apply Translucent Dark Tint + Overlay Text (Pillow)"]
    D --> F["Generate Native Urdu Audio (Edge-TTS)"]
    F --> G["Layer Background Music + Text Overlay (MoviePy)"]
    E --> H["Upload Public Media (TempFile / Cloudinary)"]
    G --> H
    H --> I["Create Instagram Media Container"]
    I --> J["Poll Container Processing (Reels)"]
    J --> K["Publish to Instagram"]
    K --> L["Update progress.json & Cycle Poet List"]

```
## 📂 Repository Layout
```text
.
├── .github/workflows/main.yml  # GitHub Actions schedule and environment setup
├── music/                      # Royalty-free instrumental MP3 tracks for Reels
├── poster.py                   # The core bot engine
├── progress.json               # Posting state tracking
├── requirements.txt            # Python dependencies
├── LICENSE                     # Attribution-Required License
└── README.md                   # System documentation

```
## 🚀 Quick Start Setup
### 1. Clone or Fork
```bash
git clone YOUR_REPO_URL
cd shayari-bot

```
### 2. Configure GitHub Secrets
Go to your repository:
Settings → Secrets and variables → Actions → New repository secret
| Secret Name | Required | Description |
|---|---|---|
| GEMINI_API_KEY | ✅ | Free API key from Google AI Studio. |
| INSTAGRAM_ACCESS_TOKEN | ✅ | Meta Graph API long-lived access token. |
| INSTAGRAM_USER_ID | ✅ | Connected Instagram Creator / Business ID. |
| PEXELS_API_KEY | ✅ | Free API key from Pexels Developer Portal. |
| UNSPLASH_ACCESS_KEY | ✅ | Free Access Key from Unsplash Developer Portal. |
| CLOUDINARY_URL | Optional | Required only if MEDIA_HOST=cloudinary. |
## 🕰️ Automated Schedule
The bot posts twice daily via GitHub Actions:
```yaml
- cron: '30 2 * * *'   # 8:00 AM IST - Static Photo
- cron: '30 13 * * *'  # 7:00 PM IST - Motion Reel

```
## 🧪 Local Testing
PowerShell (Windows):
```powershell
$env:GEMINI_API_KEY="your_key"
$env:INSTAGRAM_ACCESS_TOKEN="your_token"
$env:INSTAGRAM_USER_ID="your_user_id"
$env:PEXELS_API_KEY="your_pexels_key"
$env:UNSPLASH_ACCESS_KEY="your_unsplash_key"
$env:POST_TYPE="photo"
python -u poster.py

```
Bash (Linux / macOS):
```bash
export GEMINI_API_KEY="your_key"
export INSTAGRAM_ACCESS_TOKEN="your_token"
export INSTAGRAM_USER_ID="your_user_id"
export PEXELS_API_KEY="your_pexels_key"
export UNSPLASH_ACCESS_KEY="your_unsplash_key"
export POST_TYPE="photo"
python -u poster.py

```
---

## 🧾 License

This project is licensed under the **Attribution Required License**. See the full terms in the [LICENSE](LICENSE) file.

> **Attribution Requirement**  
> You are free to copy, modify, and distribute this software for personal or commercial automation, but visible credit to **Areeb Khan** is strictly required in derivative works or documentations.

---

<div align="center">

*Built for people who want poetry, automation, and aesthetics in the same room.*

</div>

