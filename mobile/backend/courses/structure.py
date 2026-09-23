"""Work out the shape of an uploaded book with help from the local model.

The pattern matcher in extraction.py is fast and predictable, but it only recognises the
headings it was taught: "Chapter 4", "Module 2.1", a Word Heading 1. Real books label their
parts in ways nobody anticipated, and a PDF hands over short lines that look like headings
and are not.

So the model is asked to read the candidate lines and say which of them actually start a
chapter or a module. It answers with line numbers, never with prose, and every number is
checked against the lines we sent before it is used. If Ollama is not running, or answers
with something that does not hold up, the pattern matcher takes over and the upload behaves
exactly as it did before.
"""
from __future__ import annotations

import json
import re
import urllib.request

from django.conf import settings

from .extraction import (
    _is_toc_line,
    dedupe_repeats,
    find_chapter_headings,
    find_module_headings,
    split_document,
)

MAX_CANDIDATES = 220
SYSTEM = (
    "You identify the structure of a book. You answer with JSON only: no prose, no "
    "explanation, no markdown fences."
)


def strip_running_heads(blocks: list[dict]) -> list[dict]:
    """Drop the line that sits at the top or the bottom of every page.

    A running head is short, identical each time and appears on most pages. It is not part
    of the text and it confuses everything downstream, so it goes before anything else
    looks at the book.
    """
    pages: dict = {}
    for block in blocks:
        key = block["text"].strip().lower()
        if len(key) > 90:
            continue
        pages.setdefault(key, set()).add(block.get("page", 0))
    running = {key for key, seen in pages.items() if len(seen) >= 3}
    if not running:
        return blocks
    return [block for block in blocks if block["text"].strip().lower() not in running]


def regex_candidates(blocks: list[dict]) -> list[dict]:
    """What the pattern matcher thinks are headings, before anything is believed.

    These are the lines the model is asked to rule on: which of them really start a
    section, and which are a contents page, a running head or a repeat.
    """
    found = []
    for hit in find_chapter_headings(blocks):
        found.append({"line": hit["index"], "kind": "chapter", "title": hit["title"]})
    if found:
        edges = [hit["line"] for hit in found] + [len(blocks)]
        for position, hit in enumerate(found[:]):
            for module in find_module_headings(blocks, hit["line"] + 1, edges[position + 1]):
                found.append({"line": module["index"], "kind": "module",
                              "title": module["title"]})
    return sorted(found, key=lambda item: item["line"])


def verify_candidates(course_hint: str, candidates: list[dict],
                      blocks: list[dict]) -> dict | None:
    """Ask the model to keep the real headings and say why it dropped the others."""
    if not getattr(settings, "USE_OLLAMA", True) or len(candidates) < 2:
        return None
    host = getattr(settings, "OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
    model = getattr(settings, "OLLAMA_MODEL", "llama3.1:8b")

    listing = []
    for item in candidates[:180]:
        follows = " ".join(
            block["text"] for block in blocks[item["line"] + 1:item["line"] + 3]
        )[:110]
        listing.append(
            f'{item["line"]}: [{item["kind"]}] {item["title"]}  ->  follows: {follows}'
        )

    prompt = (
        "A pattern matcher pulled these candidate headings out of a book"
        + (f" about {course_hint}" if course_hint else "")
        + ". Some of them really do start a chapter or a module. Others are a table of "
        "contents entry, a running header or footer, a repeat of a heading, or an ordinary "
        "line that happens to look like one.\n\n"
        "The text after each candidate is shown so you can tell them apart: a real heading "
        "is followed by the section itself, while a contents entry is followed by another "
        "contents entry, and a header or footer is followed by unrelated text.\n\n"
        "Answer with JSON only:\n"
        '{"keep": [12, 18, 25], "drop": [{"line": 3, "reason": "table of contents"}]}\n\n'
        + "\n".join(listing)[:12000]
    )
    body = json.dumps({
        "model": model,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.1, "num_predict": 1200},
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
    answer = (payload.get("message") or {}).get("content", "")
    match = re.search(r"\{.*\}", answer, re.DOTALL)
    if not match:
        return None
    try:
        verdict = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(verdict, dict) or not isinstance(verdict.get("keep"), list):
        return None
    return verdict


def build_confirmed(candidates: list[dict], keep: set, blocks: list[dict]):
    """Assemble the book from the candidates the model kept."""
    kept = [item for item in candidates if item["line"] in keep]
    chapter_lines = [item for item in kept if item["kind"] == "chapter"]
    if len(chapter_lines) < 2:
        return None

    edges = [item["line"] for item in chapter_lines] + [len(blocks)]
    chapters = []
    for position, chapter in enumerate(chapter_lines):
        start, stop = chapter["line"], edges[position + 1]
        modules = [item for item in kept
                   if item["kind"] == "module" and start < item["line"] < stop]
        bounds = [item["line"] for item in modules] + [stop]
        built = []
        for module_position, module in enumerate(modules):
            text = "\n".join(
                block["text"] for block in blocks[module["line"]:bounds[module_position + 1]]
            ).strip()
            built.append({"number": module_position + 1, "title": module["title"],
                          "raw_text": text})
        if not built:
            built = [{
                "number": 1,
                "title": chapter["title"],
                "raw_text": "\n".join(b["text"] for b in blocks[start:stop]).strip(),
            }]
        chapters.append({
            "number": position + 1,
            "title": chapter["title"],
            "raw_text": "\n".join(b["text"] for b in blocks[start:stop]).strip(),
            "modules": built,
        })

    if sum(len(chapter["raw_text"]) for chapter in chapters) / len(chapters) < 200:
        return None
    return chapters


def candidate_lines(blocks: list[dict]) -> list[tuple[int, str]]:
    """The lines that could plausibly start a section, with their position in the book."""
    candidates = []
    for index, block in enumerate(blocks):
        text = block["text"].strip()
        if not 3 <= len(text) <= 110:
            continue
        # A contents page repeats every chapter title before the book starts. Offering
        # those to the model gets the book sliced at the contents page.
        if _is_toc_line(text):
            continue
        if block["style"] in ("h1", "h2"):
            candidates.append((index, text))
            continue
        # A heading rarely ends in a full stop, but the model is better placed to judge
        # borderline lines than a rule is, so anything short enough is offered to it.
        words = text.split()
        if 1 <= len(words) <= 16:
            candidates.append((index, text))
    if len(candidates) <= MAX_CANDIDATES:
        return candidates

    # Too many to send. Thinning them evenly would throw away real headings, so the lines
    # that look like one are all kept and the rest are sampled to fill the room left.
    from .extraction import CHAPTER_RE, MODULE_RE, NUMBERED_RE

    def looks_like_heading(text: str) -> bool:
        return bool(CHAPTER_RE.match(text) or MODULE_RE.match(text) or NUMBERED_RE.match(text))

    strong = [item for item in candidates if looks_like_heading(item[1])]
    weak = [item for item in candidates if item not in strong]
    room = max(MAX_CANDIDATES - len(strong), 0)
    if room and weak:
        step = len(weak) / room
        weak = [weak[int(position * step)] for position in range(room)]
    else:
        weak = []
    return sorted(strong[:MAX_CANDIDATES] + weak, key=lambda item: item[0])


def ask_model(course_hint: str, candidates: list[tuple[int, str]]) -> list[dict] | None:
    if not getattr(settings, "USE_OLLAMA", True) or not candidates:
        return None
    host = getattr(settings, "OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
    model = getattr(settings, "OLLAMA_MODEL", "llama3.1:8b")

    listing = "\n".join(f"{index}: {text}" for index, text in candidates)
    prompt = (
        "Below are numbered lines taken from a book"
        + (f" about {course_hint}" if course_hint else "")
        + ". Some of them are the titles of chapters or of the sections inside a chapter. "
        "Most of them are ordinary lines of text.\n\n"
        "Pick out the real structure of the book itself. Ignore the table of contents, "
        "running headers and footers, page numbers, an index, and any heading that is "
        "repeated: keep the occurrence that is followed by the section's own text, not the "
        "one that is followed by another heading. Ignore lines that only look like headings "
        "because they are short.\n"
        "Keep the order the lines came in. Every chapter needs at least one module, and a "
        "module's line number must be greater than its chapter's.\n"
        "Answer with JSON only, in this shape and nothing else:\n"
        '[{"line": 12, "title": "Chapter title", '
        '"modules": [{"line": 15, "title": "Module title"}]}]\n\n'
        + listing[:12000]
    )
    body = json.dumps({
        "model": model,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.1, "num_predict": 1600},
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

    answer = (payload.get("message") or {}).get("content", "")
    match = re.search(r"\[.*\]", answer, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def _title_key(title: str) -> str:
    """A loose fingerprint of a heading, for spotting the same one twice."""
    stripped = re.sub(r"^\s*(chapter|module|unit|part|section)\s*\d*\s*[:.\-\u2013]?\s*",
                      "", title, flags=re.IGNORECASE)
    return re.sub(r"[^a-z0-9]+", "", stripped.lower())[:24]


def assemble(plan: list[dict], blocks: list[dict], candidates: list[tuple[int, str]]):
    """Turn the model's line numbers into chapters and modules, or refuse them.

    Nothing the model says is taken on trust: a line number has to be one we actually sent,
    the order has to make sense, and the result has to look like a book rather than a list
    of one line sections. If any of that fails we return None and the caller falls back.
    """
    allowed = dict(candidates)
    chapters = []
    for entry in plan if isinstance(plan, list) else []:
        try:
            line = int(entry.get("line"))
        except (TypeError, ValueError):
            continue
        if line not in allowed:
            continue
        modules = []
        for module in entry.get("modules") or []:
            try:
                module_line = int(module.get("line"))
            except (TypeError, ValueError):
                continue
            if module_line in allowed and module_line > line:
                modules.append({
                    "line": module_line,
                    "title": str(module.get("title") or allowed[module_line])[:240],
                })
        if not modules:
            continue
        chapters.append({
            "line": line,
            "title": str(entry.get("title") or allowed[line])[:240],
            "modules": sorted(modules, key=lambda item: item["line"]),
        })

    # The same title twice means the contents page slipped through; keep the occurrence
    # with real text after it. Contents pages rarely reproduce a heading character for
    # character, so titles are compared with the numbering stripped and truncated.
    chapters.sort(key=lambda item: item["line"])
    for position, chapter in enumerate(chapters):
        end = chapters[position + 1]["line"] if position + 1 < len(chapters) else len(blocks)
        chapter["span"] = end - chapter["line"]

    kept: list[dict] = []
    for chapter in chapters:
        key = _title_key(chapter["title"])
        match = next(
            (item for item in kept
             if key and item["key"] and (key.startswith(item["key"][:12])
                                         or item["key"].startswith(key[:12]))),
            None,
        )
        if match is None:
            kept.append({**chapter, "key": key})
            continue
        # A heading that appears twice is usually the contents page and then the chapter
        # itself, so when the first one sits in the opening pages the later one wins.
        front_matter = match["line"] < len(blocks) * 0.15
        if front_matter or chapter["span"] > match["span"]:
            kept[kept.index(match)] = {**chapter, "key": key}

    chapters = sorted(kept, key=lambda item: item["line"])
    chapters = [chapter for chapter in chapters if chapter["span"] >= 6] or chapters
    if len(chapters) < 2:
        return None

    # Slice the book at the lines the model picked.
    boundaries = [chapter["line"] for chapter in chapters] + [len(blocks)]
    built = []
    for position, chapter in enumerate(chapters):
        start, stop = chapter["line"], boundaries[position + 1]
        module_lines = [m["line"] for m in chapter["modules"] if start < m["line"] < stop]
        if not module_lines:
            return None
        modules = []
        for module_position, module in enumerate(chapter["modules"]):
            if not start < module["line"] < stop:
                continue
            module_stop = (
                chapter["modules"][module_position + 1]["line"]
                if module_position + 1 < len(chapter["modules"])
                and chapter["modules"][module_position + 1]["line"] < stop
                else stop
            )
            text = "\n".join(b["text"] for b in blocks[module["line"]:module_stop]).strip()
            modules.append({
                "number": len(modules) + 1,
                "title": module["title"],
                "raw_text": text,
            })
        if not modules:
            return None
        built.append({
            "number": position + 1,
            "title": chapter["title"],
            "raw_text": "\n".join(b["text"] for b in blocks[start:stop]).strip(),
            "modules": modules,
        })

    average = sum(len(c["raw_text"]) for c in built) / len(built)
    if average < 200:
        return None                     # sections too thin to teach from: do not trust it
    return built


def split_with_model(blocks: list[dict], course_hint: str = "") -> tuple[list[dict], str]:
    """Chapters and modules for an uploaded book, read by the local model.

    The model does the reading. It is shown the lines of the book, numbered, and asked which
    of them start a chapter or a module, with the table of contents, the running heads, the
    repeats and the lines that merely look like headings left out. It answers with line
    numbers, never prose.

    Two safety nets sit behind that, because a model can be unavailable or wrong and an
    upload still has to work. If the model's outline does not hold up against the lines that
    were sent, the pattern matcher's candidates are put back to it for a simpler keep or drop
    decision. If that fails too, the pattern matcher's own reading stands, which is exactly
    what the platform did before any model was involved.
    """
    blocks = strip_running_heads(dedupe_repeats(blocks))
    if not blocks:
        return [], "No readable text was found in the file."

    fallback, note = split_document(blocks)

    # 1. The model reads the book.
    lines = candidate_lines(blocks)
    plan = ask_model(course_hint, lines)
    if plan:
        read = assemble(plan, blocks, lines)
        if read:
            modules = sum(len(chapter["modules"]) for chapter in read)
            return read, (
                f"The local model read the book: {len(read)} chapters and {modules} modules, "
                "with the contents page, running heads and repeats left out."
            )

    # 2. The model rules on what the pattern matcher proposed.
    candidates = regex_candidates(blocks)
    if candidates:
        verdict = verify_candidates(course_hint, candidates, blocks)
        if verdict:
            offered = {item["line"] for item in candidates}
            keep = {line for line in verdict.get("keep", [])
                    if isinstance(line, int) and line in offered}
            confirmed = build_confirmed(candidates, keep, blocks)
            if confirmed:
                modules = sum(len(chapter["modules"]) for chapter in confirmed)
                dropped = len(offered) - len(keep)
                reasons = {
                    str(item.get("reason", ""))[:40]
                    for item in verdict.get("drop", []) if isinstance(item, dict)
                }
                tail = f" as {', '.join(sorted(r for r in reasons if r))}" if reasons else ""
                return confirmed, (
                    f"The local model checked {len(offered)} candidate headings and kept "
                    f"{len(keep)}, dropping {dropped}{tail}. "
                    f"{len(confirmed)} chapters and {modules} modules."
                )

    # 3. No model, or nothing from it held up.
    return fallback, note
