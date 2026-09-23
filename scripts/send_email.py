#!/usr/bin/env python3
"""send_email.py — the CANONICAL way for any Exo path to email a document WITH attachments.

deliver.py is text-only (it calls `message send -m <text>` and cannot attach files) — using it to
"send a document" silently drops the attachment. Use THIS for anything with a file.

  python3 scripts/send_email.py --to a@x.com [--cc b@x.com] --subject "..." --body "..." \
      --attach drafts/File1.pdf --attach drafts/File2.docx

Sends via ProtonMail Bridge (msmtp -a protonmail). Exits non-zero (loud) if an attachment is missing
or the send fails — never a silent drop.
"""
import argparse, email.message, mimetypes, os, subprocess, sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--to", required=True, help="comma-separated recipients")
    ap.add_argument("--cc", default="")
    ap.add_argument("--subject", required=True)
    ap.add_argument("--body", default="")
    ap.add_argument("--from-addr", default="jquinnexo@pm.me")
    ap.add_argument("--attach", action="append", default=[], help="file path (repeatable)")
    a = ap.parse_args()

    missing = [f for f in a.attach if not os.path.exists(f)]
    if missing:
        print("ERROR: attachment(s) not found: " + ", ".join(missing), file=sys.stderr)
        sys.exit(2)

    m = email.message.EmailMessage()
    m["From"] = a.from_addr
    m["To"] = a.to
    if a.cc:
        m["Cc"] = a.cc
    m["Subject"] = a.subject
    m.set_content(a.body or "")
    for f in a.attach:
        ctype, _ = mimetypes.guess_type(f)
        maintype, subtype = (ctype or "application/octet-stream").split("/", 1)
        with open(f, "rb") as fh:
            m.add_attachment(fh.read(), maintype=maintype, subtype=subtype, filename=os.path.basename(f))

    rcpts = [x.strip() for x in (a.to.split(",") + a.cc.split(",")) if x.strip()]
    r = subprocess.run(["msmtp", "-a", "protonmail", *rcpts], input=bytes(m), capture_output=True)
    if r.returncode != 0:
        print("ERROR: msmtp send failed: " + r.stderr.decode("utf-8", "ignore"), file=sys.stderr)
        sys.exit(1)
    print(f"OK: emailed {a.to}" + (f" (cc {a.cc})" if a.cc else "") +
          f" with {len(a.attach)} attachment(s): {[os.path.basename(f) for f in a.attach]}")


if __name__ == "__main__":
    main()
