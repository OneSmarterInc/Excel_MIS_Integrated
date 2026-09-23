"""PDF generation engine for MIS 3000 Excel Platform.

Generates beautiful, publication-quality PDF documents for:
- Individual Modules
- Individual Chapters (including all nested modules, demonstrations, and resources)
- Full Course Books
"""
from __future__ import annotations

import io
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def _styles():
    base = getSampleStyleSheet()
    header_title = ParagraphStyle(
        "PDFHeaderTitle",
        parent=base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0f392b"),
        spaceAfter=4,
    )
    header_subtitle = ParagraphStyle(
        "PDFHeaderSubTitle",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#4a6358"),
        spaceAfter=12,
    )
    section_heading = ParagraphStyle(
        "PDFSectionHeading",
        parent=base["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#0f392b"),
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True,
    )
    sub_heading = ParagraphStyle(
        "PDFSubHeading",
        parent=base["Heading3"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#1e5643"),
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True,
    )
    body = ParagraphStyle(
        "PDFBody",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor("#1b2e25"),
        spaceAfter=6,
    )
    bullet = ParagraphStyle(
        "PDFBullet",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor("#1b2e25"),
        leftIndent=14,
        firstLineIndent=-10,
        spaceAfter=3,
    )
    quote_text = ParagraphStyle(
        "PDFQuote",
        parent=base["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#334d40"),
    )
    code_text = ParagraphStyle(
        "PDFCode",
        parent=base["Normal"],
        fontName="Courier",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#0d47a1"),
    )
    step_num = ParagraphStyle(
        "PDFStepNum",
        parent=base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=12,
        textColor=colors.HexColor("#0f392b"),
        alignment=1,
    )
    return {
        "header_title": header_title,
        "header_subtitle": header_subtitle,
        "section_heading": section_heading,
        "sub_heading": sub_heading,
        "body": body,
        "bullet": bullet,
        "quote": quote_text,
        "code": code_text,
        "step_num": step_num,
    }


def _safe(text: str) -> str:
    """Escape XML entities for reportlab Paragraphs."""
    return (
        str(text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _render_explanation(story, text: str, s: dict):
    if not text:
        return
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            story.append(Spacer(1, 4))
            continue
        if line in (
            "In plain words",
            "The main ideas",
            "Excel terms used here",
            "Try it yourself",
            "Check yourself",
            "What this is about",
            "The main ideas, one at a time",
        ):
            story.append(Paragraph(_safe(line), s["sub_heading"]))
        elif line.startswith("- ") or line.startswith("• "):
            story.append(Paragraph(f"• {_safe(line[2:])}", s["bullet"]))
        elif line[0].isdigit() and (line[1:3] in (". ", ") ") or line[2:4] in (". ", ") ")):
            story.append(Paragraph(_safe(line), s["bullet"]))
        else:
            story.append(Paragraph(_safe(line), s["body"]))


def _render_book_text(story, text: str, s: dict):
    if not text:
        return
    box_data = [[Paragraph(_safe(text[:8000]), s["quote"])]]
    table = Table(box_data, colWidths=[500])
    table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f4f7f5")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#d5ded8")),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ])
    )
    story.append(table)
    story.append(Spacer(1, 8))


def _render_demonstrations(story, demonstrations, s: dict):
    if not demonstrations:
        return
    story.append(Paragraph("Walkthroughs &amp; Demonstrations", s["section_heading"]))
    for demo in demonstrations:
        story.append(Paragraph(f"<b>{_safe(demo.title)}</b>", s["sub_heading"]))
        if demo.summary:
            story.append(Paragraph(_safe(demo.summary), s["body"]))
        steps = demo.steps or []
        for step in steps:
            order = step.get("order", 1)
            title = step.get("title", "")
            instruction = step.get("instruction", "")
            cell = step.get("cell", "")
            formula = step.get("formula", "")

            detail = f"<b>{_safe(title)}:</b> {_safe(instruction)}" if title else _safe(instruction)
            if cell or formula:
                hints = []
                if cell:
                    hints.append(f"Cell: <code>{_safe(cell)}</code>")
                if formula:
                    hints.append(f"Formula: <code>{_safe(formula)}</code>")
                detail += f"<br/><font color='#0d47a1'>{' | '.join(hints)}</font>"

            row = [
                Paragraph(f"<b>{order}</b>", s["step_num"]),
                Paragraph(detail, s["body"]),
            ]
            t = Table([row], colWidths=[30, 470])
            t.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#e7f1ec")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ])
            )
            story.append(t)
            story.append(Spacer(1, 3))
        story.append(Spacer(1, 6))


def _render_resources(story, resources, s: dict):
    if not resources:
        return
    story.append(Paragraph("Instructor References", s["section_heading"]))
    for res in resources:
        desc = f"• <b>{_safe(res.title)}</b>"
        if res.caption:
            desc += f" — {_safe(res.caption)}"
        if res.url:
            desc += f" ({_safe(res.url)})"
        story.append(Paragraph(desc, s["bullet"]))
    story.append(Spacer(1, 6))


def generate_module_pdf(module) -> bytes:
    """Produce a PDF for a single module."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=40,
    )
    s = _styles()
    story = []

    chapter = module.chapter
    course = chapter.book.course

    # Header
    story.append(
        Paragraph(
            f"Module {chapter.number}.{module.number}: {_safe(module.title)}",
            s["header_title"],
        )
    )
    story.append(
        Paragraph(
            f"{_safe(course.code)} — {_safe(course.name)} &nbsp;|&nbsp; Chapter {chapter.number}: {_safe(chapter.title)}",
            s["header_subtitle"],
        )
    )
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0f392b"), spaceAfter=10))

    # Explanation
    if module.explanation:
        story.append(Paragraph("Easy Explanation", s["section_heading"]))
        _render_explanation(story, module.explanation, s)
        story.append(Spacer(1, 8))

    # From the book
    if module.raw_text:
        story.append(Paragraph("From the Book", s["section_heading"]))
        _render_book_text(story, module.raw_text, s)

    # Demonstrations & Resources
    _render_demonstrations(story, list(module.demonstrations.all()), s)
    _render_resources(story, list(module.resources.all()), s)

    doc.build(story)
    return buffer.getvalue()


def generate_chapter_pdf(chapter) -> bytes:
    """Produce a PDF for an entire chapter including its modules."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=40,
    )
    s = _styles()
    story = []

    course = chapter.book.course

    # Header
    story.append(
        Paragraph(
            f"Chapter {chapter.number}: {_safe(chapter.title)}",
            s["header_title"],
        )
    )
    story.append(
        Paragraph(
            f"{_safe(course.code)} — {_safe(course.name)} &nbsp;|&nbsp; Instructor: {_safe(course.faculty.name)}",
            s["header_subtitle"],
        )
    )
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0f392b"), spaceAfter=12))

    # Chapter Overview
    if chapter.explanation:
        story.append(Paragraph("Chapter Overview", s["section_heading"]))
        _render_explanation(story, chapter.explanation, s)
        story.append(Spacer(1, 8))

    if chapter.raw_text:
        story.append(Paragraph("From the Book", s["section_heading"]))
        _render_book_text(story, chapter.raw_text, s)

    _render_demonstrations(story, list(chapter.demonstrations.all()), s)
    _render_resources(story, list(chapter.resources.all()), s)

    # Modules
    modules = list(chapter.modules.order_by("number", "id"))
    if modules:
        story.append(Spacer(1, 10))
        story.append(Paragraph(f"Modules ({len(modules)})", s["section_heading"]))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd7d0"), spaceAfter=8))

        for module in modules:
            story.append(
                Paragraph(
                    f"Module {chapter.number}.{module.number}: {_safe(module.title)}",
                    s["sub_heading"],
                )
            )
            if module.explanation:
                _render_explanation(story, module.explanation, s)
                story.append(Spacer(1, 4))
            if module.raw_text:
                _render_book_text(story, module.raw_text, s)
            _render_demonstrations(story, list(module.demonstrations.all()), s)
            _render_resources(story, list(module.resources.all()), s)
            story.append(Spacer(1, 10))

    doc.build(story)
    return buffer.getvalue()


def generate_book_pdf(book) -> bytes:
    """Produce a compiled textbook PDF for the entire book."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=40,
    )
    s = _styles()
    story = []
    course = book.course

    # Cover Header
    story.append(Paragraph(_safe(book.title), s["header_title"]))
    story.append(
        Paragraph(
            f"{_safe(course.code)} — {_safe(course.name)} &nbsp;|&nbsp; Course Book<br/>"
            f"Instructor: {_safe(course.faculty.name)} &nbsp;|&nbsp; Generated: {timezone.now().strftime('%B %d, %Y')}",
            s["header_subtitle"],
        )
    )
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#0f392b"), spaceAfter=14))

    chapters = list(book.chapters.order_by("number", "id"))
    story.append(Paragraph(f"Table of Contents ({len(chapters)} Chapters)", s["section_heading"]))
    for ch in chapters:
        story.append(Paragraph(f"• <b>Chapter {ch.number}:</b> {_safe(ch.title)} ({ch.modules.count()} modules)", s["bullet"]))
    story.append(Spacer(1, 16))

    for ch in chapters:
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0f392b"), spaceAfter=10))
        story.append(Paragraph(f"Chapter {ch.number}: {_safe(ch.title)}", s["header_title"]))
        if ch.explanation:
            _render_explanation(story, ch.explanation, s)
            story.append(Spacer(1, 6))
        if ch.raw_text:
            _render_book_text(story, ch.raw_text, s)
        _render_demonstrations(story, list(ch.demonstrations.all()), s)
        _render_resources(story, list(ch.resources.all()), s)

        for mod in ch.modules.order_by("number", "id"):
            story.append(Paragraph(f"Module {ch.number}.{mod.number}: {_safe(mod.title)}", s["sub_heading"]))
            if mod.explanation:
                _render_explanation(story, mod.explanation, s)
            if mod.raw_text:
                _render_book_text(story, mod.raw_text, s)
            _render_demonstrations(story, list(mod.demonstrations.all()), s)
            _render_resources(story, list(mod.resources.all()), s)
            story.append(Spacer(1, 8))
        story.append(Spacer(1, 14))

    doc.build(story)
    return buffer.getvalue()
