// Selftest for mission-control/lib/inventory-photos.js — runs against a throwaway copy of lib/ in a temp dir.
// node scripts/inventory_photos_selftest.js   → exit 0 on pass
const fs = require('fs'), os = require('os'), path = require('path'), assert = require('assert');
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'invph-'));
fs.mkdirSync(path.join(tmp, 'lib')); fs.mkdirSync(path.join(tmp, 'data')); fs.mkdirSync(path.join(tmp, 'uploads'));
for (const f of ['inventory-photos.js', 'recycle.js']) fs.copyFileSync(path.join(__dirname, '..', 'mission-control', 'lib', f), path.join(tmp, 'lib', f));
const P = require(path.join(tmp, 'lib', 'inventory-photos.js'));
let n = 0; const ok = (c, m) => { assert.ok(c, m); n++; };
const key = 'Computer#10';
const ledger = [{ task: '3024', upload: 'abc', file: 'x.png', by: 'Steve', at: '2026-09-22T00:00:00Z' }];
ok(P.photosFor(key, ledger).length === 1, 'ledger photo shows');
const a = P.add(key, [{ filename: 'a.jpg', data: Buffer.from('1') }, { filename: 'b.png', data: Buffer.from('2') }], 'Jon');
ok(a.length === 2 && P.photosFor(key, ledger).length === 3, 'multiple photos on one part');
let threw = false; try { P.add(key, [{ filename: 'evil.pdf', data: Buffer.from('x') }], 'Jon'); } catch { threw = true; }
ok(threw, 'non-image rejected');
const f0 = path.join(P.PHOTO_DIR, a[0].file); ok(fs.existsSync(f0), 'file stored');
const r = P.remove(key, a[0].id, ledger, 'jon@x', '/t');
ok(r.recycle_id && !fs.existsSync(f0), 'page photo moved out on delete');
ok(fs.readdirSync(path.join(tmp, 'data', 'recycle-bin', 'files')).length === 1, 'file parked in recycle bin');
ok(P.photosFor(key, ledger).length === 2, 'deleted photo hidden');
P.remove(key, 'led_abc', ledger, 'jon@x', '/t');
ok(P.photosFor(key, ledger).every(p => p.source === 'page'), 'ledger photo hidden, ledger untouched');
ok(ledger.length === 1, 'ledger array not mutated');
ok(P.remove(key, 'led_abc', ledger, 'jon@x', '/t').already, 'double delete is a no-op');
threw = false; try { P.remove(key, 'nope', ledger, 'j', '/t'); } catch { threw = true; }
ok(threw, 'unknown photo refused');
const bin = fs.readdirSync(path.join(tmp, 'data', 'recycle-bin')).filter(f => f.endsWith('.jsonl'));
const entries = bin.flatMap(f => fs.readFileSync(path.join(tmp, 'data', 'recycle-bin', f), 'utf8').trim().split('\n').map(JSON.parse));
ok(entries.length === 2 && entries.every(e => e.type === 'inventory-photo' && e.extra.key === key), 'recycle entries recorded');
// Full Shop Inventory lines: key "shop#SHOP-xxxxx" (permanent ids), validated against shop-inventory.json.
const shopInv = path.join(tmp, 'data', 'shop-inventory.json');
fs.writeFileSync(shopInv, JSON.stringify({ items: [{ id: 'SHOP-00007' }, { id: 'SHOP-01685' }] }));
ok(P.isShopKey('shop#SHOP-00007') && !P.isShopKey('Computer#10') && !P.isShopKey('shop#SHOP-7'), 'shop key recognised');
ok(P.shopKeyValid('shop#SHOP-00007', shopInv) && !P.shopKeyValid('shop#SHOP-99999', shopInv), 'shop key must be a current line');
const sk = 'shop#SHOP-00007';
const s1 = P.add(sk, [{ filename: 'c.jpg', data: Buffer.from('3') }, { filename: 'd.heic', data: Buffer.from('4') }], 'Steve Norsworthy');
ok(s1.length === 2 && P.photosFor(sk, []).length === 2, 'several photos on a shop line');
ok(P.photosFor('shop#SHOP-01685', []).length === 0 && P.photosFor(key, ledger).length === 1, 'shop photos isolated per id and from BOM keys');
const rs = P.remove(sk, s1[0].id, [], 'steve@x', '/t');
ok(rs.recycle_id && P.photosFor(sk, []).length === 1 && fs.readdirSync(path.join(tmp, 'data', 'recycle-bin', 'files')).length === 2, 'shop photo delete -> recycle bin');
fs.rmSync(tmp, { recursive: true, force: true });
console.log(`inventory-photos selftest: ${n}/${n} passed`);
