#!/usr/bin/python3
"""Build Exos IDJ Japan intro/outro v2 (MC #2928). Real Exos hardware + Veo i2v seeded from real frames.
2026-10-05 PM: smokeless LOX/ethanol re-cut per #2928 note (v01_liftoff_ns2_a, v05_hover_ns).
Usage: /usr/bin/python3 build_v2.py intro|outro"""
import os, subprocess, sys, math, shutil
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = '/Users/exomac/.openclaw/workspace'
D = f'{ROOT}/drafts/idj_video_v2'
W = f'{D}/work'
V = f'{W}/veo'
M = f'{ROOT}/media/blk3-footage'
FPS = 30
ORANGE = (242, 106, 33)
FONT_EN = '/System/Library/Fonts/Avenir Next.ttc'
FONT_JP = '/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc'
FONT_JP_B = '/System/Library/Fonts/ヒラギノ角ゴシック W8.ttc'
GRADE = ("eq=contrast=1.10:saturation=1.06:gamma=0.97,"
         "curves=master='0/0 0.06/0.02 0.5/0.5 0.94/0.97 1/1',"
         "vignette=angle=PI/5,noise=alls=5:allf=t")


def sh(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if r.returncode:
        print(cmd); print(r.stderr[-2000:]); sys.exit(1)


def seg(out, src, ss, dur, speed=1.0, zoom=(1.0, 1.06), cx=0.5, cy=0.5, still=False, crop=None, extra=''):
    """Render one graded 1920x1080@30 segment of exactly dur seconds."""
    n = int(round(dur * FPS))
    z0, z1 = zoom
    pre = (f"crop={crop}," if crop else '') + "scale=2880:1620:flags=lanczos,setsar=1,"
    zp = (f"zoompan=z='{z0}+({z1}-{z0})*on/{n}':d={1 if not still else n}:"
          f"x='(iw-iw/zoom)*{cx}':y='(ih-ih/zoom)*{cy}':s=1920x1080:fps={FPS}")
    if still:
        inp = f"-i '{src}'"
        vf = pre + zp
    else:
        inp = f"-ss {ss} -i '{src}'"
        vf = f"setpts=PTS/{speed},fps={FPS}," + pre + zp
    vf += ',' + GRADE + (',' + extra if extra else '') + ',format=yuv420p'
    sh(f"ffmpeg -v error -y {inp} -vf \"{vf}\" -frames:v {n} -an -c:v libx264 -preset medium -crf 14 '{out}'")


def black(out, dur):
    sh(f"ffmpeg -v error -y -f lavfi -i color=c=black:s=1920x1080:r={FPS} -t {dur} -c:v libx264 -crf 14 -pix_fmt yuv420p '{out}'")


# ---------- typography helpers ----------
def font(p, s, i=0):
    return ImageFont.truetype(p, s, index=i)


def ease(x):
    x = max(0.0, min(1.0, x)); return 1 - (1 - x) ** 3


def text_w(f, s, track=0):
    return sum(f.getlength(c) for c in s) + track * (len(s) - 1)


def draw_tracked(d, xy, s, f, fill, track=0):
    x, y = xy
    for c in s:
        d.text((x, y), c, font=f, fill=fill); x += f.getlength(c) + track


def kinetic(img, t, t0, t1, en, jp, size=136, y=690):
    """Big heavy italic word: slide-up + tracking tighten, orange rule, JP supertitle. t in seconds."""
    if t < t0 or t > t1: return
    a_in, a_out = ease((t - t0) / 0.35), ease((t1 - t) / 0.2)
    a = min(a_in, a_out)
    f = font(FONT_EN, size, 9)
    track = 18 * (1 - a_in) + 2
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    tw = text_w(f, en, track); x = (1920 - tw) / 2; yy = y + 40 * (1 - a_in)
    # soft dark scrim for legibility over bright plumes/dust
    sc = Image.new('RGBA', img.size, (0, 0, 0, 0)); dsc = ImageDraw.Draw(sc)
    dsc.ellipse([960 - tw * 0.62, y - 30, 960 + tw * 0.62, y + size * 1.22 + 110], fill=(0, 0, 0, int(110 * a)))
    img.alpha_composite(sc.filter(ImageFilter.GaussianBlur(45)))
    # soft shadow
    sh_l = Image.new('RGBA', img.size, (0, 0, 0, 0)); ds = ImageDraw.Draw(sh_l)
    draw_tracked(ds, (x + 4, yy + 6), en, f, (0, 0, 0, int(150 * a)), track)
    sh_l = sh_l.filter(ImageFilter.GaussianBlur(10)); img.alpha_composite(sh_l)
    draw_tracked(d, (x, yy), en, f, (255, 255, 255, int(255 * a)), track)
    # orange rule draws on
    rw = int(min(tw, 420) * ease((t - t0 - 0.12) / 0.3))
    ry = int(y + size * 1.22)
    if rw > 0:
        d.rectangle([960 - rw // 2, ry, 960 + rw // 2, ry + 7], fill=ORANGE + (int(255 * a),))
    if jp:
        fj = font(FONT_JP, 46); jw = fj.getlength(jp)
        aj = min(ease((t - t0 - 0.2) / 0.3), a_out)
        d.text(((1920 - jw) / 2, ry + 26), jp, font=fj, fill=(255, 255, 255, int(235 * aj)))
    img.alpha_composite(lay)


def label(img, t, t0, t1, en, jp):
    """Lower-left documentary label: orange bar + small caps EN + JP."""
    if t < t0 or t > t1: return
    a = min(ease((t - t0) / 0.3), ease((t1 - t) / 0.2))
    d = ImageDraw.Draw(img)
    f = font(FONT_EN, 40, 0); fj = font(FONT_JP, 32)
    x = 110 - 30 * (1 - a); y = 880
    d.rectangle([x, y, x + 8, y + 104], fill=ORANGE + (int(255 * a),))
    draw_tracked(d, (x + 30, y - 2), en, f, (255, 255, 255, int(255 * a)), 3)
    d.text((x + 30, y + 58), jp, font=fj, fill=(235, 235, 235, int(235 * a)))


def bug(img, t, t0, t1):
    if t < t0 or t > t1: return
    lg = LOGO_SMALL.copy(); a = lg.split()[3].point(lambda v: int(v * 0.85)); lg.putalpha(a)
    img.alpha_composite(lg, (1920 - lg.width - 60, 50))


def logo_reveal(img, t, t0, cy=430, w=900):
    """Logo fades dark-grey -> white with a light sweep (Moonshots wordmark treatment)."""
    if t < t0: return
    p = ease((t - t0) / 1.4)
    lg = LOGO.resize((w, int(LOGO.height * w / LOGO.width)), Image.LANCZOS)
    g = int(90 + 165 * p)
    col = Image.new('RGBA', lg.size, (g, g, g, 255)); col.putalpha(lg.split()[3].point(lambda v: int(v * min(1, p * 1.6))))
    # sweep
    sx = (t - t0 - 0.3) / 1.0
    if 0 < sx < 1.2:
        sw = Image.new('L', lg.size, 0); ds = ImageDraw.Draw(sw)
        cx = int(-200 + sx * (lg.width + 400))
        ds.polygon([(cx - 60, 0), (cx + 40, 0), (cx - 40, lg.height), (cx - 140, lg.height)], fill=255)
        sw = sw.filter(ImageFilter.GaussianBlur(25))
        white = Image.new('RGBA', lg.size, (255, 255, 255, 0))
        m = Image.composite(lg.split()[3], Image.new('L', lg.size, 0), sw)
        white.putalpha(m); col.alpha_composite(white)
    img.alpha_composite(col, ((1920 - lg.width) // 2, cy - lg.height // 2))


def streak(img, t, t0, dur=0.7, y0=640, y1=560):
    """Orange light streak racing across frame (brand accent)."""
    if t < t0 or t > t0 + dur + 0.5: return
    p = ease((t - t0) / dur); fade = 1 - max(0, (t - t0 - dur) / 0.5)
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    hx = -100 + p * 2200; tx = hx - 900
    yh = y0 + (y1 - y0) * (hx / 1920); yt = y0 + (y1 - y0) * (tx / 1920)
    for wdt, al in ((22, 60), (10, 140), (4, 255)):
        d.line([(tx, yt), (hx, yh)], fill=ORANGE + (int(al * fade),), width=wdt)
    glow = lay.filter(ImageFilter.GaussianBlur(14)); img.alpha_composite(glow); img.alpha_composite(lay)
    d2 = ImageDraw.Draw(img); d2.ellipse([hx - 8, yh - 8, hx + 8, yh + 8], fill=(255, 220, 190, int(255 * fade)))


def fade_text(img, t, t0, t1, s, f, y, fill=(255, 255, 255), track=0, center=True, x=0):
    if t < t0 or t > t1: return
    a = min(ease((t - t0) / 0.4), ease((t1 - t) / 0.3))
    d = ImageDraw.Draw(img); tw = text_w(f, s, track)
    draw_tracked(d, ((1920 - tw) / 2 if center else x, y), s, f, fill + (int(255 * a),), track)


def paste_fade(img, t, t0, t1, im, xy):
    if t < t0 or t > t1: return
    a = min(ease((t - t0) / 0.4), ease((t1 - t) / 0.3))
    c = im.copy(); c.putalpha(im.split()[3].point(lambda v: int(v * a))); img.alpha_composite(c, xy)


LOGO = Image.open(f'{ROOT}/drafts/_exos_white_official.png').convert('RGBA')
LOGO_SMALL = LOGO.resize((150, int(LOGO.height * 150 / LOGO.width)), Image.LANCZOS)
SA = Image.open(f'{ROOT}/drafts/_spaceavailable_white.png').convert('RGBA')
SA_W = SA.resize((620, int(SA.height * 620 / SA.width)), Image.LANCZOS)


def flash(img, t, at, dur=0.07):
    if at <= t < at + dur:
        img.alpha_composite(Image.new('RGBA', img.size, (255, 255, 255, 200)))


# ---------- timelines ----------
def intro():
    pad = f'{V}/v10_pad.mp4' if os.path.exists(f'{V}/v10_pad.mp4') and os.environ.get('USE_V10') else None
    src = f'{M}/sarge_flight_source.mp4'
    CROP = '1244:700:308:380'   # removes burned-in title from source liftoff footage
    shots = []
    if pad:
        shots.append(('s01', pad, 0.3, 2.0, dict(zoom=(1.0, 1.04))))
    else:
        shots.append(('s01', src, 0.2, 2.0, dict(crop=CROP, zoom=(1.0, 1.10), cy=0.35)))
    shots += [
        ('s02', f'{V}/v01_liftoff_ns2_a.mp4', 4.0, 2.5, dict(zoom=(1.02, 1.08), cy=0.3)),
        ('s03', src, 4.2, 1.5, dict(crop=CROP, zoom=(1.0, 1.05), cy=0.4)),
        ('s04', f'{V}/v07_ascent2.mp4', 3.0, 2.0, dict(zoom=(1.0, 1.04), cy=0.3)),
        ('s05', f'{V}/v03_limb.mp4', 0.4, 2.0, dict(zoom=(1.0, 1.05))),
        ('s06', f'{V}/v04_sep.mp4', 0.3, 1.5, dict(speed=0.75, zoom=(1.0, 1.06), cx=0.6, cy=0.5)),
        ('s07', f'{M}/build/05_drogue.mp4', 0.4, 1.5, dict(zoom=(1.0, 1.06))),
        ('s08', f'{M}/build/06_parafoil.mp4', 0.2, 2.0, dict(zoom=(1.16, 1.24), cx=0.12, cy=0.5)),
        ('s09', f'{M}/SARGE_recovery_ops.jpg', 0, 1.5, dict(still=True, zoom=(1.04, 1.12), cy=0.3)),
        ('s10', f'{V}/v09_hangar.mp4', 0.0, 2.0, dict(zoom=(1.0, 1.04))),
        ('s11', f'{V}/v05_hover_ns.mp4', 1.2, 1.7, dict(zoom=(1.0, 1.05), cy=0.3)),
        ('BLACK', None, 0, 1.3, {}),
        ('s13', f'{V}/v03_limb.mp4', 3.0, 4.6, dict(speed=0.8, zoom=(1.04, 1.16), cy=0.6,
                                                    extra='eq=brightness=-0.06:saturation=0.85')),
    ]
    total = sum(s[3] for s in shots)

    def ov(i):
        t = i / FPS
        img = Image.new('RGBA', (1920, 1080), (0, 0, 0, 0))
        fe = font(FONT_EN, 44, 2); fj = font(FONT_JP, 30)
        fade_text(img, t, 0.15, 1.95, 'EXOS AEROSPACE', fe, 900, track=14)
        fade_text(img, t, 0.35, 1.95, 'エクソス・エアロスペース', fj, 965, (230, 230, 230))
        kinetic(img, t, 2.30, 4.45, 'REUSABLE.', '再使用型ロケット')
        kinetic(img, t, 4.55, 5.95, 'SUBORBITAL.', 'サブオービタル（準軌道）')
        label(img, t, 6.10, 7.95, 'SARGE  |  FLIGHT FOOTAGE', 'SARGE 実飛行映像')
        kinetic(img, t, 8.10, 9.95, 'FLOWN.', '飛行実証済み')
        label(img, t, 10.05, 11.45, 'NOSE CONE SEPARATION', 'ノーズコーン分離')
        kinetic(img, t, 13.10, 14.95, 'RECOVERED.', '機体を回収')
        kinetic(img, t, 15.05, 16.45, 'BUILT TO FLY AGAIN.', 'くり返し飛ぶために', size=120)
        kinetic(img, t, 16.60, 18.45, 'NEXT: BLK3', '次世代機 BLK3', size=140)
        label(img, t, 18.55, 20.15, 'BLK3  |  TETHERED TEST  |  IN DEVELOPMENT', 'BLK3 係留試験・開発中')
        bug(img, t, 2.0, 20.2)
        for at in (2.0, 8.0, 13.0, 16.5):
            flash(img, t, at)
        # sting
        T = 21.5
        logo_reveal(img, t, T + 0.1, cy=420, w=860)
        streak(img, t, T + 1.1, y0=760, y1=640)
        paste_fade(img, t, T + 1.9, total, SA_W, ((1920 - SA_W.width) // 2, 640))
        fade_text(img, t, T + 2.3, total, 'JAPAN INNOVATION DOJO  2026', font(FONT_EN, 34, 2), 760, track=10)
        fade_text(img, t, T + 2.6, total, '日本と共に、宇宙へ。', font(FONT_JP_B, 44), 820)
        if t > total - 0.5:
            img.alpha_composite(Image.new('RGBA', img.size, (0, 0, 0, int(255 * ease((t - total + 0.5) / 0.5)))))
        return img

    score = [('a', 6.0, 2.0), ('b', 36.0, total - 2.0)]
    sfx = dict(roar=(f'{V}/v01_liftoff_ns2_a.mp4', 4.0, 2.0, 2.5, 0.55),   # (file, ss, at, dur, vol)
               roar2=(f'{V}/v07_ascent2.mp4', 3.0, 6.0, 2.0, 0.30))
    build('Intro', shots, ov, total, score, sfx, booms=(2.0, 21.5), whoosh=(20.4,))


def outro():
    shots = [
        ('o1', f'{V}/v01_liftoff_ns2_a.mp4', 4.5, 1.5, dict(zoom=(1.03, 1.08), cy=0.3)),
        ('o2', f'{V}/v07_ascent2.mp4', 4.0, 1.5, dict(zoom=(1.0, 1.04), cy=0.3)),
        ('o3', f'{V}/v03_limb.mp4', 1.0, 1.5, dict(zoom=(1.0, 1.05))),
        ('o4', f'{M}/build/06_parafoil.mp4', 0.8, 1.2, dict(zoom=(1.16, 1.22), cx=0.12, cy=0.5)),
        ('o5', f'{V}/v05_hover_ns.mp4', 2.0, 1.0, dict(zoom=(1.0, 1.04), cy=0.3)),
        ('BLACK', None, 0, 1.3, {}),
        ('END', None, 0, 5.0, {}),
    ]
    total = sum(s[3] for s in shots)
    grid = Image.new('RGBA', (1920, 1080), (8, 8, 9, 255)); dg = ImageDraw.Draw(grid)
    for x in range(0, 1920, 60): dg.line([(x, 0), (x, 1080)], fill=(38, 38, 41, 255))
    for y in range(0, 1080, 60): dg.line([(0, y), (1920, y)], fill=(38, 38, 41, 255))
    vig = Image.radial_gradient('L').resize((1920, 1080)).point(lambda v: int(min(255, v * 1.1)))
    grid = Image.composite(Image.new('RGBA', grid.size, (0, 0, 0, 255)), grid, vig)

    def ov(i):
        t = i / FPS
        img = Image.new('RGBA', (1920, 1080), (0, 0, 0, 0))
        kinetic(img, t, 0.25, 3.0, 'FLOWN. RECOVERED.', '飛行・回収を実証', size=120)
        kinetic(img, t, 3.05, 6.65, "LET'S BUILD IT TOGETHER.", '共に、宇宙の未来をつくる。', size=110)
        bug(img, t, 0, 6.7)
        flash(img, t, 0.0); flash(img, t, 3.0)
        E = 8.0
        if t >= E:
            a = ease((t - E) / 0.25); g = grid.copy(); g.putalpha(int(255 * a)); img.alpha_composite(g)
            logo_reveal(img, t, E + 0.05, cy=330, w=620)
            streak(img, t, E + 0.6, y0=520, y1=500)
            fade_text(img, t, E + 0.9, total, 'THANK YOU', font(FONT_EN, 110, 9), 470, track=6)
            fade_text(img, t, E + 1.1, total, 'ありがとうございました', font(FONT_JP_B, 52), 615)
            paste_fade(img, t, E + 1.5, total, SA_W, ((1920 - SA_W.width) // 2, 712))
            # entity line (Lizi/John note on #2928, 10/5): Japan entity named on the end card
            fade_text(img, t, E + 1.7, total, 'EXOS AEROSPACE SYSTEMS JAPAN', font(FONT_EN, 48, 2), 800, track=10)
            fade_text(img, t, E + 2.0, total, 'exosaero.com    |    @exosaero', font(FONT_EN, 34, 2), 910,
                      fill=(200, 200, 200), track=4)
        if t > total - 0.4:
            img.alpha_composite(Image.new('RGBA', img.size, (0, 0, 0, int(255 * ease((t - total + 0.4) / 0.4)))))
        return img

    score = [('c', 47.5, total - 0.4)]
    sfx = dict(roar=(f'{V}/v01_liftoff_ns2_a.mp4', 4.5, 0.0, 1.5, 0.45))
    build('Outro', shots, ov, total, score, sfx, booms=(0.0, 8.0), whoosh=(6.9,))


def build(name, shots, ov, total, score, sfx, booms, whoosh):
    wd = f'{W}/build_{name}'; os.makedirs(wd, exist_ok=True)
    segs = []
    for sid, src, ss, dur, kw in shots:
        out = f'{wd}/{sid}.mp4'
        if src is None:
            black(out, dur)
        else:
            seg(out, src, ss, dur, **kw)
        segs.append(out)
    open(f'{wd}/list.txt', 'w').write(''.join(f"file '{s}'\n" for s in segs))
    sh(f"ffmpeg -v error -y -f concat -safe 0 -i '{wd}/list.txt' -c copy '{wd}/base.mp4'")
    # overlay frames
    od = f'{wd}/ov'; shutil.rmtree(od, ignore_errors=True); os.makedirs(od)
    n = int(round(total * FPS))
    for i in range(n):
        ov(i).save(f'{od}/{i:05d}.png', compress_level=1)
    # audio: score
    sc = f'{W}/score_intro.mp3'
    parts = []
    for k, (lab, ss, dur) in enumerate(score):
        p = f'{wd}/score_{lab}.wav'
        sh(f"ffmpeg -v error -y -ss {ss} -t {dur} -i '{sc}' -ar 48000 -ac 2 -af 'afade=t=in:d=0.02,afade=t=out:st={dur-0.03}:d=0.03' '{p}'")
        parts.append(p)
    ins = ''.join(f"-i '{p}' " for p in parts)
    sh(f"ffmpeg -v error -y {ins} -filter_complex 'concat=n={len(parts)}:v=0:a=1,apad' -t {total} '{wd}/score.wav'")
    # sfx: veo native audio, sub booms, whooshes
    inputs = [f"-i '{wd}/score.wav'"]; filt = []; mix = ['[0]']
    k = 1
    for nm, (f, ss, at, dur, vol) in sfx.items():
        inputs.append(f"-ss {ss} -t {dur} -i '{f}'")
        filt.append(f"[{k}:a]aresample=48000,volume={vol},afade=t=out:st={dur-0.4}:d=0.4,adelay={int(at*1000)}|{int(at*1000)}[x{k}]")
        mix.append(f'[x{k}]'); k += 1
    for at in booms:
        inputs.append("-f lavfi -t 2.5 -i 'sine=f=42:r=48000'")
        filt.append(f"[{k}:a]volume=0.9,afade=t=in:d=0.01,afade=t=out:st=0.05:d=2.4,aformat=channel_layouts=stereo,adelay={int(at*1000)}|{int(at*1000)}[x{k}]")
        mix.append(f'[x{k}]'); k += 1
    for at in whoosh:
        inputs.append("-f lavfi -t 1.2 -i 'anoisesrc=c=pink:r=48000:a=0.5'")
        filt.append(f"[{k}:a]highpass=f=300,lowpass=f=4000,afade=t=in:d=0.9:curve=exp,afade=t=out:st=0.9:d=0.3,volume=0.35,aformat=channel_layouts=stereo,adelay={int(at*1000)}|{int(at*1000)}[x{k}]")
        mix.append(f'[x{k}]'); k += 1
    fc = ';'.join(filt) + ';' + ''.join(mix) + f"amix=inputs={len(mix)}:normalize=0:duration=first,alimiter=limit=0.9,loudnorm=I=-16:TP=-1.5:LRA=11[a]"
    sh(f"ffmpeg -v error -y {' '.join(inputs)} -filter_complex \"{fc}\" -map '[a]' -ar 48000 -t {total} '{wd}/mix.wav'")
    out = f'{D}/Exos_IDJ_Japan_{name}_{os.environ.get("VER", "v2")}_2026-10-05.mp4'
    sh(f"ffmpeg -v error -y -i '{wd}/base.mp4' -framerate {FPS} -i '{od}/%05d.png' -i '{wd}/mix.wav' "
       f"-filter_complex '[0:v][1:v]overlay=0:0:format=auto,format=yuv420p[v]' -map '[v]' -map 2:a "
       f"-c:v libx264 -preset slow -crf 17 -profile:v high -pix_fmt yuv420p -r {FPS} -c:a aac -b:a 256k -ar 48000 "
       f"-movflags +faststart -t {total} '{out}'")
    print('OK', out, total)


if __name__ == '__main__':
    {'intro': intro, 'outro': outro}[sys.argv[1]]()
