#!/usr/bin/env python3
"""MechWarrior-cockpit MC theme concepts (Jon 2026-10-16 22:06: rugged HMD "not what I was going for — more mech warrior").
Generates one drop-in theme CSS per variant (same contract as mission-control/theme-*.css: page variables + surfaces,
no layout changes) into ./mech/, then renders the populated preview (MC's own class names) per variant.
Nothing here is live; the chosen CSS gets copied to mission-control/ and wired into mc-theme.js."""
import os, subprocess
import hud_rugged_preview as prev

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "mech"); os.makedirs(OUT, exist_ok=True)

V = {
 "A_MW5_Mercenary_Orange": dict(label="A · MERCENARY", steel="#2a2d30", steel_hi="#4a4f54", steel_lo="#141618", plate="#1c1f22",
   acc="#ff7a1a", acc_dim="#8a3f08", screen="#0d0b07", phos="#ffb347", phos2="#ffe0a8", ok="#9be35a", warn="#ffd23d", bad="#ff3b2f"),
 "B_Inner_Sphere_Olive_CRT": dict(label="B · INNER SPHERE", steel="#3a3f2c", steel_hi="#5f6747", steel_lo="#1d2016", plate="#2b2f20",
   acc="#d4c25a", acc_dim="#6b6128", screen="#050a04", phos="#7dff4a", phos2="#d6ffc2", ok="#7dff4a", warn="#ffd23d", bad="#ff4a3a"),
 "C_Clan_Assault_Red": dict(label="C · CLAN ASSAULT", steel="#1e1f22", steel_hi="#3c3e43", steel_lo="#0b0b0d", plate="#151619",
   acc="#ff2a2a", acc_dim="#7a1010", screen="#0a0606", phos="#ff5a4a", phos2="#ffffff", ok="#7fe0a0", warn="#ffcc33", bad="#ff2a2a"),
}

DEFAULT_BG = """  background-color:{lo} !important;
  background-image:radial-gradient(ellipse at 50% 40%,transparent 40%,rgba(0,0,0,.75) 100%),
    repeating-linear-gradient(115deg,rgba(255,255,255,.018) 0 2px,transparent 2px 6px),
    linear-gradient(90deg,rgba(0,0,0,.35) 1px,transparent 1px) !important;
  background-size:auto,auto,120px 100% !important;"""


def stars(seed_layers):
    """Tiled starfield: each layer = (tile px, [(x%,y%,radius px,alpha)...])."""
    out, sizes = [], []
    for tile, pts in seed_layers:
        for x, y, r, a in pts:
            out.append(f"radial-gradient({r}px {r}px at {x}% {y}%,rgba(255,255,255,{a}),transparent)"); sizes.append(f"{tile}px {tile}px")
    return out, sizes


STARS = stars([(173, [(12, 18, 1, .9), (64, 71, 1, .6), (88, 33, 1.4, .8)]),
               (251, [(31, 52, 1, .7), (77, 9, 1.6, .9), (52, 88, 1, .5)]),
               (389, [(18, 77, 2, .95), (69, 41, 1.2, .7), (90, 90, 1, .6)]),
               (97, [(40, 60, .7, .45), (85, 15, .7, .4)])])


def space_bg(limb, nebula, base):
    """Mech x Space body: deep-space base, nebula wash, planet limb glowing at the bottom horizon, starfield."""
    st, sz = STARS
    layers = [f"radial-gradient(ellipse 140% 60% at 50% 128%,#000 58%,{limb} 60.5%,{limb}55 62%,transparent 70%)",
              f"radial-gradient(ellipse 60% 45% at 78% 22%,{nebula}33,transparent 70%)",
              f"radial-gradient(ellipse 50% 40% at 15% 60%,{nebula}1f,transparent 70%)"] + st
    sizes = ["100% 100%"] * 3 + sz
    return (f"  background-color:{base} !important;\n  background-image:{','.join(layers)} !important;\n"
            f"  background-size:{','.join(sizes)} !important;")


SPACE = {
 "S1_Exos_Orbital": dict(label="S1 · EXOS ORBITAL", steel="#2a2c2f", steel_hi="#55595e", steel_lo="#111214", plate="#1b1d20",
   acc="#F26A21", acc_dim="#7a3410", screen="#05070a", screen_a="rgba(5,7,10,.86)", phos="#ffb27a", phos2="#f4f6f8", ok="#9be35a", warn="#ffd23d", bad="#ff3b2f",
   space=("#F26A21", "#F26A21", "#020305")),
 "S2_Deep_Space_Nebula": dict(label="S2 · DEEP SPACE", steel="#262a33", steel_hi="#4f5666", steel_lo="#0e1015", plate="#191c23",
   acc="#b38cff", acc_dim="#4d3a7a", screen="#04050c", screen_a="rgba(4,5,12,.84)", phos="#9fd2ff", phos2="#eef4ff", ok="#7fffc4", warn="#ffd23d", bad="#ff4d6d",
   space=("#6fb6ff", "#8a5cff", "#010208")),
 "S3_Mars_Dropship": dict(label="S3 · MARS DROPSHIP", steel="#33291f", steel_hi="#6b5644", steel_lo="#140f0b", plate="#231b14",
   acc="#ff8c42", acc_dim="#7a3a15", screen="#0a0605", screen_a="rgba(10,6,5,.86)", phos="#ffc49a", phos2="#fff1e6", ok="#a8e05f", warn="#ffd23d", bad="#ff3b2f",
   space=("#d9542b", "#c0392b", "#070302")),
 "S4_Mars_Dropship_Earth_Limb": dict(label="MARS DROPSHIP · EARTH LIMB", steel="#33291f", steel_hi="#6b5644", steel_lo="#140f0b", plate="#231b14",
   acc="#ff8c42", acc_dim="#7a3a15", screen="#0a0605", screen_a="rgba(10,6,5,.86)", phos="#ffc49a", phos2="#fff1e6", ok="#a8e05f", warn="#ffd23d", bad="#ff3b2f",
   space=("#6fb6ff", "#c0392b", "#070302")),  # Jon 10/16 22:14: S3 but with S2's Earth atmosphere at the bottom
}
for _v in SPACE.values():
    _v["body_bg"] = space_bg(*_v.pop("space"))


BOLT = "radial-gradient(circle at {x} {y},{hi} 0 2px,{mid} 3px,{lo} 4px,transparent 4.6px)"


def css(v):
    bolts = ",".join(BOLT.format(x=x, y=y, hi=v["steel_hi"], mid=v["steel"], lo="#000") for x, y in
                     [("11px", "11px"), ("calc(100% - 11px)", "11px"), ("11px", "calc(100% - 11px)"), ("calc(100% - 11px)", "calc(100% - 11px)")])
    brushed = f"repeating-linear-gradient(115deg,rgba(255,255,255,.025) 0 2px,transparent 2px 5px),linear-gradient({v['steel']},{v['plate']})"
    key = f"radial-gradient(circle at 12px 50%,{{lamp}} 0 3px,rgba(0,0,0,.6) 4px,transparent 5px),linear-gradient({v['steel_hi']} 0%,{v['steel']} 45%,{v['plate']} 55%,{v['steel']} 100%)"
    sel_btn = "html body button:not(#mc-theme-toggle):not(.x), html body .btn, html body .filter-btn, html body .move-btn, html body input[type=submit], html body input[type=button]"
    nx = ":not(#mc-theme-toggle):not(.x)"
    return f"""/* Mission Control MECH cockpit theme {v['label']} (Jon 2026-10-16 "more mech warrior"). Opt-in; vars + surfaces only. */
:root, :root body {{
  --navy:{v['steel_lo']} !important; --navy2:{v['plate']} !important; --navy3:{v['steel']} !important;
  --card:{v['plate']} !important; --line:{v['steel_hi']} !important; --border:{v['steel_hi']} !important;
  --text:{v['phos2']} !important; --text2:{v['phos']} !important; --muted:{v['acc_dim']} !important;
  --blue:{v['steel']} !important; --blue2:{v['acc']} !important; --accent:{v['acc']} !important; --progress-accent:{v['acc']} !important;
  --orange:{v['warn']} !important; --orange2:{v['warn']} !important; --yellow:{v['warn']} !important; --purple:{v['acc']} !important;
  --green:{v['ok']} !important; --done-accent:{v['ok']} !important; --red:{v['bad']} !important; --blocked-accent:{v['bad']} !important;
}}
html body {{ font-family:'DIN Condensed','Avenir Next Condensed','Arial Narrow',sans-serif !important; letter-spacing:.04em;
{v.get('body_bg') or DEFAULT_BG.format(lo=v['steel_lo'])}
  background-attachment:fixed !important; }}
/* header = cockpit canopy frame: thick plate, hazard band, bolts */
html body header, html body .topbar {{ position:relative;
  background:{bolts},{brushed} !important; border-bottom:6px solid {v['steel_lo']} !important;
  box-shadow:inset 0 2px 0 {v['steel_hi']}, inset 0 -2px 0 #000, 0 4px 10px rgba(0,0,0,.8) !important; }}
html body header::after {{ content:''; position:absolute; left:0; right:0; bottom:-14px; height:8px; pointer-events:none;
  background:repeating-linear-gradient(-45deg,{v['warn']} 0 10px,#0b0b0b 10px 20px); box-shadow:0 2px 0 #000; }}
html body h1, html body h2 {{ color:{v['acc']} !important; text-transform:uppercase; letter-spacing:.18em; font-weight:700;
  text-shadow:0 2px 0 #000, 0 0 8px {v['acc']}55; }}
/* h3 = stamped ID plate */
html body h3, html body h4 {{ display:inline-block; color:{v['steel_lo']} !important; background:{v['acc']}; padding:3px 12px 2px !important;
  text-transform:uppercase; letter-spacing:.22em; font-weight:700; clip-path:polygon(0 0,calc(100% - 10px) 0,100% 100%,0 100%);
  box-shadow:inset 0 -2px 0 rgba(0,0,0,.35); text-shadow:none; }}
html body a {{ color:{v['acc']}; }}
/* panels = armor plate frame (bevel, big chamfer, 4 bolts) around a recessed CRT screen */
html body .card, html body .stat-card, html body .panel, html body .box, html body .doc-item, html body .hero, html body .modal, html body .modal-content, html body .column {{
  background:{bolts},radial-gradient(ellipse at 50% 0%,{v['phos']}10,transparent 70%),linear-gradient({v.get('screen_a', v['screen'])},{v.get('screen_a', v['screen'])}) padding-box,
    linear-gradient(135deg,{v['steel_hi']},{v['steel']} 40%,{v['steel_lo']}) border-box !important;
  border:8px solid transparent !important; border-radius:0 !important;
  clip-path:polygon(18px 0,100% 0,100% calc(100% - 18px),calc(100% - 18px) 100%,0 100%,0 18px);
  box-shadow:inset 0 0 0 1px #000, inset 0 0 24px rgba(0,0,0,.9), 0 6px 0 #000 !important; color:{v['phos2']}; }}
html body .card *, html body .stat-card * {{ text-shadow:0 0 5px {v['phos']}66; }}
html body .task-card {{ background:linear-gradient({v['screen']},{v['screen']}) !important; border:2px solid {v['steel_hi']} !important;
  border-left:6px solid {v['acc']} !important; border-radius:0 !important; box-shadow:inset 0 0 12px rgba(0,0,0,.8) !important; }}
/* buttons = chunky cockpit keys: thick bevel, 6px travel, status lamp at left */
{sel_btn} {{
  font-family:'DIN Condensed','Impact','Arial Narrow',sans-serif !important; font-weight:700 !important; text-transform:uppercase;
  letter-spacing:.16em !important; color:{v['phos2']} !important; padding-left:26px !important;
  background:{key.format(lamp=v['acc_dim'])} !important;
  border:2px solid #000 !important; border-top-color:{v['steel_hi']} !important; border-radius:0 !important;
  clip-path:polygon(8px 0,100% 0,100% calc(100% - 8px),calc(100% - 8px) 100%,0 100%,0 8px);
  box-shadow:inset 0 2px 0 rgba(255,255,255,.18), inset 0 -4px 0 rgba(0,0,0,.6), 0 6px 0 #000 !important;
  text-shadow:0 2px 0 #000 !important; transition:transform .06s, box-shadow .06s; }}
html body button:not(#mc-theme-toggle):not(.x):hover, html body .btn:hover, html body .filter-btn:hover {{
  background:{key.format(lamp=v['acc'])} !important; color:#fff !important; }}
html body button:not(#mc-theme-toggle):not(.x):active, html body .btn:active, html body .filter-btn:active {{
  transform:translateY(5px); box-shadow:inset 0 3px 6px rgba(0,0,0,.8), 0 1px 0 #000 !important; }}
html body .btn-primary{nx}, html body .btn.primary{nx}, html body .btn.green{nx}, html body .filter-btn.active{nx}, html body .opp-btn-save{nx} {{
  color:#111 !important; text-shadow:0 1px 0 rgba(255,255,255,.35) !important;
  background:radial-gradient(circle at 12px 50%,#fff 0 3px,{v['acc']} 4px,transparent 6px),linear-gradient({v['acc']} 0%,{v['acc']} 45%,{v['acc_dim']} 100%) !important;
  box-shadow:inset 0 2px 0 rgba(255,255,255,.45), inset 0 -4px 0 rgba(0,0,0,.45), 0 6px 0 #000, 0 0 14px {v['acc']}66 !important; }}
html body .btn-danger{nx}, html body .btn.danger{nx} {{ color:#fff !important;
  border:4px solid transparent !important;
  background:radial-gradient(circle at 10px 50%,{v['bad']} 0 3px,#000 4px,transparent 5px) padding-box,linear-gradient(#5a1010,#2a0606) padding-box,
    repeating-linear-gradient(-45deg,{v['warn']} 0 7px,#111 7px 14px) border-box !important;
  text-shadow:0 2px 0 #000 !important; box-shadow:0 6px 0 #000, 0 0 10px {v['bad']}55 !important; }}
html body .btn.ghost{nx}, html body .btn.secondary{nx}, html body .opp-btn-ghost{nx} {{ background:{key.format(lamp='#333')} !important; color:{v['phos']} !important; }}
html body input, html body select, html body textarea {{ background:{v['screen']} !important; color:{v['phos2']} !important;
  border:3px solid {v['steel_lo']} !important; border-top-color:#000 !important; border-bottom-color:{v['steel_hi']} !important; border-radius:0 !important;
  font-family:'Menlo','SF Mono',monospace !important; box-shadow:inset 0 3px 6px rgba(0,0,0,.9) !important; }}
html body input:focus, html body select:focus, html body textarea:focus {{ outline:2px solid {v['acc']} !important; }}
html body table th {{ color:{v['acc']} !important; letter-spacing:.18em; text-transform:uppercase; border-bottom:3px solid {v['steel_hi']} !important; }}
html body table td {{ border-color:{v['steel']} !important; font-family:'Menlo','SF Mono',monospace; font-size:.92em; }}
#mc-theme-toggle {{ position:fixed; left:12px; bottom:12px; z-index:2147483001; font:700 12px 'DIN Condensed','Arial Narrow',sans-serif; letter-spacing:.18em;
  background:linear-gradient({v['steel_hi']},{v['plate']}); color:{v['acc']}; border:2px solid #000; padding:7px 12px; cursor:pointer; box-shadow:0 4px 0 #000; }}
"""


if __name__ == "__main__":
    import sys
    todo = SPACE if "--space" in sys.argv else V
    if "--only" in sys.argv: todo = {k: v for k, v in todo.items() if k.startswith(sys.argv[sys.argv.index("--only") + 1])}
    for key, v in todo.items():
        p = os.path.join(OUT, f"theme-mech-{key.split('_')[0].lower()}.css"); open(p, "w").write(css(v))
        prev.render("file://" + p, os.path.join(OUT, f"MC_MECH_{key}"), f"OPERATIONS COMMAND · {v['label']}")
        print(key, "ok")
