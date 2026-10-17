#!/usr/bin/env python3
"""Rugged HMD preview (Jon 2026-10-16: option 3 "more ruggedized, especially buttons").
Renders a populated MC-style dashboard using MC's OWN class names (.card/.stat-card/.task-card/.btn/.btn-primary/
.btn-danger/.filter-btn) styled ONLY by mission-control/theme-hud.css, so the preview is exactly what ships."""
import os, subprocess
from build import TASKS, KPIS, ALERTS, CHROME

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "hud")
CSS = "file:///Users/exomac/.openclaw/workspace/mission-control/theme-hud.css"

base = """*{box-sizing:border-box} body{margin:0;width:1600px;height:1000px;overflow:hidden;color:var(--text)}
header{display:flex;align-items:center;justify-content:space-between;padding:12px 22px}
.brand{font-size:22px;letter-spacing:.28em;color:#e9fbff;text-shadow:0 0 6px rgba(127,233,255,.55)} .brand small{display:block;font-size:11px;color:var(--text2);letter-spacing:.3em}
nav{display:flex;gap:8px} .btn,.filter-btn,button{padding:8px 14px;font-size:13px;cursor:pointer}
.sm{padding:5px 10px;font-size:11px}
.wrap{padding:14px 22px;display:grid;grid-template-columns:2fr 1fr;gap:16px}
.row{grid-column:1/3;display:flex;gap:8px;align-items:center}
.kpis{grid-column:1/3;display:grid;grid-template-columns:repeat(5,1fr);gap:14px} .stat-card{padding:14px 16px}
.kv{font-size:30px;font-weight:700;color:var(--text)} .kl{font-size:11px;letter-spacing:.22em;color:var(--text2);margin-top:3px}
.card{padding:14px 16px} h3{margin:0 0 10px;font-size:13px}
table{width:100%;border-collapse:collapse;font-size:15px} td,th{padding:8px;text-align:left;border-bottom:1px solid} th{font-size:11px}
.sc{font-size:18px;color:var(--accent);width:56px} .dim{color:var(--text2)}
.pill{font-size:11px;letter-spacing:.16em;padding:2px 7px;border:1px solid} .pCRIT{color:var(--red)} .pHIGH{color:var(--yellow)} .pMED{color:var(--text2)}
.task-card{padding:10px 12px;margin-bottom:10px;font-size:14px} .task-card .acts{display:flex;gap:6px;margin-top:8px}
.bank{display:grid;grid-template-columns:repeat(3,1fr);gap:10px} .bank .btn{padding:12px 6px;font-size:13px}
.ticker{position:absolute;bottom:0;left:0;right:0;padding:9px 22px;border-top:3px solid #2b3944;color:var(--yellow);font-size:14px;white-space:nowrap;overflow:hidden;background:linear-gradient(#1a232b,#0b1117)}
"""

def render(css_url, out_base, subtitle):
    rows = "".join(f"<tr><td class=sc>{s}</td><td>{n}</td><td class=dim>{o}</td><td><span class='pill p{p}'>{p}</span></td>"
                   f"<td><button class='btn sm'>Open</button></td></tr>" for s, n, o, p in TASKS)
    kpis = "".join(f"<div class=stat-card><div class=kv>{v}</div><div class=kl>{k}</div></div>" for k, v in KPIS)
    html = f"""<!doctype html><html><head><meta charset=utf-8><link rel=stylesheet href="{css_url}"><style>{base}</style></head><body>
    <header><div class=brand>EXOS MISSION CONTROL<small>{subtitle}</small></div>
    <nav><button class=btn>Sales ▾</button><button class=btn>Relationships ▾</button><button class=btn>Manufacturing ▾</button><button class=btn>Purchasing ▾</button><button class=btn>Business Ops ▾</button><button class='btn btn-primary'>Decisions · 7</button></nav></header>
    <div class=wrap>
    <div class=row><button class='filter-btn active'>✓ All</button><button class=filter-btn>My Tasks</button><button class=filter-btn>Group</button><button class=filter-btn>Exo</button><button class=filter-btn>Overdue</button><button class=filter-btn>★ Mission Score</button>
    <input style="margin-left:auto;width:320px;padding:8px 10px" placeholder="Search tasks…"><select style="padding:8px"><option>All priorities</option></select><button class='btn btn-primary'>+ Add</button></div>
    <div class=kpis>{kpis}</div>
    <div class=card><h3>▸ Priority targets · mission score</h3><table><tr><th>Score</th><th>Task</th><th>Owner</th><th>Pri</th><th></th></tr>{rows}</table></div>
    <div><div class=card><h3>▸ Decisions awaiting CEO</h3>
    <div class=task-card>D-7282118 · EXOS-FIN-004 intl payments<div class=acts><button class='btn btn-primary sm'>Approve</button><button class='btn ghost sm'>Hold</button><button class='btn btn-danger sm'>Reject</button></div></div>
    <div class=task-card>D-7282081 · exo3 code audit remediation<div class=acts><button class='btn btn-primary sm'>Approve</button><button class='btn ghost sm'>Hold</button><button class='btn btn-danger sm'>Reject</button></div></div></div>
    <div class=card style="margin-top:16px"><h3>▸ Control bank</h3><div class=bank>
    <button class='btn btn-primary'>Send it</button><button class=btn>Assign</button><button class=btn>Attach doc</button>
    <button class='btn secondary'>Snooze</button><button class=btn>Refresh</button><button class='btn btn-danger'>Delete</button></div></div></div>
    </div>
    <div class=ticker>⚠ MASTER CAUTION  ◆  {"  ◆  ".join(ALERTS)}</div>
    </body></html>"""

    hp = out_base + ".html"; open(hp, "w").write(html)
    png = out_base + ".png"
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--window-size=1600,1000",
                    "--allow-file-access-from-files", f"--screenshot={png}", "file://" + hp], capture_output=True, timeout=60)
    # close-up of the buttons (2x) so the machined detail is visible
    zp = out_base + "_buttons.png"
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--window-size=800,500", "--force-device-scale-factor=2",
                    "--allow-file-access-from-files", f"--screenshot={zp}", "file://" + hp + "#"], capture_output=True, timeout=60)
    print(png, os.path.exists(png))


if __name__ == "__main__":
    render(CSS, os.path.join(OUT, "MC_HUD_3R_Rugged_HMD"), "OPERATIONS COMMAND · RUGGED HMD")
