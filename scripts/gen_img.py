#!/usr/bin/env python3
"""Generate one photoreal image via Gemini paid tier. Usage: EXO_TASK=<n> gen_img.py <outfile> <prompt> [model]
Spend-guarded by scripts/google_media_guard.py (google-media-exo3)."""
import json, base64, urllib.request, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import google_media_guard as guard

KEY = json.load(open('/Users/exomac/.openclaw/secrets.json'))['google_image_api_key']

def gen(out, prompt, model="gemini-3-pro-image-preview", tries=3):
    usd = guard.check("image", model, out=out)  # needs EXO_TASK; refuses over monthly cap
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={KEY}"
    body = {"contents":[{"parts":[{"text":prompt}]}],
            "generationConfig":{"responseModalities":["IMAGE"]}}
    for t in range(tries):
        try:
            req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                         headers={"Content-Type":"application/json"})
            d = json.load(urllib.request.urlopen(req, timeout=200))
            for c in d.get("candidates",[]):
                for p in c.get("content",{}).get("parts",[]):
                    inl = p.get("inlineData") or p.get("inline_data")
                    if inl and inl.get("data"):
                        open(out,"wb").write(base64.b64decode(inl["data"]))
                        guard.charge("image", model, usd, out=out)
                        print("OK", out, os.path.getsize(out)); return True
            print("NO_IMAGE", json.dumps(d)[:200])
        except urllib.error.HTTPError as e:
            msg = e.read().decode()[:160]
            print("HTTP", e.code, msg)
            if e.code in (429,500,503): time.sleep(6*(t+1)); continue
            return False
        except Exception as e:
            print("ERR", str(e)[:120]); time.sleep(4); continue
    return False

if __name__ == "__main__":
    out, prompt = sys.argv[1], sys.argv[2]
    model = sys.argv[3] if len(sys.argv) > 3 else "gemini-3-pro-image-preview"
    sys.exit(0 if gen(out, prompt, model) else 1)
