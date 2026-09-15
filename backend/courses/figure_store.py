"""Save the pictures found in a book and have the model caption them.

Two jobs live here. The first runs once, when a book is uploaded: read the pictures out
of the file, work out which chapter or module each belongs to, and store them. The second
runs when a student opens a section: any picture there that has not been described yet is
handed to the local model along with the explanation being read, and gets a caption back.

Captioning is done at reading time rather than at upload time on purpose. An upload with
forty figures in it would otherwise sit there while the model wrote forty captions, and
nobody would know why. This way the first reader of a section pays for a handful and the
section is fully captioned soon after.
"""
from __future__ import annotations

import base64

from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone

from .explain import figure_caption
from .figures import caption_from_context, place_figure, read_figures
from .models import BookImage


def store_figures(book, path: str, kind: str) -> int:
    """Read every picture out of the uploaded file and hang it on its section.

    Returns how many were stored. Nothing here is allowed to break an upload, so a file
    whose pictures cannot be read simply stores none of them.
    """
    if not getattr(settings, "EXTRACT_BOOK_IMAGES", True):
        return 0
    try:
        figures = read_figures(path, kind)
    except Exception:
        return 0
    return save_figures(book, figures)


def collect_figures(path: str, kind: str) -> list[dict]:
    """Read the pictures out of one file without saving anything yet.

    A generated book is built from several uploaded files at once, and each scratch copy
    is deleted as soon as it has been read, so its pictures have to be taken then and
    saved after the chapters exist.
    """
    if not getattr(settings, "EXTRACT_BOOK_IMAGES", True):
        return []
    try:
        return read_figures(path, kind)
    except Exception:
        return []


def save_figures(book, figures: list[dict]) -> int:
    """Place each picture on a chapter or module of this book and store it."""
    if not figures:
        return 0

    chapters = list(book.chapters.all())
    if not chapters:
        return 0
    modules = [module for chapter in chapters for module in chapter.modules.all()]

    stored = 0
    for position, figure in enumerate(figures, start=1):
        try:
            chapter, module = place_figure(figure, chapters, modules)
            if chapter is None and module is None:
                continue
            name = f"book{book.id}_fig{position}{figure['extension']}"
            BookImage.objects.create(
                book=book,
                chapter=None if module else chapter,
                module=module,
                file=ContentFile(figure["data"], name=name),
                page=figure.get("page", 0),
                order=figure.get("order", position),
                width=figure.get("width", 0),
                height=figure.get("height", 0),
                context_text=(figure.get("context") or "")[:2000],
                caption=caption_from_context(figure.get("context", ""), figure.get("page", 0)),
            )
            stored += 1
        except Exception:
            continue
    return stored


def describe_pending(obj, kind: str) -> int:
    """Write captions for the pictures in this section that have not got one yet.

    `obj` is a Chapter or a Module. A chapter takes in its modules' pictures too, because
    that is what the reading screen shows. Only a few are done on any one visit so the
    page still opens quickly; the rest are picked up next time.
    """
    if not getattr(settings, "EXTRACT_BOOK_IMAGES", True):
        return 0
    limit = int(getattr(settings, "CAPTIONS_PER_VISIT", 6))
    if limit <= 0:
        return 0

    if kind == "chapter":
        from django.db.models import Q

        pending = BookImage.objects.filter(
            Q(chapter=obj) | Q(module__chapter=obj), described_at__isnull=True
        )
    else:
        pending = BookImage.objects.filter(module=obj, described_at__isnull=True)

    written = 0
    for image in pending[:limit]:
        encoded = ""
        if getattr(settings, "OLLAMA_VISION_MODEL", ""):
            try:
                with image.file.open("rb") as handle:
                    encoded = base64.b64encode(handle.read()).decode()
            except Exception:
                encoded = ""
        try:
            caption = figure_caption(
                obj.title, obj.explanation or "", image.context_text or "", encoded
            )
        except Exception:
            caption = None
        if not caption:
            continue                     # Ollama is not answering; keep the plain caption
        image.caption = caption
        image.described_at = timezone.now()
        image.save(update_fields=["caption", "described_at"])
        written += 1
    return written
