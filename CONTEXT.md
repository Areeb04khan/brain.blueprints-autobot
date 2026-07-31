
# 🧠 Brain Blueprints Maintainer Context

This file is the private/operational memory for this repository. Keep it updated when the workflow, hosting provider, token process, or posting logic changes.

## What This Bot Does

This project automatically posts high-engagement psychological tactics, behavioral reads, and dark psychology content to Instagram using GitHub Actions.

It produces one kind of post:
- `reel`: a vertical 1080x1920 Reel video with text, multi-tier TTS voiceover, and background visual loops designed for 100% looping engagement.

The workflow runs three times daily via cron:
- `0 2,10,18 * * *` UTC

## Required Files

- `poster.py`: main bot logic with multi-tier AI and TTS failover engines.
- `.github/workflows/main.yml`: GitHub Actions schedule and runtime setup.
- `requirements.txt`: Python dependencies (pinned MoviePy `1.0.3` and OpenAI bridge).
- `progress.json`: posting state tracking.
- `.gitignore`: ignores local caches and generated output.
- `CONTEXT.md`: this maintainer note.
- `README.md`: public setup guide.

Do not commit local virtualenvs, generated videos, Python cache folders, or Aider/Codex history files.

## Runtime Architecture

The workflow does the following:

1. Checks out the repository.
2. Installs Python 3.11.
3. Installs Linux packages:
   - `fonts-dejavu-core`
   - `fonts-dejavu-extra`
   - `ffmpeg`
4. Installs Python packages from `requirements.txt`.
5. Restores `progress.json` using `actions/cache`.
6. Runs `python poster.py`.
7. Saves `progress.json` back to the cache.

The job has `timeout-minutes: 25` so external API problems cannot leave the workflow running indefinitely.

## Important Environment Variables

Required GitHub Actions secrets:

- `GEMINI_API_KEY`: Google Gemini API key (Tier 1 AI).
- `OPENROUTER_API_KEY`: OpenRouter API key (Tier 2 AI & TTS Fallback).
- `GROQ_API_KEY`: Groq API key (Tier 3 AI & TTS Fallback).
- `NVIDIA_API_KEY`: NVIDIA NIM API key (Tier 4 AI Fallback).
- `ELEVENLABS_API_KEY`: ElevenLabs API key (Tier 1 TTS Voiceover).
- `INSTAGRAM_ACCESS_TOKEN`: Instagram OAuth access token used by the Graph API.
- `INSTAGRAM_USER_ID`: Instagram account id used in Graph API publishing endpoints.
- `PEXELS_API_KEY`: Free API key from Pexels Developer Portal.
- `UNSPLASH_ACCESS_KEY`: Free Access Key from Unsplash Developer Portal.

Workflow environment values:
- `POST_TYPE`: `reel`
- `MEDIA_HOST`: `tempfile`

## Why It Is Built This Way

GitHub Actions is used because it gives free scheduled automation and avoids running a server.

A **Multi-Tier AI & TTS Failover Architecture** is used to ensure 100% uptime. If Gemini experiences 503 capacity errors or rate limits, the script instantly cascades through OpenRouter, Groq, and NVIDIA NIM without wasting GitHub Action minutes on sleeping delays. Similarly, TTS cascades from ElevenLabs to Groq, OpenRouter, and finally Edge-TTS.

MoviePy and FFmpeg are used for Reels because Instagram requires video files with synced audio tracks and custom text overlays.

TempFile.org is used as the default media host because the Instagram Graph API requires a public HTTPS URL for video ingestion.

## How `poster.py` Works

High-level flow:

1. Validate required environment secrets and API keys.
2. Query the multi-tier AI chain to generate psychological hooks and script content.
3. Fetch portrait background videos or photos using Pexels or Unsplash.
4. Generate audio voiceovers using the multi-tier TTS failover chain.
5. Composite the final 1080x1920 vertical Reel video using MoviePy.
6. Upload generated media to the media host to acquire a public download link.
7. Create an Instagram media container (`REELS`).
8. Poll container processing status until completion.
9. Publish the container directly to Instagram (`@brain.blueprints`).

## OAuth Token Renewal / Repair Steps

When the workflow fails with an Instagram OAuth error like:

```text
Invalid OAuth access token - Cannot parse access token

```
or any similar token/authentication error, regenerate the Instagram OAuth token and update the GitHub secret.
Steps:
 1. Go to https://developers.facebook.com/apps/.
 2. Open the Meta app used by this bot.
 3. In the left menu, open Instagram -> API setup with Instagram business login.
 4. Find the connected Instagram Business/Creator account.
 5. Click Generate token.
 6. Log in as the Instagram account owner if prompted.
 7. Approve the requested permissions.
 8. Copy the generated access token exactly.
 9. Open the GitHub repository.
 10. Go to Settings -> Secrets and variables -> Actions.
 11. Update the INSTAGRAM_ACCESS_TOKEN repository secret.
 12. Re-run the workflow.
Important:
 * Copy only the token string.
 * Do not include quotes, Bearer prefixes, spaces, or line breaks.
 * Instagram long-lived access tokens usually need renewal about every 60 days.
## Common Errors And Fixes
### Invalid OAuth access token - Cannot parse access token
 * **Cause:** INSTAGRAM_ACCESS_TOKEN is missing, expired, or copied incorrectly.
 * **Fix:** Regenerate the OAuth token using the steps above and update the GitHub Actions secret.
### Missing required environment variable(s) or AI Key errors
 * **Cause:** One or more required GitHub secrets are missing.
 * **Fix:** Add or update GEMINI_API_KEY, OPENROUTER_API_KEY, GROQ_API_KEY, NVIDIA_API_KEY, ELEVENLABS_API_KEY, INSTAGRAM_ACCESS_TOKEN, and INSTAGRAM_USER_ID under repository Settings -> Secrets and variables -> Actions.
### Instagram says media cannot be fetched
 * **Cause:** Instagram could not download the hosted video URL.
 * **Fix:** Open the logged media URL in a private browser window to confirm accessibility. If blocked, check network permissions or media hosting status.
### MoviePy video render failure
 * **Cause:** Incompatible package versions or missing FFmpeg packages.
 * **Fix:** Confirm moviepy==1.0.3 and ffmpeg are correctly installed via the workflow file.
## Changing The Bot
 * **Change posting times:** Edit cron values in .github/workflows/main.yml.
 * **Change Instagram handle:** Edit IG_HANDLE in poster.py.
 * **Change psychology topic/prompt:** Edit the prompt string inside generate_content in poster.py.
## Commit Notes
When making operational fixes, update both documentation files if relevant:
 * CONTEXT.md for maintainer details and lessons learned.
 * README.md for public replication instructions.
```
