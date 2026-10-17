#!/usr/bin/env python3
"""Generate one Veo image-to-video clip SYNCHRONOUSLY (polls until done).
Usage: EXO_TASK=<n> gen_vid_veo.py <outfile.mp4> <first_frame.jpg> <prompt> [seconds=8] [model=veo-3.1-fast-generate-preview]
Spend-guarded by scripts/google_media_guard.py (google-media-exo3)."""
import base64, json, os, sys, time, urllib.error, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import google_media_guard as guard

KEY = json.load(open('/Users/exomac/.openclaw/secrets.json'))['google_image_api_key']
BASE = "https://generativelanguage.googleapis.com/v1beta"


def call(url, body=None, tries=8):
    for i in range(tries):
        req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None,
                                     headers={"Content-Type": "application/json", "x-goog-api-key": KEY})
        try:
            return json.load(urllib.request.urlopen(req, timeout=120))
        except urllib.error.HTTPError as e:
            msg = e.read()[:500]
            if e.code != 429 or i == tries - 1:
                raise RuntimeError(f"{e.code}: {msg}")
            time.sleep(30 * (i + 1))  # quota / rate limit -> back off


def gen(out, image, prompt, seconds=8, model="veo-3.1-fast-generate-preview"):
    usd = guard.check("video", model, seconds, out)  # needs EXO_TASK; refuses over monthly cap
    img = base64.b64encode(open(image, 'rb').read()).decode()
    op = call(f"{BASE}/models/{model}:predictLongRunning", {
        "instances": [{"prompt": prompt, "image": {"bytesBase64Encoded": img, "mimeType": "image/jpeg"}}],
        "parameters": {"aspectRatio": "16:9", "durationSeconds": int(seconds), "resolution": "1080p",
                       **({"negativePrompt": os.environ["VEO_NEGATIVE"]} if os.environ.get("VEO_NEGATIVE") else {})}})  # NEGATIVE prompt via env
    name = op["name"]
    for _ in range(90):
        time.sleep(10)
        op = call(f"{BASE}/{name}")
        if op.get("done"):
            break
    if "error" in op or not op.get("done"):
        guard.charge("video", model, usd, seconds, out, ok=False)
        print(json.dumps(op)[:1500]); return False
    guard.charge("video", model, usd, seconds, out)
    resp = op["response"].get("generateVideoResponse", op["response"])
    uri = resp["generatedSamples"][0]["video"]["uri"]
    req = urllib.request.Request(uri, headers={"x-goog-api-key": KEY})
    open(out, 'wb').write(urllib.request.urlopen(req, timeout=300).read())
    print("OK", out); return True


if __name__ == "__main__":
    a = sys.argv
    sys.exit(0 if gen(a[1], a[2], a[3], *(a[4:6])) else 1)
