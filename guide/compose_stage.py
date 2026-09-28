"""
compose_stage.py - Python half of the guide generator (no Blender needed; Pillow + reportlab).
Reads <build>/manifest.json + raw renders, draws callouts, and writes the PDF, the markdown and the step images.
"""
import json, os
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.fonts import addMapping
from reportlab.platypus import Paragraph, Frame, Table, TableStyle, Spacer, KeepInFrame
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

import guide_text as T
import guide_style as S

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "fonts")

def _font(bold=False, size=30):
    """DejaVu from guide/fonts, else the system copy, else Pillow's default."""
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    for d in (FONTS, "/usr/share/fonts/truetype/dejavu", "/Library/Fonts", os.path.expanduser("~/Library/Fonts")):
        p = os.path.join(d, name)
        if os.path.exists(p): return p if size is None else ImageFont.truetype(p, size)
    return None if size is None else ImageFont.load_default()

# ------------------------------------------------------------------ callouts on the render
def overlay(raw_png, callouts, out_png):
    im = Image.open(raw_png).convert("RGBA")
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255)); bg.alpha_composite(im)
    d = ImageDraw.Draw(bg); font = _font(True, 30)
    W, H = bg.size; placed = []
    def hits(b): return any(not (b[2] + 8 < p[0] or b[0] > p[2] + 8 or b[3] + 8 < p[1] or b[1] > p[3] + 8) for p in placed)
    for c in callouts:
        (ax, ay), text, (dx, dy) = c["px"], c["text"], c["offset"]
        tw, th = d.textbbox((0, 0), text, font=font)[2:]; pad = 10
        lx, ly = ax + dx, ay + dy; step = 1 if dy >= 0 else -1
        for _ in range(60):
            lx = min(max(lx, tw/2 + pad + 6), W - tw/2 - pad - 6)
            ly = min(max(ly, th/2 + pad + 6), H - th/2 - pad - 6)
            box = [lx - tw/2 - pad, ly - th/2 - pad, lx + tw/2 + pad, ly + th/2 + pad]
            if not hits(box): break
            ly += step * 22
            if ly > H - th or ly < th: step = -step
        placed.append(box)
        ex, ey = min(max(ax, box[0]), box[2]), min(max(ay, box[1]), box[3])
        d.line([(ax, ay), (ex, ey)], fill=(30, 30, 30), width=3)
        d.ellipse([ax - 7, ay - 7, ax + 7, ay + 7], fill=S.COL["arrow"], outline=(30, 30, 30), width=2)
        d.rounded_rectangle(box, radius=10, fill=(255, 255, 255), outline=(30, 30, 30), width=3)
        d.text((lx - tw/2, ly - th/2 - 2), text, font=font, fill=(20, 20, 20))
    bg.convert("RGB").save(out_png)

# ------------------------------------------------------------------ PDF
def _styles():
    reg, bold = _font(False, None), _font(True, None)
    if reg and bold:
        pdfmetrics.registerFont(TTFont("DV", reg)); pdfmetrics.registerFont(TTFont("DVB", bold))
        addMapping("DV", 0, 0, "DV"); addMapping("DV", 1, 0, "DVB"); f, fb = "DV", "DVB"
    else:
        f, fb = "Helvetica", "Helvetica-Bold"
    ink, mute = colors.HexColor(S.INK), colors.HexColor(S.MUTE)
    st = dict(
        h=ParagraphStyle("h", fontName=fb, fontSize=8.5, textColor=mute, leading=11, spaceAfter=4),
        b=ParagraphStyle("b", fontName=f, fontSize=9.6, textColor=ink, leading=12.8),
    )
    st["n"] = ParagraphStyle("n", parent=st["b"], leftIndent=16, firstLineIndent=-16, spaceAfter=4.5)
    st["s"] = ParagraphStyle("s", parent=st["b"], fontSize=9.0, leading=11.8)
    return st, f, fb

W, H = letter; M = 0.5 * inch

def _jpeg(png, build_dir):
    """PDF copy of an image as a high-quality JPEG (keeps the PDF ~1/4 the size; the PNGs stay for markdown)."""
    jpg = os.path.join(build_dir, "pdf_" + os.path.splitext(os.path.basename(png))[0] + ".jpg")
    Image.open(png).convert("RGB").save(jpg, quality=90, optimize=True, subsampling=0)
    return jpg

def _rgb(c): return colors.Color(c[0]/255, c[1]/255, c[2]/255)

def _box(c, st, x, y, w, h, label, body, fill, edge):
    c.setFillColor(colors.HexColor(fill)); c.setStrokeColor(colors.HexColor(edge)); c.setLineWidth(1)
    c.roundRect(x, y, w, h, 5, stroke=1, fill=1)
    c.setFillColor(colors.HexColor(edge)); c.rect(x, y, 0.06*inch, h, stroke=0, fill=1)
    Frame(x + 0.16*inch, y + 0.06*inch, w - 0.26*inch, h - 0.12*inch, 0, 0, 0, 0).addFromList(
        [KeepInFrame(w - 0.26*inch, h - 0.12*inch,
                     [Paragraph(label, ParagraphStyle("x", parent=st["h"], textColor=colors.HexColor(edge))), Paragraph(body, st["s"])],
                     mode="shrink")], c)

def _footer(c, f, left, right):
    c.setFont(f, 7.5); c.setFillColor(colors.HexColor(S.MUTE))
    c.drawString(M, 0.28*inch, left); c.drawRightString(W - M, 0.28*inch, right)

def cover(c, st, f, fb, hero_png, meta):
    c.setFillColor(colors.HexColor(S.INK)); c.rect(0, H - 2.1*inch, W, 2.1*inch, stroke=0, fill=1)
    c.setFillColor(colors.HexColor(S.ACCENT)); c.rect(0, H - 2.1*inch, 0.12*inch, 2.1*inch, stroke=0, fill=1)
    c.setFillColor(colors.HexColor("#aeb6c0")); c.setFont(fb, 10); c.drawString(M, H - 0.75*inch, "ASSEMBLY GUIDE")
    c.setFillColor(colors.white); c.setFont(fb, 30); c.drawString(M, H - 1.25*inch, "NEMA17 Cycloidal Drive")
    c.setFillColor(colors.HexColor("#d5dae0")); c.setFont(f, 12)
    c.drawString(M, H - 1.62*inch, f"{len(T.STEPS)} steps  ·  {T.RATIO}:1  ·  3D-printed, bearing-supported, two-disc")
    im = Image.open(hero_png); iw = W - 2*M; ih = iw * im.height / im.width
    top = H - 2.1*inch - 0.25*inch
    c.drawImage(hero_png, M, top - ih, iw, ih)
    rows = [[Paragraph(f"<b>{k}</b>", st["s"]), Paragraph(v, st["s"])] for k, v in T.SPECS]
    tab = Table(rows, colWidths=[1.1*inch, W - 2*M - 1.1*inch])
    tab.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -2), 0.4, colors.HexColor("#d9dde2")),
                             ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                             ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    tw, th = tab.wrap(W - 2*M, 3*inch); tab.drawOn(c, M, top - ih - 0.25*inch - th)
    c.setFont(f, 8); c.setFillColor(colors.HexColor(S.MUTE))
    c.drawString(M, M + 0.1*inch, f"Generated {meta['date']} from geometry/params.py{('  ·  commit ' + meta['commit']) if meta.get('commit') else ''}"
                                  f"  ·  Blender {meta.get('blender', '?')}")
    c.showPage()

def page(c, st, f, fb, num, step, img, checks, meta):
    t = T.resolved(step)
    c.setFillColor(colors.HexColor(S.INK)); c.rect(0, H - 0.95*inch, W, 0.95*inch, stroke=0, fill=1)
    c.setFillColor(colors.HexColor(S.ACCENT)); c.rect(0, H - 0.95*inch, 0.12*inch, 0.95*inch, stroke=0, fill=1)
    c.setFillColor(colors.HexColor("#aeb6c0")); c.setFont(fb, 9); c.drawString(M, H - 0.38*inch, f"STEP {num} OF {len(T.STEPS)}")
    c.setFillColor(colors.white); c.setFont(fb, 21); c.drawString(M, H - 0.72*inch, t["title"])
    iw = W - 2*M; ih = iw * 1150/1800; top = H - 0.95*inch - 0.18*inch
    c.drawImage(img, M, top - ih, iw, ih)
    c.setStrokeColor(colors.HexColor("#d9dde2")); c.setLineWidth(0.8); c.rect(M, top - ih, iw, ih, stroke=1, fill=0)
    y_top = top - ih - 0.2*inch
    lw = 2.45*inch; rw = W - 2*M - lw - 0.3*inch
    left = [Paragraph("YOU NEED" if t["need"] else "SPECS", st["h"])]
    if t["need"]:
        rows = [[Paragraph(f"<b>{q}×</b>" if q else "", st["s"]), "", Paragraph(txt, st["s"])] for q, txt, _ in t["need"]]
        tab = Table(rows, colWidths=[0.36*inch, 0.14*inch, lw - 0.5*inch])
        ts = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 2),
              ("TOPPADDING", (0, 0), (-1, -1), 1.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5)]
        ts += [("BACKGROUND", (1, i), (1, i), _rgb(S.base_colour(k))) for i, (_, _, k) in enumerate(t["need"])]
        tab.setStyle(TableStyle(ts)); left.append(tab)
    else:
        left += [Paragraph(s, st["s"]) for s in (f"<b>{k}:</b> {v}" for k, v in T.SPECS[:3])]
    right = [Paragraph("DO THIS", st["h"])] + [Paragraph(f"<b>{i}.</b>  {s}", st["n"]) for i, s in enumerate(t["do"], 1)]
    if t.get("tools"): right += [Spacer(1, 6), Paragraph("TOOLS", st["h"]), Paragraph(t["tools"], st["s"])]
    bad = [x for x in checks if not x["ok"]]
    reserve = 1.35*inch + (0.75*inch if bad else 0)
    fh = y_top - (M + reserve)
    Frame(M, M + reserve, lw, fh, 0, 0, 0, 0).addFromList([KeepInFrame(lw, fh, left, mode="shrink")], c)
    Frame(M + lw + 0.3*inch, M + reserve, rw, fh, 0, 0, 0, 0).addFromList([KeepInFrame(rw, fh, right, mode="shrink")], c)
    bw = (W - 2*M - 0.2*inch) / 2; by = M + 0.22*inch
    _box(c, st, M, by, bw, 1.05*inch, "CHECK", t["check"], S.CHECK_FILL, S.CHECK_EDGE)
    _box(c, st, M + bw + 0.2*inch, by, bw, 1.05*inch, "TIP", t["tip"], S.TIP_FILL, S.TIP_EDGE)
    if bad:
        msg = "; ".join(f"{x['part']} collides with {x['hits']} ({x['overlap_mm3']} mm³, {x['at_travel_mm']} mm before seating)" for x in bad)
        _box(c, st, M, by + 1.05*inch + 0.12*inch, W - 2*M, 0.6*inch, "ASSEMBLY PATH BLOCKED: fix the design before building",
             msg, S.BLOCK_FILL, S.BLOCK_EDGE)
    _footer(c, f, f"NEMA17 cycloidal drive  ·  assembly guide  ·  {meta['date']}", f"{num} / {len(T.STEPS)}")
    c.showPage()

# ------------------------------------------------------------------ markdown
def markdown(md_path, img_rel, meta, results):
    L = [f"# NEMA17 Cycloidal Drive: Assembly Guide", "",
         f"Generated {meta['date']} from `geometry/params.py`" + (f" (commit `{meta['commit']}`)" if meta.get("commit") else "")
         + f". {len(T.STEPS)} steps. The PDF version has the same content.", ""]
    L += ["| | |", "|---|---|"] + [f"| **{k}** | {v} |" for k, v in T.SPECS] + [""]
    for num, step in enumerate(T.STEPS, 1):
        if step["key"] not in img_rel: continue
        t = T.resolved(step)
        L += [f"## Step {num}: {t['title']}", "", f"![Step {num}]({img_rel[step['key']]})", ""]
        bad = [x for x in results.get(step["key"], []) if not x["ok"]]
        if bad:
            L += ["> **ASSEMBLY PATH BLOCKED.** " + "; ".join(f"{x['part']} collides with {x['hits']} ({x['overlap_mm3']} mm³)" for x in bad), ""]
        if t["need"]:
            L += ["**You need:** " + ", ".join(f"{q}× {txt}" if q else txt for q, txt, _ in t["need"]), ""]
        if t.get("tools"): L += [f"**Tools:** {t['tools']}", ""]
        L += [f"{i}. {s}" for i, s in enumerate(t["do"], 1)] + [""]
        L += [f"**Check:** {t['check']}", "", f"**Tip:** {t['tip']}", ""]
    with open(md_path, "w") as f: f.write("\n".join(L))

# ------------------------------------------------------------------ entry
def compose(build_dir, out_dir, stem, meta, cover_page=True):
    man = json.load(open(os.path.join(build_dir, "manifest.json")))
    meta = dict(meta, blender=man.get("blender"))
    img_dir = os.path.join(out_dir, "img"); os.makedirs(img_dir, exist_ok=True)
    st, f, fb = _styles()
    pdf_path = os.path.join(out_dir, stem + ".pdf"); md_path = os.path.join(out_dir, stem + ".md")
    c = canvas.Canvas(pdf_path, pagesize=letter)
    c.setTitle("NEMA17 Cycloidal Drive: Assembly Guide"); c.setSubject(f"Generated {meta['date']}")
    img_rel, results = {}, {}
    if cover_page and "done" in man["steps"] and not meta.get("only"):
        hero = os.path.join(build_dir, man["steps"]["done"]["raw"])
        hero_flat = os.path.join(build_dir, "hero.png")
        im = Image.open(hero).convert("RGBA"); bg = Image.new("RGBA", im.size, (255, 255, 255, 255)); bg.alpha_composite(im)
        bg.convert("RGB").save(hero_flat)
        cover(c, st, f, fb, _jpeg(hero_flat, build_dir), meta)
    only = meta.get("only")
    for num, step in enumerate(T.STEPS, 1):
        k = step["key"]
        if k not in man["steps"] or (only and k not in only): continue
        s = man["steps"][k]
        out_png = os.path.join(img_dir, f"step-{num:02d}-{k}.png")
        overlay(os.path.join(build_dir, s["raw"]), s["callouts"], out_png)
        img_rel[k] = os.path.relpath(out_png, out_dir); results[k] = s["path_checks"]
        page(c, st, f, fb, num, step, _jpeg(out_png, build_dir), s["path_checks"], meta)
    c.save()
    markdown(md_path, img_rel, meta, results)
    blocked = {k: [x for x in v if not x["ok"]] for k, v in results.items()}
    return pdf_path, md_path, {k: v for k, v in blocked.items() if v}
