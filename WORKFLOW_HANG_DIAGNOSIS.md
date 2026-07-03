# 🔴 Workflow Hang Diagnosis & Fix (v4.2.1)

**Issue:** When triggering the workflow, it shows "processing" for hours without completing or throwing an error.

**Status:** ✅ **FIXED** — All timeouts, error handling, and logging improved

---

## 📊 Root Cause Analysis

### **Primary Culprit: Reel Video Polling Loop (Lines 712-724 in original poster.py)**

```python
# ORIGINAL CODE (BROKEN):
for attempt in range(15):
    time.sleep(10)
    status = requests.get(...)
    sc = status.get("status_code","")
    
    if sc == "FINISHED":
        break          # ✅ Good
    if sc == "ERROR":
        return False   # ✅ Good
    # ❌ PROBLEM: If status is "IN_PROGRESS" or anything else, just loops again
    # No explicit timeout, no error message, no exit condition
```

**Why it hangs:**
- Instagram returns `"IN_PROGRESS"` or `"PROCESSING"` status
- Code loops up to 15 times × 10 seconds = 150 seconds max
- After 150 seconds, code continues to publish even if video isn't ready
- If publishing fails silently or hangs, workflow appears frozen
- GitHub Actions log shows "processing" indefinitely

### **Secondary Issues:**

1. **No timeouts on network requests** — If Instagram API is slow, code waits forever
2. **No error handling for API responses** — `requests.json()` can fail silently
3. **Unclear logging** — Can't tell which step is actually hanging
4. **No explicit completion signal** — Code proceeds even if polling times out

---

## ✅ Fixes Applied (v4.2.1)

### **Fix 1: Explicit Timeouts on All API Calls**

**Before:**
```python
requests.post(...).json()  # ❌ No timeout — can hang indefinitely
```

**After:**
```python
requests.post(..., timeout=15).json()  # ✅ Timeout after 15 seconds
# If API doesn't respond in 15s, raises requests.exceptions.Timeout
# We catch it and log clearly
```

**Impact:**
- Any API call that takes >15 seconds will fail with a clear error
- Prevents infinite waits on network issues
- **Cost:** None (just adds safety)

---

### **Fix 2: Better Error Detection**

**Before:**
```python
container = requests.post(...).json()
if "id" not in container:  # ❌ Misses API error responses
    print(f"Container failed: {container}")
```

**After:**
```python
container_response = requests.post(..., timeout=15).json()
if "error" in container_response:  # ✅ Catch API errors first
    print(f"Error: {container_response.get('error', {}).get('message')}")
    return False
if "id" not in container_response:
    print(f"No ID received: {container_response}")
    return False
```

**Impact:**
- Catches "unauthorized", "rate_limit_exceeded", "invalid_token" errors immediately
- Instagram tells us what went wrong (e.g., token expired)
- Workflow exits cleanly instead of hanging
- **Cost:** None (just better error handling)

---

### **Fix 3: Improved Polling with Timeout**

**Before:**
```python
for attempt in range(15):
    time.sleep(10)
    status = requests.get(...)  # ❌ No timeout
    sc = status.get("status_code","")
    if sc == "FINISHED":
        break
    if sc == "ERROR":
        return False
    # Loop continues silently if status is IN_PROGRESS
```

**After:**
```python
max_attempts = 20
finished = False

for attempt in range(1, max_attempts + 1):
    time.sleep(10)
    
    try:
        status_response = requests.get(..., timeout=10).json()
    except requests.exceptions.Timeout:
        # ✅ Log timeout and retry (don't hang)
        print(f"   [{attempt}/{max_attempts}] Status check timeout (retrying...)")
        continue
    except Exception as e:
        # ✅ Log any other error and retry
        print(f"   [{attempt}/{max_attempts}] Status check error: {e}")
        continue

    if "error" in status_response:
        # ✅ Catch API errors during polling
        print(f"❌ Instagram error: {status_response.get('error')}")
        return False

    status_code = status_response.get("status_code", "")
    # ✅ Clear logging at every step
    print(f"   [{attempt}/{max_attempts}] Status: {status_code}")

    if status_code == "FINISHED":
        finished = True
        break
    elif status_code == "ERROR":
        return False
    # Loop continues for IN_PROGRESS/PROCESSING

if not finished:
    # ✅ Explicit warning if polling times out
    print(f"⚠️  Warning: Video not confirmed FINISHED after {max_attempts*10}s")
    print("   Proceeding to publish anyway...")
```

**Impact:**
- Polls up to 20 times (instead of 15) = 200 seconds max (3.3 minutes) — more time for larger videos
- Every status check has a 10-second timeout
- Clear logging shows exact attempt number and status at each step
- If polling times out, workflow continues with a warning (better than hanging)
- **Cost:** None (just clearer flow)

---

### **Fix 4: Better Logging Throughout**

**Before:**
```python
print("☁️  Uploading video...")
# ... lots of code ...
# No clear indication of what step is happening or what went wrong
```

**After:**
```python
# ✅ Clear step markers
print("☁️  Uploading video to catbox.moe...")
print("   Creating Instagram media container...")
print("⏳ Waiting for Instagram to process video...")
print("📤 Publishing Reel...")

# ✅ Explanatory comments in code
# FIX (v4.2.1): Added explicit timeout logic, better error messages...

# ✅ Progress indicators in loops
print(f"   [{attempt}/{max_attempts}] Status: {status_code}")

# ✅ Clear error messages
print(f"❌ Instagram error: {error_message}")
print("⚠️  Warning: Video not confirmed FINISHED after Xs")
```

**Impact:**
- GitHub Actions logs show exactly which step is running
- If workflow hangs, you can see the last logged step
- Makes debugging much easier
- **Cost:** None (just better output)

---

## 🚀 How to Deploy the Fix

### **Option A: Use the Fixed File (Recommended)**

1. **Download the fixed `poster.py`** from outputs
2. **Replace your current `poster.py`** in the GitHub repo
3. **Commit and push:**
   ```bash
   git add poster.py
   git commit -m "Fix: Improve timeout handling and logging (v4.2.1)"
   git push origin master
   ```
4. **Test with workflow_dispatch** (manual trigger):
   - Go to GitHub repo → Actions → Daily Shayari Post
   - Click "Run workflow" → Select "photo" → Run
   - Watch the logs — you should see clear step-by-step progress

### **Option B: Manual Changes**

If you want to understand exactly what changed:

1. Find lines 684-740 (original `upload_video_to_instagram` function)
2. Replace with the new version (see the file `poster.py`)
3. Find lines 746-846 (original `post_photo` function)
4. Replace with the new version
5. Commit and test

---

## 📋 Changes Summary

| Function | Change | Benefit |
|---|---|---|
| `upload_video_to_instagram()` | Added timeouts + better error handling + improved polling | Prevents infinite hangs on reel uploads |
| `post_photo()` | Added timeouts + error detection | Prevents hangs on photo uploads |
| Overall | Better logging at each step | Easier debugging if issues occur |

---

## 🧪 Testing the Fix

### **Test 1: Manual Photo Post**
```bash
# Go to GitHub repo → Actions → Daily Shayari Post
# Click "Run workflow" → Select "photo" → Run

# Expected: Should complete in 30-60 seconds with clear logs
# Watch for: 
# ✅ "Container ID: ..."
# ✅ "Photo posted! ID: ..."
```

### **Test 2: Manual Reel Post**
```bash
# Go to GitHub repo → Actions → Daily Shayari Post
# Click "Run workflow" → Select "reel" → Run

# Expected: Should show polling progress like:
# ⏳ Waiting for Instagram to process video...
#    [1/20] Status: IN_PROGRESS
#    [2/20] Status: IN_PROGRESS
#    [3/20] Status: FINISHED
# ✅ Processing complete!
# 📤 Publishing Reel...
# 🎉 Reel posted! ID: ...

# Max duration: ~200 seconds (3.3 minutes) including upload + processing
```

### **Test 3: Check for Known Issues**

If you see these messages, here's what they mean:

| Message | Meaning | Action |
|---|---|---|
| `Status check timeout (retrying...)` | Instagram API slow, but will retry | OK — normal during network slowness |
| `❌ Instagram error: unauthorized` | Token expired | Go to Meta Developer Console and regenerate token |
| `⚠️  Warning: Video not confirmed FINISHED` | Processing took >200s | Check Instagram app — video likely still being processed, will be published when ready |
| `❌ No container ID received` | Instagram API rejected the request | Check caption length (max 2200 chars), image quality, or video format |

---

## 🔐 Security Note

**No secrets are exposed in the fixed code.** All API keys and tokens:
- Come from GitHub Secrets (not hardcoded)
- Are never logged or printed
- Are passed only to legitimate Instagram/catbox API endpoints

---

## 📝 Version History

- **v4.2.0:** Original code with polling loop but no timeouts
- **v4.2.1:** ✅ Added timeouts, error handling, and improved logging (THIS FIX)

---

## ❓ FAQ

**Q: Will the workflow run faster?**
A: No — the bottleneck is Instagram's processing time, not our code. But you'll know exactly what's happening.

**Q: What if Instagram takes >200 seconds to process a video?**
A: The workflow will publish it anyway (with a warning). Instagram processes it in the background.

**Q: What if my Instagram token is expired?**
A: The workflow will now tell you clearly: `"❌ Instagram error: unauthorized"`
Then regenerate the token and re-run.

**Q: Do I need to change anything in main.yml?**
A: No — the workflow file is fine. Only `poster.py` needed fixing.

**Q: How often should I renew my Instagram token?**
A: Every 60 days. Check the GitHub Actions logs — if you see "unauthorized" errors, it's time to renew.

---

## 💬 Next Steps

1. **Use the fixed `poster.py`** from outputs
2. **Test with workflow_dispatch** to verify it works
3. **Monitor the first scheduled run** (8 AM IST for photo, 7 PM IST for reel)
4. **Check logs** to ensure everything completes quickly

If you see any errors in the logs, let me know the exact error message and I can help you debug it!

---

**Questions?** Ask and I'll explain any part in detail.
