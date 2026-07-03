# ⚡ Quick Fix Guide: Workflow Hang Issue

**Problem:** Workflow runs for hours showing "processing" without completing  
**Solution:** Update `poster.py` with v4.2.1 (improved timeout handling)  
**Time to Apply:** 5 minutes  
**Cost:** ₹0 (Free)

---

## 🎯 Step-by-Step Fix

### **Step 1: Get the Fixed File**
Download `poster.py` from the outputs folder (already fixed and ready to use).

### **Step 2: Update Your GitHub Repo**

Open a terminal and run:

```bash
# Clone or navigate to your shayari-bot repo
cd ~/path/to/shayari-bot

# Copy the fixed file into your repo
# (Replace ~/Downloads/poster.py with actual path)
cp ~/Downloads/poster.py .

# Check what changed
git diff poster.py

# Stage, commit, and push
git add poster.py
git commit -m "Fix: Add timeout handling and improve logging (v4.2.1)"
git push origin master
```

### **Step 3: Test the Fix**

1. Go to your GitHub repo: `github.com/Areeb04khan/shayari-bot`
2. Click on **Actions** tab
3. Click **Daily Shayari Post** workflow
4. Click **Run workflow** button
5. Select **"photo"** from dropdown
6. Click **Run workflow**

**Expected Result:**
- Workflow starts and shows clear progress in logs
- Should complete in **30-60 seconds** (not hours!)
- Logs show step-by-step what's happening

### **Step 4: Watch the Logs**

Click on the running workflow to see logs. You should see:

```
☁️  Uploading video to catbox.moe...
   Creating Instagram media container...
✅ Container ID: [xxxxx]

⏳ Waiting for Instagram to process video...
   [1/20] Status: IN_PROGRESS
   [2/20] Status: IN_PROGRESS
   [3/20] Status: FINISHED
   ✅ Processing complete!

📤 Publishing Reel...
🎉 Reel posted! ID: [xxxxx]
✅ Progress saved. Total posts: [N]
✅ Completed successfully.
```

---

## 🔍 Troubleshooting

### **Workflow Still Hangs**

**Check 1: Is your Instagram access token valid?**
- If expired, you'll see: `❌ Instagram error: unauthorized`
- **Fix:** Regenerate token from Meta Developer Console and update GitHub Secrets

**Check 2: Are your secrets set in GitHub?**
- Go to repo Settings → Secrets and variables → Actions
- Verify these exist:
  - `GEMINI_API_KEY`
  - `INSTAGRAM_ACCESS_TOKEN`
  - `INSTAGRAM_USER_ID`
  - `IMGBB_API_KEY`

**Check 3: Is the internet connection working?**
- GitHub Actions runs on cloud servers
- Very unlikely to fail, but if you see timeout errors repeatedly, it might be a network issue

### **Workflow Runs But Doesn't Post**

**Check the logs for:**
```
❌ Instagram error: [message]
```

| Error Message | Meaning | Fix |
|---|---|---|
| `unauthorized` | Token expired | Regenerate token (expires every 60 days) |
| `rate_limit_exceeded` | Too many requests | Wait a few minutes and try again |
| `invalid_access_token` | Token is corrupted | Regenerate token |
| `No container ID received` | Invalid image/video format | Check if IMGBB or catbox is down |
| `Publish failed: ...` | Container wasn't ready | This is expected — workflow retries automatically |

---

## 📊 What Changed (Technical)

### **Main Changes:**

1. **Added `timeout=15` to all API calls**
   - Prevents infinite waits if Instagram API is slow
   - Workflow fails cleanly instead of hanging

2. **Better error detection**
   - Checks for `"error"` key in API responses first
   - Gives you the exact error message (e.g., "unauthorized")

3. **Improved polling loop**
   - Now 20 attempts instead of 15 (200s instead of 150s max wait)
   - Clear logging at each attempt
   - Continues with warning if processing takes >200s (better than hanging)

4. **Better logging**
   - Each step shows progress markers (☁️ ⏳ 📤 🎉)
   - Polling shows attempt number: `[1/20] [2/20]` etc.
   - Makes it easy to see where code is stuck

### **Old Code (Problem):**
```python
for attempt in range(15):
    time.sleep(10)
    status = requests.get(...).json()  # ❌ No timeout
    sc = status.get("status_code","")
    if sc == "FINISHED":
        break
    if sc == "ERROR":
        return False
    # ❌ If status is IN_PROGRESS, loop continues silently
    # No indication of progress, no timeout, no clear error message
```

### **New Code (Fixed):**
```python
for attempt in range(1, max_attempts + 1):
    time.sleep(10)
    
    try:
        status_response = requests.get(..., timeout=10).json()  # ✅ Timeout added
    except requests.exceptions.Timeout:
        print(f"   [{attempt}/{max_attempts}] Status check timeout (retrying...)")  # ✅ Log it
        continue
    except Exception as e:
        print(f"   [{attempt}/{max_attempts}] Status check error: {e}")  # ✅ Log error
        continue

    if "error" in status_response:  # ✅ Check for API errors
        print(f"❌ Instagram error: {status_response.get('error')}")
        return False

    status_code = status_response.get("status_code", "")
    print(f"   [{attempt}/{max_attempts}] Status: {status_code}")  # ✅ Show progress

    if status_code == "FINISHED":
        finished = True
        break
    elif status_code == "ERROR":
        return False
```

**Key differences:**
- ✅ Timeout on every request (prevents infinite hangs)
- ✅ Clear progress logging at each attempt
- ✅ Error handling for API failures
- ✅ Explicit exit if processing times out (with warning, not silent failure)

---

## ✅ Verification Checklist

After applying the fix:

- [ ] Downloaded `poster.py` from outputs
- [ ] Replaced old file in your GitHub repo
- [ ] Committed and pushed changes
- [ ] Triggered workflow manually (photo test)
- [ ] Workflow completed in <2 minutes (not hours!)
- [ ] Logs show clear step-by-step progress
- [ ] Photo was posted to Instagram

---

## 🆘 Still Having Issues?

If the workflow still hangs after applying this fix:

1. **Check the last line in the logs** — tell me exactly what it says
2. **Check your Instagram token** — verify it's not expired
3. **Check GitHub Secrets** — make sure all 4 are set correctly
4. **Check if IMGBB or catbox is down** — try uploading a file to their sites manually

Then share the exact error message and I'll help debug!

---

## 📞 Support

Questions about the fix? I can explain:
- How timeouts work
- Why polling was hanging
- How error handling works
- How to debug if issues persist
- Anything else about the code!

Just ask.
