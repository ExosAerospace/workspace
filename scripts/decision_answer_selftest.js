#!/usr/bin/env node
// exo3 r2 eval for the R-017 human-confirm gate (mission-control/lib/decision-answer.js).
// Replays the exact R-017 STEP 4 POST body and proves:
//   1. a token "Auto-closed: underlying item resolved" leaves the card OPEN with a proposal,
//   2. a token "Closed (already done): …" does the same,
//   3. a token approve ("Yes") is still rejected,
//   4. a token close on an already-answered card is a no-op,
//   5. a human session answer (the ✓ Confirm click) still closes the card,
//   6. a session user who is not assignee/approver is still rejected,
//   7. server.js actually routes /api/decisions/answer through applyAnswer (wiring check).
// Usage: node scripts/decision_answer_selftest.js   (exit 0 = all pass)
'use strict';
const path = require('path');
const fs = require('fs');
const assert = require('assert');
const { applyAnswer } = require(path.join(__dirname, '..', 'mission-control', 'lib', 'decision-answer.js'));

const now = '2026-09-29T12:00:00.000Z';
const card = () => ({ id: 'D-TEST', status: 'open', assignedTo: 'jquinn@exosaero.com', question: 'q' });
const tokenCtx = { viaToken: true, who: 'Decisions Daily Update (token)', sessionEmail: '', now, mayAnswer: () => false };
const jonCtx = { viaToken: false, who: 'John Quinn', sessionEmail: 'jquinn@exosaero.com', now, mayAnswer: () => true };
let n = 0; const t = (name, fn) => { fn(); n++; console.log('  ok ' + name); };

t('R-017 Auto-closed POST -> card stays open with proposal', () => {
  const d = card();
  const r = applyAnswer(d, JSON.parse('{"id":"D-TEST","answer":"Auto-closed: underlying item resolved"}'), tokenCtx);
  assert.strictEqual(r.result, 'proposed');
  assert.strictEqual(d.status, 'open');
  assert.strictEqual(d.answer, undefined);
  assert.strictEqual(d.answeredAt, undefined);
  assert.strictEqual(d.proposedAnswer, 'Auto-closed: underlying item resolved');
  assert.strictEqual(d.auto_proposed.by, 'Decisions Daily Update');
  assert.strictEqual(d.auto_proposed.at, now);
});
t('R-017 Closed (already done) POST -> proposal only', () => {
  const d = card();
  assert.strictEqual(applyAnswer(d, { id: 'D-TEST', answer: 'Closed (already done): sent to X 9/20', note: 'mail_search hit' }, tokenCtx).result, 'proposed');
  assert.strictEqual(d.status, 'open');
  assert.strictEqual(d.auto_proposed.basis, 'mail_search hit');
});
t('token approve is rejected, card untouched', () => {
  const d = card();
  assert.strictEqual(applyAnswer(d, { id: 'D-TEST', answer: 'Yes' }, tokenCtx).result, 'rejected');
  assert.deepStrictEqual(d, card());
});
t('token close on an answered card is a no-op', () => {
  const d = Object.assign(card(), { status: 'answered', answer: 'No' });
  assert.strictEqual(applyAnswer(d, { id: 'D-TEST', answer: 'Auto-closed: x' }, tokenCtx).result, 'skipped');
  assert.strictEqual(d.answer, 'No'); assert.strictEqual(d.proposedAnswer, undefined);
});
t('human Confirm (session answer) closes the card and records confirmation', () => {
  const d = card();
  applyAnswer(d, { id: 'D-TEST', answer: 'Auto-closed: underlying item resolved' }, tokenCtx);
  assert.strictEqual(applyAnswer(d, { id: 'D-TEST', answer: 'Auto-closed: underlying item resolved' }, jonCtx).result, 'answered');
  assert.strictEqual(d.status, 'answered');
  assert.strictEqual(d.answeredByEmail, 'jquinn@exosaero.com');
  assert.strictEqual(d.proposal_resolution.confirmed, true);
});
t('non-assignee session answer is rejected', () => {
  const d = card();
  assert.strictEqual(applyAnswer(d, { id: 'D-TEST', answer: 'Yes' }, Object.assign({}, jonCtx, { mayAnswer: () => false })).result, 'rejected');
  assert.strictEqual(d.status, 'open');
});
t('server.js routes /api/decisions/answer through applyAnswer (no direct status write for token)', () => {
  const src = fs.readFileSync(path.join(__dirname, '..', 'mission-control', 'server.js'), 'utf8');
  const i = src.indexOf("req.url === '/api/decisions/answer'");
  assert(i > 0, 'answer route not found');
  const block = src.slice(i, i + 6000);
  assert(/require\('\.\/lib\/decision-answer'\)|decisionAnswer\.applyAnswer|applyAnswer\(/.test(block), 'route does not call applyAnswer');
  assert(!/d\.status\s*=\s*'answered'/.test(block), 'route still sets status answered directly');
  assert(/proposed:\s*true/.test(block) || /proposed:\s*proposedIds\.length/.test(block), 'route does not return proposed flag');
});
console.log(`decision_answer selftest: ${n}/7 pass`);
