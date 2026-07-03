# Shayari Bot Maintainer Context

This file is the private/operational memory for this repository. Keep it updated when the workflow, hosting provider, token process, or posting logic changes.

## What This Bot Does

This project automatically posts Shayari content to Instagram using GitHub Actions.

It produces two kinds of posts:

- `photo`: a square 1080x1080 image post.
- `reel`: a vertical 1080x1920 Reel video with text, Urdu TTS voiceover, and background music.

The workflow runs twice daily:

- Morning photo: `30 2 * * *` UTC, about 8:00 AM IST.
- Evening reel: `30 13 * * *` UTC, about 7:00 PM IST.

The same generated Shayari is intended to be used for both the photo and the reel on the same day. The photo run saves the generated content to `progress.json`, and the reel run reuses it.

## Required Files

- `poster.py`: main bot logic.
- `.github/workflows/main.yml`: GitHub Actions schedule and runtime setup.
- `requirements.txt`: Python dependencies.
- `progress.json`: posting state and duplicate guard.
- `music/`: background MP3 files used for Reels.
- `.gitignore`: ignores local caches and generated output.
- `CONTEXT.md`: this maintainer note.
- `README.md`: public setup guide.

Do not commit local virtualenvs, generated images/videos, Python cache folders, or Aider/Codex history files.

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
6. Determines `POST_TYPE` from either manual workflow input or the cron trigger.
7. Runs `python poster.py`.
8. Saves `progress.json` back to the cache.

The job has `timeout-minutes: 25` so external API problems cannot leave the workflow running indefinitely.

## Important Environment Variables

Required GitHub Actions secrets:

- `GEMINI_API_KEY`: Google Gemini API key for generating structured Shayari content.
- `INSTAGRAM_ACCESS_TOKEN`: Instagram OAuth access token used by the Graph API.
- `INSTAGRAM_USER_ID`: Instagram account id used in Graph API publishing endpoints.

Workflow environment values:

- `POST_TYPE`: `photo` or `reel`.
- `MEDIA_HOST`: currently `tempfile`.
- `MAX_RETRIES`: currently `2`.
- `RETRY_DELAY_SECONDS`: currently `60`.

Optional values:

- `CLOUDINARY_URL`: required only if `MEDIA_HOST=cloudinary`.
- `CATBOX_USERHASH`: optional only if `MEDIA_HOST=catbox`.

## Why It Is Built This Way

GitHub Actions is used because it gives free scheduled automation and avoids running a server.

Gemini is used to generate structured content because the bot needs more than plain text. It asks for Roman text, Urdu text, English translation, caption, emotion, colors, source, and hashtags in JSON form.

Pillow is used for images because the designs are deterministic and do not need a browser or frontend runtime.

Edge TTS is used for Reels because it can generate Urdu voiceover without a paid TTS service.

MoviePy and FFmpeg are used for Reels because Instagram needs video files, not just images.

TempFile.org is currently used as the default media host because Instagram Graph API needs a public HTTPS URL for each image/video. Catbox started returning `Invalid uploader`, and TempFile returned usable direct download URLs without requiring a new secret.

Cloudinary support exists because it is the best durable long-term option. Use it if TempFile becomes unreliable or if permanent hosted media URLs are preferred.

## How `poster.py` Works

High-level flow:

1. Validate required secrets.
2. Load `progress.json`.
3. Pick the current poet from `POET_SCHEDULE`.
4. Pick a format from `FORMAT_WEIGHTS`.
5. Generate or reuse Shayari content:
   - Photo runs usually call Gemini.
   - Reel runs reuse `today_content` from `progress.json` when available.
6. Build an Instagram caption with hashtags and a disclaimer.
7. Create the media:
   - Photo: `create_photo_image`.
   - Reel: `create_reel_image`, `generate_tts`, then `create_reel_video`.
8. Upload generated media to the configured media host.
9. Create an Instagram media container.
10. Publish the container.
11. Save progress only after successful posting.

## Progress Behavior

`progress.json` tracks:

- `poet_index`
- `total_posts`
- `last_post_date`
- `last_post_type`
- `status`
- `today_content`

The duplicate guard checks if the same `POST_TYPE` has already posted successfully on the current UTC date. If yes, it skips.

Photo success:

- Saves `today_content`.
- Advances `poet_index`.

Reel success:

- Reuses `today_content`.
- Clears `today_content` after posting.
- Does not advance `poet_index`.

## OAuth Token Renewal / Repair Steps

When the workflow fails with an Instagram OAuth error like:

```text
Invalid OAuth access token - Cannot parse access token
```

or any similar token/authentication error, regenerate the Instagram OAuth token and update the GitHub secret.

Steps:

1. Go to https://developers.facebook.com/apps/.
2. Open the Meta app used by this bot.
3. In the left menu, open `Instagram` -> `API setup with Instagram business login`.
4. Find the connected Instagram Business/Creator account.
5. Click `Generate token`.
6. Log in as the Instagram account owner if prompted.
7. Approve the requested permissions.
8. Copy the generated access token exactly.
9. Open the GitHub repository.
10. Go to `Settings` -> `Secrets and variables` -> `Actions`.
11. Update the `INSTAGRAM_ACCESS_TOKEN` repository secret.
12. Re-run the `Daily Shayari Post` workflow.

Important:

- Copy only the token string.
- Do not include quotes.
- Do not prefix it with `Bearer`.
- Do not add spaces or line breaks.
- Instagram long-lived access tokens usually need renewal about every 60 days.

Optional verification:

```bash
curl "https://graph.instagram.com/me?fields=id,username&access_token=YOUR_TOKEN"
```

Expected response should include the Instagram account `id` and `username`.

## Common Errors And Fixes

### `Invalid OAuth access token - Cannot parse access token`

Cause: `INSTAGRAM_ACCESS_TOKEN` is missing, expired, copied incorrectly, or is the wrong token type.

Fix: regenerate the OAuth token using the steps above and update the GitHub Actions secret.

### `Missing required environment variable(s)`

Cause: one or more required GitHub secrets are not set.

Fix: add or update `GEMINI_API_KEY`, `INSTAGRAM_ACCESS_TOKEN`, and `INSTAGRAM_USER_ID` under repository `Settings` -> `Secrets and variables` -> `Actions`.

### `catbox upload failed: Invalid uploader`

Cause: Catbox rejected the anonymous upload.

Fix: keep `MEDIA_HOST=tempfile`, or switch to `MEDIA_HOST=cloudinary` and add `CLOUDINARY_URL`.

### `tempfile upload failed`

Cause: TempFile.org may be temporarily down, rate-limited, or rejecting the file.

Fix options:

1. Re-run the workflow once.
2. Switch to Cloudinary for more reliable hosting.
3. If using Cloudinary, set `MEDIA_HOST=cloudinary` in the workflow and add `CLOUDINARY_URL` as a GitHub secret.

### Instagram says media cannot be fetched

Cause: Instagram could not download the hosted image/video URL.

Fix:

1. Open the logged media URL in a private browser window.
2. Confirm it downloads or displays without login.
3. If the URL is blocked or redirects strangely, switch media hosts.
4. Prefer Cloudinary for durable CDN URLs.

### Gemini returns invalid JSON

Cause: Gemini sometimes wraps JSON in markdown fences or returns malformed content.

Current mitigation: `poster.py` strips common markdown code fences before `json.loads`.

Fix if it repeats:

1. Re-run once.
2. Tighten the prompt in `generate_content`.
3. Add JSON repair or schema validation before using the response.

### Workflow appears stuck

Cause: external API calls, uploads, or video processing can be slow.

Current mitigation:

- GitHub job timeout is 25 minutes.
- Script retries are short: 2 attempts with 60 seconds delay.
- Upload and Instagram API calls have explicit timeouts.

Fix if it repeats:

1. Check which step consumed time in Actions logs.
2. If media upload is slow, change media host.
3. If Reel processing is slow, reduce video duration or check MoviePy/FFmpeg logs.

### Reel TTS fails

Cause: Edge TTS can fail due to network or service issues.

Current behavior: the script falls back to a silent Reel generated through FFmpeg.

Fix if it repeats:

1. Re-run the workflow.
2. Check if `edge-tts` changed behavior.
3. Pin or update `edge-tts` in `requirements.txt`.

### MoviePy is missing or video creation fails

Cause: dependency install issue or incompatible package behavior.

Current behavior: the script tries to fall back to a silent FFmpeg video.

Fix:

1. Confirm `moviepy==1.0.3` installed successfully.
2. Confirm `ffmpeg` installed in the workflow.
3. Re-run the workflow.

### Duplicate or wrong poet/content

Cause: `progress.json` state is stale or cache restore brought back unexpected state.

Fix:

1. Inspect `progress.json`.
2. Manually adjust `poet_index` if needed.
3. Clear or update the GitHub Actions cache if the wrong state keeps restoring.

## Changing The Bot

Change posting times:

- Edit cron values in `.github/workflows/main.yml`.

Change Instagram handle shown on images:

- Edit `IG_HANDLE` in `poster.py`.

Change poets:

- Edit `POET_SCHEDULE` in `poster.py`.

Change visual styling:

- Edit `EMOTION_PALETTES`, `create_photo_image`, or `create_reel_image`.

Change generated content style:

- Edit the prompt inside `generate_content`.
- Edit `FORMAT_WEIGHTS` for more couplets, four-liners, one-liners, or longer excerpts.

Change media host:

- `MEDIA_HOST=tempfile`: no extra secret, temporary URLs.
- `MEDIA_HOST=cloudinary`: durable URLs, requires `CLOUDINARY_URL`.
- `MEDIA_HOST=catbox`: available but not recommended due to previous `Invalid uploader` failures.

## Commit Notes

When making operational fixes, update both docs if relevant:

- `CONTEXT.md` for maintainer details and lessons learned.
- `README.md` for public replication instructions.
