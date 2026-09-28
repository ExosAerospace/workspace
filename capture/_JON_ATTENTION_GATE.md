# JON-ATTENTION GATE — every capture agent, every run (Jon, 2026-09-28)

Before you put ANY item in front of Jon ("needs your attention", "unread", "decision needed",
"send X"), it must pass all four checks. If it fails any one, drop it from the Jon list.

1. **Already sent?** Check `logs/outreach-sent-registry.json` and this tracker's
   "AUTO SENT-CONFIRMATIONS" block (look for the address AND any co-recipient). If it was sent,
   this is reply-watch only. Never ask Jon to send it again.
2. **Is it a real ask?** For "X replied / reply unread" items, read the ACTUAL message with
   `python3 scripts/mail_search.py --since <date> <sender>`. Don't rely on your tracker notes.
   A short acknowledgement ("Agreed, thanks", "Got it", "Noted") with no question or request
   is CLOSED. Jon's Proton inbox (jquinnexo@pm.me) is not his Outlook, so say where the email is.
3. **Closed stays closed.** Never re-raise an item this tracker marks ✅ CLOSED / SENT / RESOLVED
   unless a NEW inbound email or event changes it. If that happens, cite the new email.
4. **No carry-forward.** If you flagged an item last run and there are no new facts, re-verify it
   at the source (checks 1–2) before flagging again. If you can't show new evidence, drop it.
   Repeating "still unread, now N days" from your own notes is not evidence.

Why: on 9/28, two "need your direct attention" items were both false. The Concho letter had
already been sent on 9/26. Edgar's "unread" 9/21 reply said only "Agreed and Thanks for the
update." One had been re-flagged daily for 7 days from agent notes alone.
