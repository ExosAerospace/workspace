# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

## Email — ProtonMail Bridge

Jon's email is **jquinnexo@pm.me** (ProtonMail).

**ProtonMail Bridge** is installed and running on ExoMac. It exposes local SMTP and IMAP:

- **Outbound (SMTP):** `msmtp` configured for jquinnexo@pm.me via Bridge on port 1025
  - Bridge cert: `~/.protonmail-bridge.crt`
  - Bridge must be running for outbound to work
- **Inbound (IMAP):** Available via Bridge on localhost (port 1143 typically)
  - Script: `scripts/mission-control-imap.py` reads inbox
- **Use cases:** Sending emails (drafts, outreach, follow-ups), scanning inbox for opportunities, daily briefings

**Remember:** You CAN send and read email. Don't say you can't. ProtonMail Bridge makes this possible locally — no external API needed.

---

## QuickBooks

Jon has provided QuickBooks access. Available for financial queries, invoicing, expense tracking, and reporting as needed.

---

Add whatever helps you do your job. This is your cheat sheet.
