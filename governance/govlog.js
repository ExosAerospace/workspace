'use strict';
/**
 * govlog.js -- Searchable-Logs-with-Correlation-IDs pillar (Node / ERP side).
 *
 * Mirror of governance/govlog.py for the Node ERP DAL and any JS worker.
 * Appends correlated events to the same substrate: governance/events.jsonl.
 *
 *   const { newRun, event } = require('../governance/govlog');
 *   const run = newRun('erp-dal');
 *   event(run, 'upsertDeal', 'ok', '', { entity: 'deal', id: 'EXOS-0001' });
 *
 * The run_id is the correlation id that also lands in audit_log.correlation_id,
 * so an ERP mutation joins the same trace as the agent run that caused it.
 */
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const LOG = path.join(__dirname, 'events.jsonl');

function newRun(agent) {
  return { agent, run_id: crypto.randomBytes(8).toString('hex') };
}

function event(run, evt, status = 'info', detail = '', fields = {}) {
  const rid = run && run.run_id ? run.run_id : String(run);
  const agent = run && run.agent ? run.agent : 'unknown';
  const row = Object.assign(
    { ts: new Date().toISOString(), correlation_id: rid, agent, event: evt, status },
    detail ? { detail } : {},
    fields
  );
  fs.appendFileSync(LOG, JSON.stringify(row) + '\n');
  return rid;
}

module.exports = { newRun, event };

if (require.main === module) {
  const r = newRun(process.argv[2] || 'govlog-selftest');
  event(r, process.argv[3] || 'selftest', 'ok', process.argv[4] || 'ok');
  console.log(`wrote event run_id=${r.run_id} -> ${LOG}`);
}
