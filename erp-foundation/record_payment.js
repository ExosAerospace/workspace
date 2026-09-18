'use strict';
/**
 * record_payment.js — THE COMMISSION TRIGGER (manual "mark paid" entry point).
 *
 * When Exos is paid by a customer on a contract, run this. It accrues a commission
 * (status 'due', due 30 days out per the agreement) for every agent attributed to the
 * contract, then files a Mission Control payout task for finance/Jon to approve+pay.
 * NOTHING moves money autonomously — it queues a payable.
 *
 *   node record_payment.js --contract ctr-xyz --amount 750000 --date 2026-08-15 \
 *        [--payload-pct 0.80] [--customer "BioServe"] [--dry]
 */
const path = require('path'), fs = require('fs');
const { openErp } = require('./dal');
const args = Object.fromEntries(process.argv.slice(2).reduce((a,x,i,arr)=>{
  if (x.startsWith('--')) a.push([x.slice(2), (arr[i+1] && !arr[i+1].startsWith('--')) ? arr[i+1] : true]); return a;
},[]));
const DRY = !!args.dry;
const contract = args.contract, amount = Number(args.amount), date = args.date;
if (!contract || !amount || !date) { console.error('need --contract --amount --date'); process.exit(2); }
const bookedKg = args["booked-kg"] ? Number(args["booked-kg"]) : 0;
const capacityKg = args.capacity ? Number(args.capacity) : 135;

const erp = openErp(path.join(__dirname, 'mc.db'), { actor: 'jquinn@exosaero.com', agent: 'commission-trigger' });
const attrs = erp.listAttributions(contract);
if (!attrs.length) { console.error(`No sales-agent attribution on contract ${contract} — nothing to pay. Add one with upsertAttribution first.`); erp.close(); process.exit(1); }

if (DRY) {
  console.log(`DRY RUN — payment $${amount} on ${contract} (${date}), booked ${bookedKg||'?'}kg / cap ${capacityKg}kg:`);
  for (const a of attrs) {
    const ag = erp.listCommissions; // noop ref
  }
}
const rows = erp.recordContractPayment(contract, { amount, date, booked_kg: bookedKg, capacity_kg: capacityKg, customer: args.customer || null });
const due = rows[0] && rows[0].due_date;
for (const r of rows) {
  const bonus = r.bonus_applies ? ` (base ${r.rate*100}% on all + ${r.bonus_rate*100}% on top-25% slice $${r.bonus_base_amount})` : '';
  console.log(`  ${r.agent_name}: $${r.commission_amount} commission${bonus} — status ${r.status}, due ${r.due_date}`);
}
erp.close();

if (DRY) { console.log('(dry: commission rows written to ledger but NO MC task filed)'); process.exit(0); }

// File an MC payout task per commission (Supabase tasks) — the approval/payment queue.
const SB = 'https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1';
const KEY = JSON.parse(fs.readFileSync(require('os').homedir()+'/.openclaw/secrets.json')).supabase_service_role_key;
(async () => {
  for (const r of rows) {
    const task = {
      title: `Pay ${r.agent_name} $${r.commission_amount} sales commission — contract ${r.contract_id}`,
      description: `Commission trigger: Exos received $${r.payment_amount} from ${r.customer||'customer'} on ${r.payment_date} `+
        `(contract ${r.contract_id}). Per agreement: ${r.rate*100}% base${r.bonus_applies?` + ${r.bonus_rate*100}% payload bonus`:''} `+
        `= $${r.commission_amount}. DUE ${r.due_date} (payment + 30 days). Ledger id ${r.id}. Approve + pay via QuickBooks, then mark paid.`,
      category: 'EXOS ADMIN', priority: 85, due_date: r.due_date + 'T23:59:59Z',
      owner: 'Jon', assigned_to: 'Jon', assigned_email: 'jquinn@exosaero.com',
      source: `commission-trigger ${r.id}`, state: 'To Do',
    };
    const resp = await fetch(SB+'/tasks', { method:'POST', headers:{ apikey:KEY, Authorization:'Bearer '+KEY, 'Content-Type':'application/json', Prefer:'return=representation' }, body: JSON.stringify(task) });
    const j = await resp.json();
    console.log(`  filed MC payout task #${Array.isArray(j)&&j[0]?j[0].id:'?'} (due ${r.due_date})`);
  }
})();
