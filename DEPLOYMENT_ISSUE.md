# DEPLOYMENT NOTES - 23 Feb 2026

## Issue: Vercel not updating with STOCK Cava

**Problem:** 
- Local version shows "STOCK Cava" correctly ✅
- Vercel deployment shows old "Cava" only ❌
- Cache issue confirmed

**Solution applied:**

1. **Updated Service Worker cache name:**
   - Old: `cm-v3-stock-cava`
   - New: `stock-cava-2026-02-23-final`

2. **Added build identifier in HTML:**
   - Comment: `<!-- Build: 2026-02-23-STOCK-CAVA -->`

3. **Changed project name in vercel.json:**
   - Old: `cava-metropolis`
   - New: `stock-cava`

4. **No-cache headers already set for:**
   - `/index.html`
   - `/sw.js`
   - `/(.*)`

## Manual Redeploy Instructions:

If automatic deployment still shows old version:

### In Vercel Dashboard:

1. Go to your project
2. Click **"Deployments"** tab
3. Find the LATEST deployment (should be timestamped just now)
4. Click the **3 dots (⋮)** menu
5. Select **"Redeploy"**
6. **UNCHECK** "Use existing Build Cache"
7. Click **"Redeploy"**

This forces a complete rebuild ignoring all caches.

## Verification:

After deployment is "Ready":

1. Open in **Incognito mode**
2. Hard refresh: `Cmd + Shift + R`
3. Check DevTools > Application > Service Workers
   - Should show: `stock-cava-2026-02-23-final`
4. Look for header comment in HTML source:
   - Should contain: `<!-- Build: 2026-02-23-STOCK-CAVA -->`

## Expected Result:

```
    STOCK Cava
   METROPOLIS
```

Where "STOCK" is in Montserrat ExtraBold and "Cava" in Playfair Display Italic.
