#!/usr/bin/env python3
"""
MEETING TRANSCRIBE — capture a live meeting's audio on ExoMac and transcribe it locally.

Records from a CoreAudio input (default: the BlackHole 2ch loopback that carries system
output — i.e. everyone else on the call) in short chunks, runs each chunk through whisper.cpp,
and appends the text to a transcript in transcripts/inbox/ so ingest-transcripts.py extracts
contacts + action items automatically. Chunked so a long meeting streams to disk and nothing
is lost if it's interrupted. 100% local — no audio leaves the machine.

Setup (one time): install BlackHole, then route the meeting's OUTPUT to a Multi-Output Device
that includes BlackHole so you still hear it while we capture it. See meeting-capture-SETUP.md.

Run:  python3 scripts/meeting-transcribe.py                 # capture until Ctrl-C (or stop file)
      python3 scripts/meeting-transcribe.py --minutes 60    # hard stop after 60 min
      python3 scripts/meeting-transcribe.py --device "Aggregate Device" --label "NGC sync"
      touch transcripts/.stop-capture                        # graceful stop from anywhere
"""
import os, sys, re, subprocess, argparse, datetime, signal

WS = os.path.expanduser("~/.openclaw/workspace")
MODEL = os.path.join(WS, "models", "whisper", "ggml-small.en.bin")
INBOX = os.path.join(WS, "transcripts", "inbox")
TMP = os.path.join(WS, "transcripts", ".chunks")
STOPFILE = os.path.join(WS, "transcripts", ".stop-capture")
WHISPER = "/opt/homebrew/bin/whisper-cli"
FFMPEG = "/opt/homebrew/bin/ffmpeg"
CHUNK_SEC = 60
_stop = {"v": False}


def avfoundation_index(name):
    """Resolve the avfoundation audio-input index for a device by (case-insensitive) name."""
    p = subprocess.run([FFMPEG, "-f", "avfoundation", "-list_devices", "true", "-i", ""],
                       capture_output=True, text=True)
    txt = p.stderr
    audio = txt.split("AVFoundation audio devices:")[-1] if "audio devices:" in txt else txt
    for line in audio.splitlines():
        m = re.search(r"\[(\d+)\]\s+(.*)", line)
        if m and name.lower() in m.group(2).strip().lower():
            return m.group(1), m.group(2).strip()
    return None, None


def record_chunk(idx, wav, seconds):
    subprocess.run([FFMPEG, "-y", "-f", "avfoundation", "-i", f":{idx}",
                    "-t", str(seconds), "-ar", "16000", "-ac", "1", wav],
                   capture_output=True)
    return os.path.exists(wav) and os.path.getsize(wav) > 1000


def transcribe(wav, base):
    subprocess.run([WHISPER, "-m", MODEL, "-f", wav, "-otxt", "-of", base, "-nt"],
                   capture_output=True)
    txt = base + ".txt"
    return open(txt).read().strip() if os.path.exists(txt) else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--device", default="BlackHole", help="input device name substring")
    ap.add_argument("--minutes", type=float, default=0, help="hard stop after N minutes (0=until stopped)")
    ap.add_argument("--label", default="", help="short meeting label for the filename/header")
    a = ap.parse_args()

    if not os.path.exists(MODEL):
        print(f"ERROR: whisper model missing at {MODEL} (still downloading?)"); sys.exit(1)
    idx, dev = avfoundation_index(a.device)
    if idx is None:
        print(f"ERROR: no audio input matching '{a.device}'. Install BlackHole and route the "
              f"meeting output through it (see transcripts/meeting-capture-SETUP.md).")
        print("Available inputs:")
        subprocess.run([FFMPEG, "-f", "avfoundation", "-list_devices", "true", "-i", ""])
        sys.exit(1)

    os.makedirs(INBOX, exist_ok=True); os.makedirs(TMP, exist_ok=True)
    if os.path.exists(STOPFILE): os.remove(STOPFILE)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M")
    slug = re.sub(r"[^a-z0-9]+", "-", (a.label or "webex-meeting").lower()).strip("-")
    out = os.path.join(INBOX, f"{slug}-{stamp}.txt")
    header = (f"# Meeting transcript{' — ' + a.label if a.label else ''}\n"
              f"Captured {datetime.datetime.now():%Y-%m-%d %H:%M} · device: {dev} · local whisper.cpp\n\n")
    open(out, "w").write(header)
    print(f"▶ capturing from '{dev}' → {out}\n  Stop: Ctrl-C or `touch {STOPFILE}`")

    signal.signal(signal.SIGINT, lambda *_: _stop.__setitem__("v", True))
    start = datetime.datetime.now(); n = 0
    while not _stop["v"]:
        if os.path.exists(STOPFILE): print("\n■ stop file seen"); break
        if a.minutes and (datetime.datetime.now() - start).total_seconds() >= a.minutes * 60:
            print("\n■ time limit reached"); break
        n += 1
        wav = os.path.join(TMP, f"chunk-{stamp}-{n:04d}.wav")
        base = os.path.join(TMP, f"chunk-{stamp}-{n:04d}")
        if not record_chunk(idx, wav, CHUNK_SEC):
            print("  (no audio this chunk — is the meeting routed through the device?)")
            continue
        text = transcribe(wav, base)
        if text:
            ts = datetime.datetime.now().strftime("%H:%M")
            with open(out, "a") as f:
                f.write(f"[{ts}] {text}\n")
            print(f"  [{ts}] +{len(text.split())} words")
        for f in (wav, base + ".txt"):
            try: os.remove(f)
            except OSError: pass

    if os.path.exists(STOPFILE): os.remove(STOPFILE)
    print(f"\n✔ transcript saved: {out}\n  ingest-transcripts.py will extract contacts + action items on its next run.")


if __name__ == "__main__":
    main()
