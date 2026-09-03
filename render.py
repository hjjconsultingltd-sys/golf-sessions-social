#!/usr/bin/env python3
"""
Golf Sessions social renderer (GitHub Actions edition).

Renders brand-exact PNGs from the templates in the brand pack (v1.0):
  statement   split panel, one headline                  1080x1350 / 1080x1080 / 1080x1920
  numeral     hero number on ink                          1080x1350 / 1080x1080
  match       match result share graphic, team colours   1080x1080 / 1080x1920
  testimonial split panel, a quote                        1080x1350 / 1080x1080
  cover       page cover, split lockup                    1584x396 (LinkedIn) / 1200x630 (OG)
  carousel    one page of a format explainer             1080x1350 (alternating ink/paper)
  photo       photograph on top, type on an ink scrim    1080x1350 / 1080x1080

Usage:
  python3 render.py --fonts              # download and instantiate the brand fonts into fonts/
  python3 render.py --all                # render every spec in specs/ whose hash changed (uses out/manifest.json)
  python3 render.py specs/w2-04.json     # render one spec file (an object or a list of objects)
  python3 render.py --demo               # one of everything into out/

A spec is {"id": "w2-04-1", "template": "carousel", "size": "portrait", "fields": {...}}.
Output is always out/<id>.png. A spec file may hold one spec or a list of specs (a carousel).

Brand rules enforced here, not left to chance: monochrome only (team colours
only on the match template), Big Shoulders Display 900/700 for display, Instrument
Sans 400/500/600 for everything else, radius 0, no shadows, tabular numerals,
halves as the ½ glyph, hairlines 1px, panels bleed, text never does, 34/66 split.
"""
import json, sys, os, asyncio, html, hashlib, glob, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "fonts")
SPECS = os.path.join(HERE, "specs")
OUT = os.path.join(HERE, "out")
PHOTOS = os.path.join(HERE, "photos")
MANIFEST = os.path.join(OUT, "manifest.json")

INK, G900, G700, G500, G300, G100, PAPER = "#0A0A0A", "#202024", "#3C3C44", "#70707A", "#ADADB6", "#E4E4E9", "#FAFAFA"
HAIR_L, HAIR_D = "#D8D8DE", "#3C3C44"

SIZES = {
    "portrait": (1080, 1350), "square": (1080, 1080), "story": (1080, 1920),
    "linkedin_cover": (1584, 396), "og": (1200, 630), "facebook_cover": (1640, 624),
}

FONT_SOURCES = {
    "BigShouldersDisplay.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/bigshouldersdisplay/BigShouldersDisplay%5Bwght%5D.ttf",
    "InstrumentSans-VF.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/instrumentsans/InstrumentSans%5Bwdth,wght%5D.ttf",
}


def fetch_fonts():
    """Download the two variable fonts from google/fonts and instantiate Instrument Sans at 400/500/600."""
    os.makedirs(FONTS, exist_ok=True)
    for name, url in FONT_SOURCES.items():
        path = os.path.join(FONTS, name)
        if not os.path.exists(path):
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req) as r, open(path, "wb") as f:
                f.write(r.read())
    from fontTools.ttLib import TTFont
    from fontTools.varLib import instancer
    vf = os.path.join(FONTS, "InstrumentSans-VF.ttf")
    for wght, label in ((400, "Regular"), (500, "Medium"), (600, "SemiBold")):
        target = os.path.join(FONTS, f"InstrumentSans-{label}.ttf")
        if os.path.exists(target):
            continue
        font = TTFont(vf)
        inst = instancer.instantiateVariableFont(font, {"wght": wght, "wdth": 100})
        inst.save(target)
    print("fonts ready in", FONTS)


CSS = f"""
@font-face {{ font-family: "Big Shoulders Display"; src: url("file://{FONTS}/BigShouldersDisplay.ttf"); font-weight: 100 900; }}
@font-face {{ font-family: "Instrument Sans"; src: url("file://{FONTS}/InstrumentSans-Regular.ttf"); font-weight: 400; }}
@font-face {{ font-family: "Instrument Sans"; src: url("file://{FONTS}/InstrumentSans-Medium.ttf"); font-weight: 500; }}
@font-face {{ font-family: "Instrument Sans"; src: url("file://{FONTS}/InstrumentSans-SemiBold.ttf"); font-weight: 600; }}
* {{ box-sizing: border-box; margin: 0; padding: 0; border-radius: 0 !important; box-shadow: none !important; }}
html, body {{ width: 100%; height: 100%; overflow: hidden; }}
body {{ font-family: "Instrument Sans", sans-serif; -webkit-font-smoothing: antialiased; font-variant-numeric: tabular-nums; }}
.display {{ font-family: "Big Shoulders Display", sans-serif; font-weight: 900; text-transform: uppercase; letter-spacing: -0.01em; line-height: 0.88; }}
.display-700 {{ font-family: "Big Shoulders Display", sans-serif; font-weight: 700; text-transform: uppercase; letter-spacing: -0.01em; line-height: 0.92; }}
.eyebrow {{ font-weight: 600; text-transform: uppercase; letter-spacing: 0.16em; }}
.body {{ font-weight: 400; line-height: 1.6; }}
.label {{ font-weight: 500; }}
.canvas {{ position: relative; width: 100%; height: 100%; }}
"""


def esc(s):
    return html.escape(str(s)).replace("\n", "<br>")


def half(s):
    # 8.5 -> 8½, 0.5 -> ½; the brand sets halves as the glyph, never .5
    s = str(s)
    if s.endswith(".5"):
        head = s[:-2]
        return ("" if head in ("0", "") else head) + "½"
    return s


# ---------- templates ----------

def statement(f, W, H):
    pad = round(W * 0.05)
    split = round(W * 0.34)
    head = f.get("headline", "EVERY HOLE COUNTS.")
    sub = f.get("sub", "")
    eyebrow = f.get("eyebrow", "GOLF SESSIONS")
    size = f.get("headline_size", round(W * 0.155))
    # the eyebrow must stay on the 34% ink panel: box it to the panel width and let the fit guard shrink it
    return f"""
<div class="canvas" style="background:{PAPER}">
  <div style="position:absolute;left:0;top:0;width:{split}px;height:100%;background:{INK}"></div>
  <div class="eyebrow fit" style="position:absolute;left:{pad}px;top:{pad}px;width:{split-2*pad}px;font-size:{round(W*0.018)}px;line-height:1.5;color:{G300}">{esc(eyebrow).replace(' · ', '<br>')}</div>
  <div style="position:absolute;left:{split+pad}px;right:{pad}px;top:50%;transform:translateY(-50%)">
    <div class="display" style="font-size:{size}px;color:{INK};text-wrap:balance">{esc(head)}</div>
    {f'<div class="body" style="margin-top:{round(W*0.035)}px;font-size:{round(W*0.028)}px;color:{G700};max-width:26ch">{esc(sub)}</div>' if sub else ''}
  </div>
  <div class="label" style="position:absolute;right:{pad}px;bottom:{pad}px;font-size:{round(W*0.02)}px;color:{G500}">golf-sessions.com</div>
</div>"""


def numeral(f, W, H):
    pad = round(W * 0.06)
    num = half(f.get("number", "469"))
    eyebrow = f.get("eyebrow", "THE AGENCY CHALLENGE CUP 2026")
    line = f.get("line", "POINTS SCORED LIVE")
    body = f.get("body", "28 players. 3 days. 3 formats. Celtic Manor.")
    return f"""
<div class="canvas" style="background:{INK}">
  <div class="eyebrow" style="position:absolute;left:{pad}px;top:{pad}px;font-size:{round(W*0.018)}px;color:{G300}">{esc(eyebrow)}</div>
  <div style="position:absolute;left:{pad}px;right:{pad}px;top:50%;transform:translateY(-52%)">
    <div class="display" style="font-size:{round(H*0.38)}px;color:{PAPER};line-height:0.82">{esc(num)}</div>
    <div class="display-700" style="margin-top:{round(W*0.02)}px;font-size:{round(W*0.07)}px;color:{PAPER}">{esc(line)}</div>
    <div class="body" style="margin-top:{round(W*0.025)}px;font-size:{round(W*0.028)}px;color:{G300};max-width:30ch">{esc(body)}</div>
  </div>
  <div style="position:absolute;left:{pad}px;right:{pad}px;bottom:{pad+round(W*0.045)}px;height:1px;background:{HAIR_D}"></div>
  <div class="label" style="position:absolute;right:{pad}px;bottom:{pad}px;font-size:{round(W*0.02)}px;color:{G500}">golf-sessions.com</div>
  <div class="display" style="position:absolute;left:{pad}px;bottom:{pad-4}px;font-size:{round(W*0.03)}px;color:{PAPER}">GOLF SESSIONS</div>
</div>"""


def match(f, W, H):
    a, b = f.get("team_a", "NORTHSIDE"), f.get("team_b", "HARBOUR")
    ca, cb = f.get("colour_a", "#1B2A4A"), f.get("colour_b", "#7A1F2E")
    sa, sb = half(f.get("score_a", "8.5")), half(f.get("score_b", "6.5"))
    top = f.get("eyebrow", "SESSION 2 · SATURDAY FOURSOMES")
    status = f.get("status", "FINAL")
    line = f.get("line", "")
    strip = round(H * 0.075)
    pad = round(W * 0.045)
    return f"""
<div class="canvas" style="background:{INK}">
  <div style="position:absolute;left:0;top:{strip}px;width:50%;bottom:{strip}px;background:{ca}"></div>
  <div style="position:absolute;left:50%;top:{strip}px;width:50%;bottom:{strip}px;background:{cb}"></div>
  <div class="eyebrow" style="position:absolute;left:{pad}px;top:0;height:{strip}px;line-height:{strip}px;font-size:{round(W*0.018)}px;color:{G300}">{esc(top)}</div>
  <div class="eyebrow" style="position:absolute;right:{pad}px;top:0;height:{strip}px;line-height:{strip}px;font-size:{round(W*0.018)}px;color:{PAPER}">{esc(status)}</div>
  <div style="position:absolute;left:{pad}px;width:calc(50% - {pad*1.5}px);top:50%;transform:translateY(-50%);color:{PAPER}">
    <div class="display-700" style="font-size:{round(W*0.062)}px">{esc(a)}</div>
    <div class="display" style="font-size:{round(W*0.28)}px;line-height:0.85;margin-top:{round(W*0.02)}px">{esc(sa)}</div>
  </div>
  <div style="position:absolute;right:{pad}px;width:calc(50% - {pad*1.5}px);top:50%;transform:translateY(-50%);color:{PAPER};text-align:right">
    <div class="display-700" style="font-size:{round(W*0.062)}px">{esc(b)}</div>
    <div class="display" style="font-size:{round(W*0.28)}px;line-height:0.85;margin-top:{round(W*0.02)}px">{esc(sb)}</div>
  </div>
  {f'<div class="body" style="position:absolute;left:{pad}px;right:{pad}px;bottom:{strip+pad}px;text-align:center;font-size:{round(W*0.026)}px;color:{PAPER};font-weight:500">{esc(line)}</div>' if line else ''}
  <div class="display" style="position:absolute;left:{pad}px;bottom:0;height:{strip}px;line-height:{strip}px;font-size:{round(W*0.03)}px;color:{PAPER}">GOLF SESSIONS</div>
  <div class="label" style="position:absolute;right:{pad}px;bottom:0;height:{strip}px;line-height:{strip}px;font-size:{round(W*0.02)}px;color:{G500}">golf-sessions.com</div>
</div>"""


def testimonial(f, W, H):
    pad = round(W * 0.05)
    split = round(W * 0.34)
    quote = f.get("quote", "")
    name = f.get("name", "")
    role = f.get("role", "")
    return f"""
<div class="canvas" style="background:{PAPER}">
  <div style="position:absolute;left:0;top:0;width:{split}px;height:100%;background:{INK}"></div>
  <div class="display" style="position:absolute;left:{pad}px;top:{pad-round(W*0.02)}px;font-size:{round(W*0.32)}px;color:{PAPER};line-height:1">&ldquo;</div>
  <div class="eyebrow" style="position:absolute;left:{pad}px;bottom:{pad}px;font-size:{round(W*0.018)}px;color:{G300}">GOLF SESSIONS</div>
  <div style="position:absolute;left:{split+pad}px;right:{pad}px;top:50%;transform:translateY(-50%)">
    <div class="label" style="font-size:{round(W*0.036)}px;line-height:1.35;color:{INK};text-wrap:pretty">{esc(quote)}</div>
    <div style="height:1px;background:{HAIR_L};margin:{round(W*0.04)}px 0"></div>
    <div class="display-700" style="font-size:{round(W*0.045)}px;color:{INK}">{esc(name)}</div>
    <div class="body" style="font-size:{round(W*0.022)}px;color:{G500};margin-top:6px">{esc(role)}</div>
  </div>
  <div class="label" style="position:absolute;right:{pad}px;bottom:{pad}px;font-size:{round(W*0.02)}px;color:{G500}">golf-sessions.com</div>
</div>"""


def cover(f, W, H):
    # split lockup: GOLF on paper, SESSIONS on ink, 34/66, baselines aligned
    size = round(H * 0.42)
    tag = f.get("tagline", "Team golf, broadcast. Live scoring on every phone, a board on the clubhouse TV.")
    pad = round(W * 0.04)
    split = round(W * 0.34)
    return f"""
<div class="canvas" style="background:{INK}">
  <div style="position:absolute;left:0;top:0;width:{split}px;height:100%;background:{PAPER}"></div>
  <div style="position:absolute;left:{pad}px;right:{pad}px;top:50%;transform:translateY(-58%);display:flex;align-items:baseline;gap:{round(size*0.28)}px">
    <div class="display" style="font-size:{size}px;color:{INK};width:{split-pad}px">GOLF</div>
    <div class="display" style="font-size:{size}px;color:{PAPER};white-space:nowrap">SESSIONS</div>
  </div>
  <div class="body" style="position:absolute;left:{split+pad}px;right:{pad}px;bottom:{round(H*0.12)}px;font-size:{round(H*0.058)}px;color:{G300};max-width:60ch">{esc(tag)}</div>
  <div class="label" style="position:absolute;right:{pad}px;bottom:{round(H*0.045)}px;font-size:{round(H*0.05)}px;color:{G500}">golf-sessions.com</div>
</div>"""


def carousel(f, W, H):
    dark = bool(f.get("dark", False))
    bg, fg, muted, hair = (INK, PAPER, G300, HAIR_D) if dark else (PAPER, INK, G500, HAIR_L)
    pad = round(W * 0.07)
    eyebrow = f.get("eyebrow", "")
    head = f.get("headline", "")
    body = f.get("body", "")
    page = f.get("page", "")
    return f"""
<div class="canvas" style="background:{bg}">
  {f'<div class="eyebrow" style="position:absolute;left:{pad}px;top:{pad}px;font-size:{round(W*0.019)}px;color:{muted}">{esc(eyebrow)}</div>' if eyebrow else ''}
  <div style="position:absolute;left:{pad}px;right:{pad}px;top:50%;transform:translateY(-50%)">
    <div class="display" style="font-size:{f.get('headline_size', round(W*0.16))}px;color:{fg};text-wrap:balance">{esc(head)}</div>
    {f'<div class="body" style="margin-top:{round(W*0.04)}px;font-size:{round(W*0.03)}px;color:{muted if dark else G700};max-width:30ch">{esc(body)}</div>' if body else ''}
  </div>
  <div style="position:absolute;left:{pad}px;right:{pad}px;bottom:{pad+round(W*0.045)}px;height:1px;background:{hair}"></div>
  <div class="display" style="position:absolute;left:{pad}px;bottom:{pad-4}px;font-size:{round(W*0.03)}px;color:{fg}">GOLF SESSIONS</div>
  <div class="label" style="position:absolute;right:{pad}px;bottom:{pad}px;font-size:{round(W*0.02)}px;color:{muted}">{esc(page)}</div>
</div>"""


def photo(f, W, H):
    """Photograph fitted to the width at the top (at most 60% of the canvas), desaturated, blacks lifted,
    a scrim into ink, and eyebrow, headline and body on the ink below it. Type never sits over faces."""
    pad = round(W * 0.06)
    name = f.get("photo", "")
    src = name if name.startswith("http") else "file://" + os.path.join(PHOTOS, name)
    crop = {"top": "top", "bottom": "bottom"}.get(f.get("crop", "centre"), "center")
    ph = round(H * float(f.get("photo_height", 0.58)))
    eyebrow = f.get("eyebrow", "")
    head = f.get("headline", "")
    body = f.get("body", "")
    size = f.get("headline_size", round(W * 0.115))
    return f"""
<div class="canvas" style="background:{INK}">
  <div style="position:absolute;left:0;top:0;width:100%;height:{ph}px;overflow:hidden">
    <img src="{src}" style="width:100%;height:100%;object-fit:cover;object-position:{crop};filter:grayscale(1) contrast(0.92) brightness(1.04);display:block">
    <div style="position:absolute;left:0;right:0;bottom:0;height:45%;background:linear-gradient(to bottom, rgba(10,10,10,0) 0%, rgba(10,10,10,0.9) 100%)"></div>
  </div>
  <div style="position:absolute;left:{pad}px;right:{pad}px;top:{ph - round(H*0.04)}px">
    {f'<div class="eyebrow fit" style="font-size:{round(W*0.018)}px;line-height:1.5;color:{G300};margin-bottom:{round(W*0.025)}px">{esc(eyebrow)}</div>' if eyebrow else ''}
    <div class="display" style="font-size:{size}px;color:{PAPER};text-wrap:balance">{esc(head)}</div>
    {f'<div class="body" style="margin-top:{round(W*0.03)}px;font-size:{round(W*0.027)}px;color:{G300};max-width:34ch">{esc(body)}</div>' if body else ''}
  </div>
  <div style="position:absolute;left:{pad}px;right:{pad}px;bottom:{pad+round(W*0.045)}px;height:1px;background:{HAIR_D}"></div>
  <div class="display" style="position:absolute;left:{pad}px;bottom:{pad-4}px;font-size:{round(W*0.03)}px;color:{PAPER}">GOLF SESSIONS</div>
  <div class="label" style="position:absolute;right:{pad}px;bottom:{pad}px;font-size:{round(W*0.02)}px;color:{G500}">golf-sessions.com</div>
</div>"""


TEMPLATES = {"statement": statement, "numeral": numeral, "match": match, "testimonial": testimonial,
             "cover": cover, "carousel": carousel, "photo": photo}

FIT_GUARD = """() => {
  // shrink any display headline that overflows its box, and any .fit block that overflows or wraps past two lines
  for (const el of document.querySelectorAll('.display, .display-700')) {
    let size = parseFloat(getComputedStyle(el).fontSize);
    let guard = 40;
    while (el.scrollWidth > el.clientWidth + 1 && guard-- > 0) { size *= 0.96; el.style.fontSize = size + 'px'; }
  }
  for (const el of document.querySelectorAll('.fit')) {
    let size = parseFloat(getComputedStyle(el).fontSize);
    let guard = 40;
    const maxH = parseFloat(getComputedStyle(el).lineHeight) * 2 + 1;
    while ((el.scrollWidth > el.clientWidth + 1 || el.scrollHeight > maxH) && guard-- > 0) { size *= 0.96; el.style.fontSize = size + 'px'; }
  }
}"""


async def render_many(specs):
    from playwright.async_api import async_playwright
    os.makedirs(OUT, exist_ok=True)
    results = []
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for spec in specs:
            W, H = SIZES.get(spec.get("size", "portrait"), spec.get("size"))
            body = TEMPLATES[spec["template"]](spec.get("fields", {}), W, H)
            doc = f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{body}</body></html>"
            out = os.path.join(OUT, spec["id"] + ".png")
            tmp = os.path.join(OUT, f"_render_{spec['id']}.html")
            open(tmp, "w").write(doc)
            pg = await b.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
            await pg.goto("file://" + tmp)
            await pg.evaluate("document.fonts.ready")
            await pg.evaluate("() => Promise.all([...document.images].map(i => i.complete ? null : new Promise(r => { i.onload = r; i.onerror = r; })))")
            await pg.evaluate(FIT_GUARD)
            await pg.screenshot(path=out, type="png")
            await pg.close()
            os.remove(tmp)
            results.append(out)
            print(out)
        await b.close()
    return results


def load_specs(path):
    data = json.load(open(path))
    specs = data if isinstance(data, list) else [data]
    for s in specs:
        if "id" not in s:
            raise SystemExit(f"{path}: every spec needs an id")
    return specs


def spec_hash(spec):
    return hashlib.sha256(json.dumps(spec, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def render_all(force=False):
    """Render every spec under specs/ whose hash is not in out/manifest.json (or whose PNG is missing)."""
    manifest = json.load(open(MANIFEST)) if os.path.exists(MANIFEST) else {}
    todo = []
    for path in sorted(glob.glob(os.path.join(SPECS, "*.json"))):
        for spec in load_specs(path):
            h = spec_hash(spec)
            png = os.path.join(OUT, spec["id"] + ".png")
            if force or manifest.get(spec["id"]) != h or not os.path.exists(png):
                todo.append((spec, h))
    if not todo:
        print("nothing to render")
        return
    asyncio.run(render_many([s for s, _ in todo]))
    for spec, h in todo:
        manifest[spec["id"]] = h
    os.makedirs(OUT, exist_ok=True)
    json.dump(manifest, open(MANIFEST, "w"), indent=1, sort_keys=True)


DEMO = [
    {"id": "demo-statement", "template": "statement", "size": "portrait",
     "fields": {"eyebrow": "HOW TO RUN A DAY · 5 OF 6", "headline": "EVERY HOLE COUNTS.", "sub": "One point a hole. 18 points a match. Every card matters."}},
    {"id": "demo-numeral", "template": "numeral", "size": "portrait"},
    {"id": "demo-match", "template": "match", "size": "square", "fields": {"line": "Hartley & Boyd win 3 & 1"}},
    {"id": "demo-testimonial", "template": "testimonial", "size": "portrait",
     "fields": {"quote": "Twenty-eight players, three days, and not one argument about the score. The board at dinner did the talking.", "name": "JONATHAN HANDFORD", "role": "The Agency Challenge Cup 2026"}},
    {"id": "demo-cover", "template": "cover", "size": "linkedin_cover"},
    {"id": "demo-carousel-1", "template": "carousel", "size": "portrait",
     "fields": {"eyebrow": "FORMATS, EXPLAINED", "headline": "FOURSOMES.", "body": "One ball. Two players. Alternate shots.", "page": "1 / 5"}},
    {"id": "demo-carousel-2", "template": "carousel", "size": "portrait",
     "fields": {"dark": True, "eyebrow": "THE RULE", "headline": "TAKE TURNS.", "body": "One player drives the odd holes, the other the evens. Then you alternate every shot until the ball is holed.", "page": "2 / 5"}},
]

if __name__ == "__main__":
    os.chdir(HERE)
    args = sys.argv[1:]
    if "--fonts" in args:
        fetch_fonts()
    elif "--demo" in args:
        asyncio.run(render_many(DEMO))
    elif "--all" in args:
        render_all(force="--force" in args)
    else:
        specs = [s for a in args for s in load_specs(a)]
        asyncio.run(render_many(specs))
