// exo3 r2 (R-017 human-confirm gap, 2026-09-29): how one answer is applied to one decision card.
//
// AI proposes, a human confirms. A token-authenticated caller (the "Decisions Matrix Daily Update"
// cron R-017, no login session) can NEVER change a card's status. Its "Closed …"/"Auto-closed …"
// answers become a PROPOSAL on the still-open card (proposedAnswer + auto_proposed), the same shape
// the send-watcher / email-tracker use (commit a98e06d). decisions.html renders it as
// "🤖 Exo proposes … ✓ Confirm", and the Confirm click is a normal session answer that closes it.
//
// Pure function: no I/O, so scripts/decision_answer_selftest.js can replay R-017 against it.
'use strict';

const isClose = a => /^(auto-)?closed\b/i.test(String(a || '').trim());

// it: {id, answer, note}; ctx: {viaToken, who, sessionEmail, now, mayAnswer(d)->bool}
// Returns {result: 'answered'|'proposed'|'rejected'|'skipped'}; mutates d on answered/proposed.
function applyAnswer(d, it, ctx) {
  if (!d) return { result: 'skipped' };
  if (it.answer === undefined && !it.note) return { result: 'skipped' };
  if (ctx.viaToken) {
    if (!isClose(it.answer)) return { result: 'rejected' };
    const st = String(d.status || 'open').toLowerCase();
    if (st !== 'open' && st !== 'pending') return { result: 'skipped' }; // never touch a human-answered card
    d.proposedAnswer = String(it.answer);
    d.auto_proposed = { by: 'Decisions Daily Update', at: ctx.now, basis: String(it.note || it.answer || '') };
    d.updated = ctx.now;
    // status, answer, answeredAt, answeredBy are deliberately NOT touched.
    return { result: 'proposed' };
  }
  if (!ctx.mayAnswer(d)) return { result: 'rejected' };
  d.answer = it.answer ?? d.answer; d.note = it.note || ''; d.status = 'answered';
  d.answeredAt = ctx.now; d.answeredBy = ctx.who; d.updated = ctx.now;
  if (ctx.sessionEmail) d.answeredByEmail = ctx.sessionEmail;
  if (d.proposedAnswer !== undefined || d.auto_proposed) {
    d.proposal_resolution = { confirmed: String(d.answer) === String(d.proposedAnswer || ''), by: ctx.who, at: ctx.now };
  }
  return { result: 'answered' };
}

module.exports = { applyAnswer, isClose };
