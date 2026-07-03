# Shayari Bot Context

## Current Working Setup

The GitHub Actions workflow runs `poster.py` twice per day:

- Morning photo post: `30 2 * * *` UTC, around 8:00 AM IST.
- Evening reel post: `30 13 * * *` UTC, around 7:00 PM IST.

Required GitHub Actions secrets:

- `GEMINI_API_KEY`
- `INSTAGRAM_ACCESS_TOKEN`
- `INSTAGRAM_USER_ID`

The workflow also sets:

- `MEDIA_HOST=tempfile`
- `MAX_RETRIES=2`
- `RETRY_DELAY_SECONDS=60`

`MEDIA_HOST=tempfile` is used because Catbox rejected uploads with `Invalid uploader`. TempFile returns a direct public download URL that Instagram can fetch during media publishing.

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
