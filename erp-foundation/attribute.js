'use strict';
/**
 * attribute.js — Sales-process step: tag WHO initiated a contract, so commissions route to them.
 * Part of the ExO 3.0 sales automation: deal won → contract → ATTRIBUTE (here) → payment → payout.
 *
 *   node attribute.js --contract ctr-xyz --agent-email lquinn@exosaero.com [--role initiated] [--rate 0.05]
 *   node attribute.js --contract ctr-xyz --agent agent-lquinn
 */
const path = require('path');
const { openErp } = require('./dal');
const a = Object.fromEntries(process.argv.slice(2).reduce((acc,x,i,arr)=>{ if(x.startsWith('--')) acc.push([x.slice(2), (arr[i+1]&&!arr[i+1].startsWith('--'))?arr[i+1]:true]); return acc; },[]));
if(!a.contract || (!a.agent && !a['agent-email'])){ console.error('need --contract and (--agent or --agent-email)'); process.exit(2); }
const erp = openErp(path.join(__dirname,'mc.db'), { actor:'jquinn@exosaero.com', agent:'sales-attribution' });
let agentId = a.agent;
if(!agentId){ const ag = erp.getAgentByEmail(a['agent-email']); if(!ag){ console.error('no sales agent for '+a['agent-email']); process.exit(1);} agentId = ag.id; }
const id = `attr-${a.contract}-${agentId}`;
const row = erp.upsertAttribution({ id, contract_id:a.contract, agent_id:agentId, role:a.role||'initiated',
  rate: a.rate!=null && a.rate!==true ? Number(a.rate) : null, effective_date:new Date().toISOString().slice(0,10) });
console.log('attributed contract', a.contract, '->', agentId, '('+row.role+(row.rate!=null?`, rate ${row.rate}`:', agent default rate')+')');
erp.close();
