'use strict';
// Seed sales agents from signed agreements. Lizi = first (5% + 5% payload bonus + equity).
const path = require('path');
const { openErp } = require('./dal');
const erp = openErp(path.join(__dirname, 'mc.db'), { actor: 'jquinn@exosaero.com', agent: 'seed-sales-agents' });
const a = erp.upsertSalesAgent({
  id: 'agent-lquinn', name: 'Elizabeth Quinn', email: 'lquinn@exosaero.com',
  base_rate: 0.05, bonus_rate: 0.05,
  bonus_condition: 'Payload sale filling >75% of vehicle payload capacity',
  equity_shares: 20000, equity_vesting: '3-year, 1/3 annual (~6,667/yr)',
  agreement_doc: 'erp-foundation/agent-agreements/Elizabeth_Quinn_Commercialization_Agent_Agreement_2025_r2.docx',
  status: 'Active',
});
console.log('seeded agent:', a.name, '| base', a.base_rate, '| bonus', a.bonus_rate, '| equity', a.equity_shares);
erp.close();
