"""Fill slide 2 (The Problem) of the Seva Innovation Challenge 2026 template.

Run:  python build_slide2.py   (needs python-pptx)
Reads template_original.pptx and writes Pik-drishti_AI_Seva_2026.pptx next to it.
"""

import copy
from pathlib import Path

from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

HERE = Path(__file__).resolve().parent
BUMP = 1  # pt added to every text size in this deck, for readability
SRC, OUT = HERE / "template_original.pptx", HERE / "Pik-drishti_AI_Seva_2026.pptx"

INK = RGBColor(0x1F, 0x29, 0x37)
NAVY = RGBColor(0x1B, 0x2A, 0x5C)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
MUTED = RGBColor(0x6B, 0x72, 0x80)


def fill(shape, paras, color=INK, size=10, bullets=False, space_after=3):
    """paras: list of paragraphs; each is a str or a list of (text, bold) runs."""
    tf = shape.text_frame
    first = tf.paragraphs[0]
    proto_ppr = copy.deepcopy(first._p.pPr) if first._p.pPr is not None else None
    proto_rpr = first.runs[0]._r.rPr if first.runs else None
    for p in list(tf.paragraphs)[1:]:
        p._p.getparent().remove(p._p)
    for r in list(first.runs):
        r._r.getparent().remove(r._r)
    for i, para in enumerate(paras):
        p = first if i == 0 else tf.add_paragraph()
        if i and proto_ppr is not None:
            p._p.insert(0, copy.deepcopy(proto_ppr))
        runs = [(para, False)] if isinstance(para, str) else para
        for text, bold in runs:
            r = p.add_run()
            if proto_rpr is not None:
                r._r.insert(0, copy.deepcopy(proto_rpr))
            r.text = text
            f = r.font
            f.italic = False
            f.bold = bold
            f.size = Pt(size + BUMP)
            f.color.rgb = color
        p.space_after = Pt(space_after)
        if bullets:
            ppr = p._p.get_or_add_pPr()
            ppr.set("marL", str(Inches(0.14)))
            ppr.set("indent", str(-Inches(0.14)))
            for tag in ("a:buNone", "a:buChar", "a:buAutoNum"):
                for el in ppr.findall(qn(tag)):
                    ppr.remove(el)
            bu = etree.SubElement(ppr, qn("a:buChar"))
            bu.set("char", "•")


prs = Presentation(SRC)
s = prs.slides[1]
by_name = {sh.name: sh for sh in s.shapes}

fill(by_name["Text 7"], [[
    ("After floods or unseasonal rain, every damaged farm is inspected ", False),
    ("by hand", True), (" (panchanama) before relief or insurance is paid. With lakhs of farms hit at once "
                        "this takes ", False), ("weeks", True),
    (", and farmers must leave the ruined crop standing as proof.", False)]])

fill(by_name["Text 10"], [[
    ("Small and marginal farmers across Maharashtra. In 2025, ", False), ("29 of 36 districts", True),
    (" and ", False), ("253 talukas", True), (" were hit, Marathwada the worst. ", False),
    ("Also the talathis and agriculture assistants who must survey every field, and the officials who "
     "approve relief.", False)]])

fill(by_name["Text 13"], [
    [("60–68 lakh ha", True), (" crops damaged, Jun–Sep 2025; ", False), ("₹31,628 cr", True),
     (" relief (State Govt)", False)],
    [("Banana storms, 2026: survey ordered ", False), ("~3 weeks", True),
     (" late, 1.5–2 months to reach Solapur", False)],
    [("The State itself proposed ", False), ("using satellites", True), (" to assess damage (PTI)", False)],
], size=9.5, bullets=True)

fill(by_name["Text 16"], [
    [("Panchanama", True), (" is manual, field by field, and depends on the surveyor", False)],
    [("Drone surveys", True), (" help but go district by district and cost more", False)],
    [("YES-TECH / CROPIC", True), (" estimate season-end yield for insurance, not each farm's damage right "
                                   "after an event", False)],
], size=9.5, bullets=True)

fill(by_name["Text 18"], [[("60 lakh+ ha", True)]], color=RGBColor(0xF2, 0x8C, 0x28), size=24)
fill(by_name["Text 19"], ["of crops damaged by rain and floods in Maharashtra, June–Sept 2025"], color=WHITE,
     size=10.5)
fill(by_name["Text 21"], ["Until the survey is done, relief, crop loans and re-sowing all wait, and ₹31,628 crore "
                          "of aid rests on manual field checks."], color=RGBColor(0xC9, 0xD2, 0xEC), size=10)

src = s.shapes.add_textbox(Inches(0.5), Inches(5.1), Inches(5.4), Inches(0.38))
src.name = "Sources"
tf = src.text_frame
tf.word_wrap = True
for side in ("left", "right", "top", "bottom"):
    setattr(tf, f"margin_{side}", 0)
r = tf.paragraphs[0].add_run()
r.text = ("Sources: Govt of Maharashtra relief package, 7 Oct 2025 (Scroll, The Week); Rural Voice, 27 Jun 2026; "
          "PTI via Outlook India, Jan 2024; MoA&FW YES-TECH (2023).")
r.font.size = Pt(7)
r.font.name = "Nirmala UI"
r.font.color.rgb = MUTED

prs.save(OUT)
print("saved", OUT)
