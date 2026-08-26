# Permanent Fix — Kill the winmail.dat / TNEF Problem

**Context:** John Vinson (and almost certainly every other non-Outlook recipient on the LVRS
Charter Working Group) received the Charter and Round-1 Survey as an unreadable
`winmail.dat` blob. Root cause: Outlook composed the message in **Rich Text (RTF)**, which
bundles attachments into a single TNEF (`winmail.dat`) container that non-Outlook mail
clients (Gmail, Apple Mail, Verizon/Yahoo, etc.) cannot unpack.

There are two ways to fix this permanently. Do **both** if you can — #1 protects everyone
regardless of device; #2 protects your own desktop today.

---

## Fix #1 — Org-wide (the real permanent fix) — GATED, awaiting your approval

Disable TNEF at the **Exchange Online / Microsoft 365 tenant** level for the default remote
(Internet) domain. Once done, **no user on any device or client can ever send winmail.dat to
an external recipient again** — it is enforced server-side, so it does not depend on anyone
remembering to change a setting.

Exchange Online PowerShell (run by the tenant admin — Atomus manages the Exos GCC High
tenant):

```powershell
Connect-ExchangeOnline
# Inspect current setting first
Get-RemoteDomain -Identity Default | Format-List Name,DomainName,TNEFEnabled
# Apply the fix: never send TNEF/winmail.dat to Internet recipients
Set-RemoteDomain -Identity Default -TNEFEnabled $false
```

- **Effect:** All outbound mail to external domains is converted to standard MIME. Attachments
  arrive as normal files on every client.
- **Reversible:** `Set-RemoteDomain -Identity Default -TNEFEnabled $null` restores default
  (client-decides) behavior. `$true` would force TNEF (do not use).
- **Blast radius:** Cosmetic only — affects how attachments/rich formatting are encoded on
  outbound Internet mail. No impact on internal mail, no data loss, no downtime.
- **Who runs it:** Atomus (tenant admin) or Exos IT with Exchange admin rights. I cannot run
  this — it requires tenant admin credentials and is an infrastructure change.

## Fix #2 — Per-machine (do this on your desktop Outlook right now, 30 seconds)

Only fixes the machine you set it on, but it protects *you* immediately:

**Outlook (Windows) → File → Options → Mail → "Compose messages in this format" → HTML**
Then, just below: **"When sending messages in Rich Text format to Internet recipients" →
Convert to HTML.**

> Note: this setting lives in **desktop** Outlook. Outlook for iOS / Outlook on the web do
> not produce winmail.dat, so the offending sends came from a desktop Outlook composing in
> Rich Text. If the whole team composes from mixed devices, Fix #1 is the only one that
> guarantees the problem is gone for good.

---

## Recommendation

Approve **Fix #1** (org-wide TNEF disable) — it is the true "do once, never again" fix and it
covers the entire team and every recipient. Apply **Fix #2** on your own desktop today as an
immediate stopgap. The LVRS resend already went out clean (PDF + Word), so this is about
preventing the next occurrence, not the current thread.
