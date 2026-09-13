#!/usr/bin/env python3
"""
secrets_transfer.py — securely move the credential set from the mini to the Studio.

Packages the sensitive bits into ONE AES-256 encrypted archive (openssl, PBKDF2) so they
can travel over a local high-speed cable/drive during setup — NEVER Discord/email/plaintext.
Decrypt on the Studio with the same passphrase.

Included:
  - ~/.openclaw/secrets.json            (37 keys)
  - ~/.protonmail-bridge.crt            (Bridge cert)
  - ~/.msmtprc                          (outbound email config, if present)
  - ~/.openclaw/state/                  (small runtime state; optional)

NOT included (re-auth on the Studio instead — device-bound):
  - ProtonMail Bridge login/2FA (reinstall + sign in)
  - QuickBooks OAuth (re-consent if refresh token doesn't carry)
  - Browser profile / site logins (many sites force re-login on a new device)

Usage:
  ON THE MINI:    python3 scripts/secrets_transfer.py --package   -> writes secrets-bundle.enc
  ON THE STUDIO:  python3 scripts/secrets_transfer.py --unpack secrets-bundle.enc
Passphrase: env SECRETS_XFER_PASS, else prompted. Use a strong one; share it out-of-band.
"""
import os, sys, subprocess, tarfile, tempfile, getpass, glob

HOME = os.path.expanduser("~")
OUT = os.path.join(HOME, "secrets-bundle.enc")

INCLUDE = [
    os.path.join(HOME, ".openclaw", "secrets.json"),
    os.path.join(HOME, ".protonmail-bridge.crt"),
    os.path.join(HOME, ".msmtprc"),
    os.path.join(HOME, ".openclaw", "state"),
]

def _pass(confirm=False):
    p = os.environ.get("SECRETS_XFER_PASS")
    if p:
        return p
    p = getpass.getpass("Passphrase: ")
    if confirm:
        if p != getpass.getpass("Confirm passphrase: "):
            print("Passphrases do not match."); sys.exit(1)
    if len(p) < 10:
        print("Use a passphrase >= 10 chars."); sys.exit(1)
    return p

def package():
    present = [p for p in INCLUDE if os.path.exists(p)]
    missing = [p for p in INCLUDE if not os.path.exists(p)]
    if missing:
        print("NOTE: not found (skipped):")
        for m in missing: print("   -", m)
    if not present:
        print("Nothing to package."); sys.exit(1)
    print("Packaging:")
    for p in present: print("   +", p)
    pw = _pass(confirm=True)
    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tf:
        tmp = tf.name
    try:
        with tarfile.open(tmp, "w:gz") as tar:
            for p in present:
                tar.add(p, arcname=os.path.relpath(p, HOME))
        rc = subprocess.run(
            ["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-iter", "300000", "-salt",
             "-in", tmp, "-out", OUT, "-pass", f"pass:{pw}"]).returncode
        if rc != 0:
            print("openssl encrypt failed."); sys.exit(1)
    finally:
        os.remove(tmp)
    os.chmod(OUT, 0o600)
    print(f"\nWrote {OUT} (0600). Move it to the Studio over a LOCAL cable/drive, then --unpack.")
    print("Delete the .enc from BOTH machines once verified.")

def unpack(enc):
    if not os.path.exists(enc):
        print(f"Not found: {enc}"); sys.exit(1)
    pw = _pass(confirm=False)
    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tf:
        tmp = tf.name
    try:
        rc = subprocess.run(
            ["openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-iter", "300000",
             "-in", enc, "-out", tmp, "-pass", f"pass:{pw}"]).returncode
        if rc != 0:
            print("Decrypt failed (wrong passphrase?)."); sys.exit(1)
        with tarfile.open(tmp, "r:gz") as tar:
            names = tar.getnames()
            print("Restoring into", HOME, ":")
            for n in names: print("   ->", n)
            tar.extractall(HOME)
        # tighten perms on secrets
        sj = os.path.join(HOME, ".openclaw", "secrets.json")
        if os.path.exists(sj): os.chmod(sj, 0o600)
        print("\nDone. Verify: python3 -c \"import json,os;print(len(json.load(open(os.path.expanduser('~/.openclaw/secrets.json')))),'keys')\"")
        print("Then delete the .enc bundle from both machines.")
    finally:
        os.remove(tmp)

if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "--package":
        package()
    elif a and a[0] == "--unpack" and len(a) > 1:
        unpack(a[1])
    else:
        print(__doc__); sys.exit(2)
