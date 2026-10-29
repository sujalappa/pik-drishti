"""PDF report for a drought or crop-damage assessment."""

from __future__ import annotations

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

GREEN = colors.HexColor("#1f5f45")
LINE = colors.HexColor("#d9d3c3")


def _styles():
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle("H1x", parent=ss["Title"], fontSize=17, textColor=GREEN, alignment=0, spaceAfter=4))
    ss.add(ParagraphStyle("H2x", parent=ss["Heading2"], fontSize=12, textColor=GREEN, spaceBefore=10, spaceAfter=4))
    ss.add(ParagraphStyle("Cell", parent=ss["BodyText"], fontSize=7.5, leading=9.5))
    ss.add(ParagraphStyle("Small", parent=ss["BodyText"], fontSize=8, leading=10, textColor=colors.HexColor("#555")))
    return ss


def _table(rows, widths, header_bg=GREEN):
    t = Table(rows, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), header_bg), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5), ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f6f3ec")]),
    ]))
    return t


def build(path, title: str, subtitle: str, facts: list[tuple[str, str]], method: dict, sources: list[dict],
          columns: list[tuple[str, str]], rows: list[dict], note: str) -> None:
    ss = _styles()
    doc = SimpleDocTemplate(str(path), pagesize=landscape(A4), leftMargin=14 * mm, rightMargin=14 * mm,
                            topMargin=12 * mm, bottomMargin=12 * mm, title=title, author="Pik-drishti AI")
    story = [Paragraph(title, ss["H1x"]), Paragraph(subtitle, ss["Small"]), Spacer(1, 6)]
    story.append(_table([["Item", "Value"]] + [[k, Paragraph(str(v), ss["Cell"])] for k, v in facts],
                        [70 * mm, 190 * mm]))
    story.append(Paragraph("Method", ss["H2x"]))
    story += [Paragraph(f"<b>{k.replace('_', ' ').capitalize()}:</b> {v}", ss["Small"]) for k, v in method.items()]
    story.append(Paragraph("Results", ss["H2x"]))
    body = [[label for _, label in columns]] + [
        [Paragraph("" if r.get(k) is None else str(r.get(k)), ss["Cell"]) for k, _ in columns] for r in rows]
    width = (269 * mm) / len(columns)
    story.append(_table(body, [width] * len(columns)))
    story.append(Paragraph("Data sources", ss["H2x"]))
    story.append(_table([["Dataset", "Provider", "Used for", "Licence / citation"]] + [
        [Paragraph(s["dataset"], ss["Cell"]), Paragraph(s.get("provider", ""), ss["Cell"]),
         Paragraph(s.get("used_for", ""), ss["Cell"]),
         Paragraph(f"{s.get('license', '')}. {s.get('citation', '')}", ss["Cell"])] for s in sources],
        [70 * mm, 55 * mm, 80 * mm, 64 * mm]))
    story += [Spacer(1, 6), Paragraph(note, ss["Small"])]
    doc.build(story)
