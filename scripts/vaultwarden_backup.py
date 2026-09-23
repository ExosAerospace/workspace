#!/usr/bin/env python3
"""vaultwarden_backup.py — nightly backup of the self-hosted Vaultwarden data.

Vaultwarden's vaults are zero-knowledge (already encrypted), but the SQLite DB + the server RSA key
+ attachments must be backed up to survive a disk loss. This does a CONSISTENT online sqlite backup
(safe while the server is running) plus the key material and attachments, tars them, and keeps the
last N archives. Point offsite DR (the Mini) at the backup dir to get a second copy.

launchd: com.exos.vaultwarden-backup (daily). Store dir: $VW_BACKUP_DIR or ~/exos-asset-backups/vaultwarden.
"""
import os, sys, shutil, subprocess, tarfile, datetime, glob

DATA = os.environ.get("VW_DATA_DIR", "/Users/exomac/vaultwarden-data")
DEST = os.environ.get("VW_BACKUP_DIR", os.path.expanduser("~/exos-asset-backups/vaultwarden"))
KEEP = int(os.environ.get("VW_BACKUP_KEEP", "14"))
DB = os.path.join(DATA, "db.sqlite3")


def main():
    if not os.path.exists(DB):
        print(f"ERROR: no db at {DB}", file=sys.stderr); sys.exit(1)
    os.makedirs(DEST, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M")
    work = os.path.join(DEST, f".work-{stamp}")
    os.makedirs(work, exist_ok=True)
    try:
        # 1) consistent online SQLite backup (safe while Vaultwarden is running)
        subprocess.run(["/usr/bin/sqlite3", DB, f".backup '{os.path.join(work, 'db.sqlite3')}'"],
                       check=True, timeout=120)
        # 2) key material + config + attachments/sends
        for name in ["rsa_key.pem", "rsa_key.pub.pem", "config.json", ".admin_token"]:
            src = os.path.join(DATA, name)
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(work, name))
        for d in ["attachments", "sends"]:
            src = os.path.join(DATA, d)
            if os.path.isdir(src):
                shutil.copytree(src, os.path.join(work, d))
        # 3) tar.gz
        archive = os.path.join(DEST, f"vaultwarden-{stamp}.tar.gz")
        with tarfile.open(archive, "w:gz") as t:
            t.add(work, arcname=f"vaultwarden-{stamp}")
        os.chmod(archive, 0o600)
        size = os.path.getsize(archive)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    # 4) retention — keep the newest KEEP archives
    archives = sorted(glob.glob(os.path.join(DEST, "vaultwarden-*.tar.gz")))
    for old in archives[:-KEEP]:
        try:
            os.remove(old)
        except Exception:
            pass
    print(f"OK: {archive} ({size // 1024} KB); {min(len(archives), KEEP)} archives retained in {DEST}")


if __name__ == "__main__":
    main()
