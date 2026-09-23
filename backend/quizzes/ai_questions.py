"""Quiz questions written by the local model from the section's own text.

The template bank is still there and still does the three long business questions, because
those are marked against a number the platform worked out itself and a model's arithmetic
cannot be trusted with that. The multiple choice questions are different: what matters is
that they are about the passage the student just read, so the model is asked to write them
from that passage.

Everything that comes back is checked before it is used. A question needs a prompt, four
distinct options, a correct answer that points at one of them, and an explanation. Anything
that fails is dropped, and if too few survive the template bank fills the rest, so a quiz
always has its full set.
"""
from __future__ import annotations

import json
import re
import urllib.request

from django.conf import settings

SYSTEM = (
    "You write multiple choice questions for undergraduate business students learning "
    "Microsoft Excel. You answer with JSON only: no prose, no markdown fences."
)
MAX_ROWS = 8
MAX_COLUMNS = 4


def _ask(prompt: str, tokens: int = 1800) -> str | None:
    if not getattr(settings, "USE_OLLAMA", True):
        return None
    host = getattr(settings, "OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
    model = getattr(settings, "OLLAMA_MODEL", "llama3.1:8b")
    body = json.dumps({
        "model": model,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.5, "num_predict": tokens},
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt},
        ],
    }).encode()
    request = urllib.request.Request(
        f"{host}/api/chat", data=body, headers={"content-type": "application/json"}
    )
    try:
        with urllib.request.urlopen(
            request, timeout=getattr(settings, "OLLAMA_TIMEOUT", 180)
        ) as response:
            payload = json.loads(response.read().decode())
    except Exception:
        return None
    return (payload.get("message") or {}).get("content", "") or None


def _clean_sheet(raw, title: str) -> dict:
    """Turn the model's little table into the worksheet the app draws beside the question."""
    if not isinstance(raw, dict):
        return {}
    headers = [str(cell)[:24] for cell in (raw.get("headers") or [])][:MAX_COLUMNS]
    rows = []
    for row in (raw.get("rows") or [])[:MAX_ROWS]:
        if not isinstance(row, list):
            continue
        rows.append([str(cell)[:24] for cell in row][:MAX_COLUMNS])
    if not headers or not rows:
        return {}
    width = len(headers)
    rows = [row + [""] * (width - len(row)) for row in rows if len(row) <= width]
    file_name = re.sub(r"[^A-Za-z0-9]+", "_", title)[:28].strip("_") or "Worksheet"
    return {
        "file": f"{file_name}.xlsx",
        "sheet": str(raw.get("sheet") or "Sheet1")[:18],
        "columns": [chr(65 + index) for index in range(width)],
        "rows": [headers] + rows,
        "highlight": [],
        "note": str(raw.get("note") or "")[:160],
    }


STOPWORDS = {
    "which", "would", "there", "where", "these", "those", "about", "after", "before",
    "under", "value", "cells", "cell", "excel", "sheet", "worksheet", "following",
    "statement", "student", "question", "answer", "formula", "column", "return", "returns",
}


def _grounded(prompt: str, options: list[str], passage: str) -> bool:
    """Is this question actually about the passage, or has the model wandered off?

    The instruction says to stay inside the section, but instructions are not a guarantee.
    A question that shares none of its subject words with the text it claims to be about is
    testing something the student was never given, so it is dropped.
    """
    lowered = passage.lower()
    words = {
        word for word in re.findall(r"[a-z]{5,}", f"{prompt} {' '.join(options)}".lower())
        if word not in STOPWORDS
    }
    if not words:
        return False
    hits = sum(1 for word in words if word in lowered)
    return hits >= 2


def _validate(item, title: str) -> dict | None:
    if not isinstance(item, dict):
        return None
    prompt = str(item.get("prompt") or item.get("question") or "").strip()
    options = [str(option).strip() for option in (item.get("options") or []) if str(option).strip()]
    explanation = str(item.get("explanation") or "").strip()
    if not prompt or len(prompt) < 15 or len(options) != 4 or not explanation:
        return None
    if len(set(option.lower() for option in options)) != 4:
        return None                              # repeated options give the answer away
    try:
        correct = int(item.get("correct_index"))
    except (TypeError, ValueError):
        return None
    if not 0 <= correct < 4:
        return None
    return {
        "prompt": prompt[:600],
        "options": [option[:120] for option in options],
        "correct_index": correct,
        "explanation": explanation[:600],
        "skill": str(item.get("skill") or "From your reading")[:80],
        "workbook": _clean_sheet(item.get("sheet"), title),
        "kind": "MCQ",
        "written_by": "ollama",
    }


def questions_from_text(title: str, text: str, count: int, seed_hint: str = "") -> list[dict]:
    """Ask the model for `count` questions about this section.

    The passage handed in is the explanation the student was given for the section, with
    the book's own text behind it, so the questions are about the page they actually read
    rather than about Excel in general. Returns what survives checking.
    """
    passage = (text or "").strip()
    if len(passage) < 200:
        return []

    prompt = (
        f"Below is the explanation a student has just read for the section '{title}', "
        "followed by the text it was written from.\n\n"
        f"{passage[:7000]}\n\n"
        f"Write {count} multiple choice questions that test whether the student has "
        "understood this explanation.\n"
        "Every question must be answerable from the explanation above. Ask about the ideas "
        "it actually sets out, in the order it sets them out. Do not use a fact, a "
        "function or an example that is not in it, and do not test an Excel feature it never "
        "mentions. If the passage is short, ask fewer but stay inside it.\n"
        "Make the wrong answers plausible: the mistakes a student actually makes on this "
        "material, not silly options.\n"
        + (f"Vary them from any earlier set: {seed_hint}\n" if seed_hint else "")
        + "Where a question would be clearer with a small worksheet beside it, include a "
        "sheet with up to four columns and eight rows of realistic business data.\n"
        "Answer with JSON only, in this shape:\n"
        '{"questions": [{"prompt": "...", "options": ["a","b","c","d"], "correct_index": 0, '
        '"explanation": "why that answer is right", "skill": "what it tests", '
        '"sheet": {"sheet": "Sales", "headers": ["Branch","Revenue"], '
        '"rows": [["North","24000"]], "note": ""}}]}'
    )
    answer = _ask(prompt)
    if not answer:
        return []
    match = re.search(r"\{.*\}", answer, re.DOTALL)
    if not match:
        return []
    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []

    raw = payload.get("questions") if isinstance(payload, dict) else payload
    written = []
    seen = set()
    for item in raw or []:
        question = _validate(item, title)
        if question and not _grounded(question["prompt"], question["options"], passage):
            question = None                      # about something this module never covered
        if question and question["prompt"].lower() not in seen:
            seen.add(question["prompt"].lower())
            written.append(question)
        if len(written) == count:
            break
    return written
