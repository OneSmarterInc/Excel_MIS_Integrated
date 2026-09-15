"""Pull readable text out of an uploaded book and split it into chapters and modules.

The uploaded file can be PDF, Word, PowerPoint or plain text. Every reader returns
the same shape, a list of blocks, so the chapter and module splitters never need to
know which format the text came from. Nothing here calls a network service, so the
extraction works the same on a laptop with no internet connection.
"""
from __future__ import annotations

import re
import unicodedata

WORD_NUMBERS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20,
}
ROMAN = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7, "viii": 8,
         "ix": 9, "x": 10, "xi": 11, "xii": 12, "xiii": 13, "xiv": 14, "xv": 15}

CHAPTER_RE = re.compile(
    r"^\s*(?:chapter|chap\.?|unit|part)\s+"
    r"(?P<num>\d{1,2}|[ivxlcdm]{1,5}|one|two|three|four|five|six|seven|eight|nine|ten|"
    r"eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty)"
    r"\b[\s:.\u2013\u2014-]*(?P<title>.{0,140})$",
    re.IGNORECASE,
)
MODULE_RE = re.compile(
    r"^\s*(?:module|section|lesson|topic|activity)\s+"
    r"(?P<num>\d{1,2}(?:\.\d{1,2})?)\b[\s:.\u2013\u2014-]*(?P<title>.{0,140})$",
    re.IGNORECASE,
)
NUMBERED_RE = re.compile(r"^\s*(?P<num>\d{1,2}\.\d{1,2})[\s:.\u2013\u2014-]+(?P<title>[A-Za-z].{2,140})$")
TOC_RE = re.compile(r"(\.{3,}\s*\d{1,4}\s*$)|(\s{2,}\d{1,4}\s*$)")
EXCEL_TERMS = re.compile(
    r"\b(SUM|AVERAGE|COUNT|COUNTA|COUNTIF|SUMIF|MIN|MAX|IF|VLOOKUP|XLOOKUP|INDEX|MATCH|"
    r"ROUND|TODAY|CONCAT|TEXT|PMT|NPV|IRR|AUTOSUM|AUTOFILL|PIVOT ?TABLE|ABSOLUTE REFERENCE|"
    r"RELATIVE REFERENCE|CONDITIONAL FORMATTING|CHART|FILTER|SORT|FREEZE PANES)\b",
    re.IGNORECASE,
)


def clean(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    text = text.replace("\u00a0", " ").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


# --------------------------------------------------------------------------- readers

def read_pdf(path: str) -> list[dict]:
    from pypdf import PdfReader

    blocks: list[dict] = []
    reader = PdfReader(path)
    for page_no, page in enumerate(reader.pages, start=1):
        try:
            page_text = page.extract_text() or ""
        except Exception:
            page_text = ""
        for line in page_text.split("\n"):
            line = clean(line)
            if line:
                blocks.append({"text": line, "style": "body", "page": page_no})
    return blocks


def read_docx(path: str) -> list[dict]:
    import docx

    blocks: list[dict] = []
    document = docx.Document(path)
    for paragraph in document.paragraphs:
        text = clean(paragraph.text)
        if not text:
            continue
        style = (paragraph.style.name or "").lower() if paragraph.style else ""
        if style.startswith("heading 1") or style == "title":
            level = "h1"
        elif style.startswith("heading 2") or style.startswith("heading 3"):
            level = "h2"
        else:
            level = "body"
        blocks.append({"text": text, "style": level, "page": 0})
    for table in document.tables:
        for row in table.rows:
            cells = [clean(cell.text) for cell in row.cells]
            joined = " | ".join(c for c in cells if c)
            if joined:
                blocks.append({"text": joined, "style": "body", "page": 0})
    return blocks


def read_pptx(path: str) -> list[dict]:
    from pptx import Presentation

    blocks: list[dict] = []
    presentation = Presentation(path)
    for index, slide in enumerate(presentation.slides, start=1):
        title_shape = slide.shapes.title
        title_id = title_shape.shape_id if title_shape is not None else None
        title = clean(title_shape.text) if title_shape is not None else ""
        if title:
            blocks.append({"text": title, "style": "h2", "page": index})
        for shape in slide.shapes:
            if shape.shape_id == title_id or not shape.has_text_frame:
                continue
            for paragraph in shape.text_frame.paragraphs:
                text = clean("".join(run.text for run in paragraph.runs))
                if text:
                    blocks.append({"text": text, "style": "body", "page": index})
    return blocks


def read_txt(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8", errors="ignore") as handle:
        raw = handle.read()
    blocks = []
    for line in raw.split("\n"):
        line = clean(line)
        if line:
            blocks.append({"text": line, "style": "body", "page": 0})
    return blocks


READERS = {"pdf": read_pdf, "docx": read_docx, "pptx": read_pptx, "txt": read_txt}


def detect_kind(filename: str) -> str:
    lowered = filename.lower()
    if lowered.endswith(".pdf"):
        return "pdf"
    if lowered.endswith(".docx") or lowered.endswith(".doc"):
        return "docx"
    if lowered.endswith(".pptx") or lowered.endswith(".ppt"):
        return "pptx"
    return "txt"


# ------------------------------------------------------------------- heading matching

def _number(raw: str) -> int | None:
    raw = raw.strip().lower()
    if raw.isdigit():
        return int(raw)
    if raw in WORD_NUMBERS:
        return WORD_NUMBERS[raw]
    if raw in ROMAN:
        return ROMAN[raw]
    return None


def _is_toc_line(text: str) -> bool:
    return bool(TOC_RE.search(text)) and len(text) < 120


def _title_from(match_title: str, blocks: list[dict], index: int, fallback: str) -> str:
    title = clean(match_title).strip(" :.-\u2013\u2014")
    if len(title) < 3:
        for offset in range(1, 4):
            if index + offset < len(blocks):
                candidate = clean(blocks[index + offset]["text"]).strip(" :.-")
                if 3 <= len(candidate) <= 120:
                    title = candidate
                    break
    return (title or fallback)[:240]


def find_chapter_headings(blocks: list[dict]) -> list[dict]:
    """Return one entry per detected chapter start, with duplicates resolved."""
    hits: list[dict] = []
    for index, block in enumerate(blocks):
        text = block["text"]
        if _is_toc_line(text):
            continue
        match = CHAPTER_RE.match(text)
        if match:
            number = _number(match.group("num"))
            if number is None or number > 60:
                continue
            hits.append({
                "index": index,
                "number": number,
                "title": _title_from(match.group("title"), blocks, index, f"Chapter {number}"),
            })
            continue
        if block["style"] == "h1" and 3 <= len(text) <= 140:
            hits.append({"index": index, "number": None, "title": text})
    if not hits:
        return []

    # A table of contents repeats every chapter title near the front of the book.
    # For each chapter number keep the occurrence that is followed by the most text.
    spans: dict = {}
    for position, hit in enumerate(hits):
        end = hits[position + 1]["index"] if position + 1 < len(hits) else len(blocks)
        hit["span"] = end - hit["index"]
        key = hit["number"] if hit["number"] is not None else f"t:{hit['title'].lower()}"
        if key not in spans or hit["span"] > spans[key]["span"]:
            spans[key] = hit
    kept = sorted(spans.values(), key=lambda h: h["index"])
    return [h for h in kept if h["span"] >= 3] or kept


def find_module_headings(blocks: list[dict], start: int, end: int) -> list[dict]:
    hits = []
    for index in range(start, end):
        text = blocks[index]["text"]
        if _is_toc_line(text):
            continue
        if CHAPTER_RE.match(text):
            continue
        match = MODULE_RE.match(text) or NUMBERED_RE.match(text)
        if match:
            raw = match.group("num")
            number = int(float(raw)) if "." not in raw else int(raw.split(".")[1])
            hits.append({
                "index": index,
                "number": number,
                "title": _title_from(match.group("title"), blocks, index, f"Module {number}"),
            })
        elif blocks[index]["style"] == "h2" and 3 <= len(text) <= 140:
            hits.append({"index": index, "number": None, "title": text})
    seen, unique = set(), []
    for hit in hits:
        key = hit["title"].lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(hit)
    return unique


# ------------------------------------------------------------------------- splitting

def _text_of(blocks: list[dict], start: int, end: int) -> str:
    return "\n".join(b["text"] for b in blocks[start:end]).strip()


def _guess_title(text: str, fallback: str) -> str:
    for line in text.split("\n"):
        line = clean(line).strip(" :.-")
        if 12 <= len(line) <= 110 and not line.endswith((",", ";")):
            words = line.split()
            if 2 <= len(words) <= 16:
                return line[:240]
    return fallback


def _even_chunks(blocks: list[dict], start: int, end: int, count: int) -> list[tuple[int, int]]:
    total = max(end - start, 1)
    count = max(1, min(count, total))
    size = total / count
    bounds = []
    for i in range(count):
        chunk_start = start + int(round(i * size))
        chunk_end = start + int(round((i + 1) * size)) if i < count - 1 else end
        if chunk_end > chunk_start:
            bounds.append((chunk_start, chunk_end))
    return bounds


def split_modules(blocks: list[dict], start: int, end: int) -> list[dict]:
    headings = find_module_headings(blocks, start + 1, end)
    modules = []
    if len(headings) >= 2:
        for position, hit in enumerate(headings):
            stop = headings[position + 1]["index"] if position + 1 < len(headings) else end
            body = _text_of(blocks, hit["index"], stop)
            if len(body) < 40 and position + 1 < len(headings):
                continue
            modules.append({"number": position + 1, "title": hit["title"], "raw_text": body})
    if not modules:
        span = end - start
        wanted = 2 if span < 24 else min(7, max(3, span // 18))
        for position, (chunk_start, chunk_end) in enumerate(
            _even_chunks(blocks, start + 1, end, wanted), start=1
        ):
            body = _text_of(blocks, chunk_start, chunk_end)
            if not body:
                continue
            modules.append({
                "number": position,
                "title": _guess_title(body, f"Module {position}"),
                "raw_text": body,
            })
    return modules or [{
        "number": 1,
        "title": "Module 1",
        "raw_text": _text_of(blocks, start, end) or "No readable text in this section.",
    }]


def dedupe_repeats(blocks: list[dict]) -> list[dict]:
    """Drop a line that immediately repeats the one before it, such as a running head."""
    cleaned: list[dict] = []
    for block in blocks:
        if cleaned and cleaned[-1]["text"].lower() == block["text"].lower():
            if block["style"] != "body":
                cleaned[-1]["style"] = block["style"]
            continue
        cleaned.append(block)
    return cleaned


def split_document(blocks: list[dict]) -> tuple[list[dict], str]:
    """Return (chapters, note). Each chapter carries its own module list."""
    blocks = dedupe_repeats(blocks)
    if not blocks:
        return [], "No readable text was found in the file."

    headings = find_chapter_headings(blocks)
    note = ""
    segments: list[tuple[int, int, str, int]] = []

    if len(headings) >= 2:
        for position, hit in enumerate(headings):
            end = headings[position + 1]["index"] if position + 1 < len(headings) else len(blocks)
            number = hit["number"] if hit["number"] is not None else position + 1
            segments.append((hit["index"], end, hit["title"], number))
        note = f"Detected {len(segments)} chapter headings in the document."
    else:
        count = min(12, max(3, len(blocks) // 60 or 3))
        for position, (start, end) in enumerate(_even_chunks(blocks, 0, len(blocks), count), start=1):
            body = _text_of(blocks, start, end)
            segments.append((start, end, _guess_title(body, f"Part {position}"), position))
        note = (
            "No chapter headings were found, so the book was divided into "
            f"{len(segments)} evenly sized chapters."
        )

    chapters = []
    used_numbers = set()
    for position, (start, end, title, number) in enumerate(segments, start=1):
        if number in used_numbers or number <= 0:
            number = position
        used_numbers.add(number)
        chapters.append({
            "number": number,
            "title": title,
            "raw_text": _text_of(blocks, start, end),
            "modules": split_modules(blocks, start, end),
        })
    return chapters, note


<<<<<<< HEAD
def extract(path: str, filename: str, course_hint: str = "", use_model: bool = True) -> dict:
    """Read the file and work out its chapters and modules.

    With a model running, structure.split_with_model reads the candidate headings and says
    which of them really start a section. Without one, or if what comes back does not hold
    up, this falls through to the pattern matcher below, which is what it always used.
    """
    kind = detect_kind(filename)
    blocks = READERS[kind](path)
    if use_model:
        from .structure import split_with_model

        chapters, note = split_with_model(blocks, course_hint)
    else:
        chapters, note = split_document(blocks)
=======
def extract(path: str, filename: str) -> dict:
    kind = detect_kind(filename)
    blocks = READERS[kind](path)
    chapters, note = split_document(blocks)
>>>>>>> origin/main
    characters = sum(len(b["text"]) for b in blocks)
    return {"kind": kind, "chapters": chapters, "note": note, "character_count": characters}


def excel_terms_in(text: str) -> list[str]:
    found = []
    for match in EXCEL_TERMS.finditer(text or ""):
        term = match.group(0).upper().replace("  ", " ")
        if term not in found:
            found.append(term)
    return found[:12]
