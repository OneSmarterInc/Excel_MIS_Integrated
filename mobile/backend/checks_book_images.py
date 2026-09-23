"""Check that pictures come out of a book and land on the right section.

Run it with the server stopped:

    python checks_book_images.py

It builds a small Word file, a PowerPoint file and a PDF, each with a picture in a known
place, pushes them through the same path an upload takes, and reports where each picture
ended up. Ollama is not needed; captions fall back to the words around the picture.
"""
import io
import os
import tempfile

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
os.environ.setdefault("USE_OLLAMA", "0")
django.setup()

from django.contrib.auth import get_user_model  # noqa: E402

from courses.extraction import detect_kind, extract  # noqa: E402
from courses.figure_store import store_figures  # noqa: E402
from courses.figures import read_figures  # noqa: E402
from courses.models import Book, Course  # noqa: E402
from courses.views import store_chapters  # noqa: E402

PASS, FAIL = "  ok  ", " FAIL "


def picture(colour, size=(420, 300)) -> bytes:
    from PIL import Image, ImageDraw

    image = Image.new("RGB", size, colour)
    draw = ImageDraw.Draw(image)
    for x in range(0, size[0], 40):
        draw.line([(x, 0), (x, size[1])], fill=(20, 20, 20), width=2)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def build_docx(path):
    import docx

    document = docx.Document()
    document.add_heading("Chapter 1 Building a worksheet", level=1)
    document.add_paragraph(
        "Module 1 Entering data. A worksheet begins as an empty grid of cells. "
        "Type the headings into row one and the figures underneath them, and the "
        "column becomes something a formula can add up later on."
    )
    document.add_paragraph(
        "The screenshot below shows the headings sitting in row one of the sheet."
    )
    document.add_picture(io.BytesIO(picture((220, 230, 245))))
    document.add_paragraph(
        "Module 2 Adding a total. The SUM function adds every cell in a range, and the "
        "colon between two addresses is what makes them a range rather than two cells."
    )
    document.add_paragraph(
        "Here the total appears in the row under the column of revenue figures."
    )
    document.add_picture(io.BytesIO(picture((245, 225, 215))))
    document.add_heading("Chapter 2 Looking values up", level=1)
    document.add_paragraph(
        "Module 1 VLOOKUP. VLOOKUP searches the first column of a table and returns a "
        "value from a column beside it, which is how a code becomes a product name."
    )
    document.save(path)


def build_pptx(path):
    from pptx import Presentation
    from pptx.util import Inches

    presentation = Presentation()
    for index, (heading, body) in enumerate(
        [
            ("Chapter 1 Charts that answer a question",
             "A column chart compares branches against each other."),
            ("Chapter 2 Conditional formatting",
             "A rule colours the cell as the figure is typed into it."),
        ]
    ):
        slide = presentation.slides.add_slide(presentation.slide_layouts[5])
        slide.shapes.title.text = heading
        box = slide.shapes.add_textbox(Inches(0.6), Inches(1.6), Inches(6), Inches(1.2))
        box.text_frame.text = body
        slide.shapes.add_picture(
            io.BytesIO(picture((210, 240, 220) if index == 0 else (245, 215, 235))),
            Inches(0.6), Inches(3.0), Inches(4),
        )
    presentation.save(path)


def build_pdf(path):
    """A small PDF with real text on each page and a JPEG figure beside it.

    It is assembled by hand rather than with a PDF library so the check script does not
    add a dependency the platform itself does not use.
    """
    import io as _io

    from PIL import Image

    def jpeg(colour):
        from PIL import ImageDraw

        image = Image.new("RGB", (520, 360), colour)
        draw = ImageDraw.Draw(image)
        for x in range(0, 520, 60):
            for y in range(0, 360, 60):
                draw.rectangle([x, y, x + 28, y + 28], fill=(40, 60, 110))
        buffer = _io.BytesIO()
        image.save(buffer, format="JPEG", quality=90)
        return buffer.getvalue()

    lines = [
        [
            "Chapter 1 Reading the formula bar",
            "Module 1 What the bar shows. The grid shows a cell after formatting has been",
            "applied to it, and the formula bar shows what is really inside the cell. When",
            "the two disagree, the formula bar is the one telling the truth about the sheet.",
            "The screenshot below has a formula in the bar and a rounded figure in the grid.",
        ],
        [
            "Chapter 2 Absolute references",
            "Module 1 Locking a cell. Dollar signs hold a reference still while a formula is",
            "copied down a column, so a shared tax rate in E1 stays E1 on every row instead",
            "of drifting to E2 and quietly returning zero on the second line of the sheet.",
            "The screenshot below shows the same formula copied down four rows.",
        ],
    ]

    objects = {}
    images = [jpeg((226, 234, 248)), jpeg((246, 231, 222))]

    for index, page_lines in enumerate(lines):
        text = "BT /F1 13 Tf 60 760 Td 18 TL\n"
        for line in page_lines:
            text += f"({line}) Tj T*\n"
        text += "ET\nq 360 0 0 250 60 380 cm /Im0 Do Q"
        objects[5 + index] = (
            f"<< /Length {len(text)} >>\nstream\n{text}\nendstream".encode("latin-1")
        )
        objects[8 + index] = (
            b"<< /Type /XObject /Subtype /Image /Width 520 /Height 360 "
            b"/ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length "
            + str(len(images[index])).encode()
            + b" >>\nstream\n"
            + images[index]
            + b"\nendstream"
        )
        objects[3 + index] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources "
            f"<< /Font << /F1 7 0 R >> /XObject << /Im0 {8 + index} 0 R >> >> "
            f"/Contents {5 + index} 0 R >>"
        ).encode("latin-1")

    objects[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objects[2] = b"<< /Type /Pages /Kids [3 0 R 4 0 R] /Count 2 >>"
    objects[7] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"

    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for number in sorted(objects):
        offsets[number] = len(out)
        out += f"{number} 0 obj\n".encode() + objects[number] + b"\nendobj\n"
    start = len(out)
    top = max(objects) + 1
    out += f"xref\n0 {top}\n".encode()
    out += b"0000000000 65535 f \n"
    for number in range(1, top):
        out += f"{offsets.get(number, 0):010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {top} /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n".encode()
    with open(path, "wb") as handle:
        handle.write(bytes(out))


def report(label, condition, detail=""):
    print(f"[{PASS if condition else FAIL}] {label}" + (f"  {detail}" if detail else ""))
    return bool(condition)


def run_one(path, name):
    kind = detect_kind(name)
    figures = read_figures(path, kind)
    print(f"\n{name}: {len(figures)} pictures read out of the file")

    result = extract(path, name, use_model=False)
    faculty = get_user_model().objects.filter(role="FACULTY").first()
    if faculty is None:
        faculty = get_user_model().objects.create_user(
            email="figurecheck@example.com", password="checks123", name="Figure Check",
            role="FACULTY",
        )
    course, _ = Course.objects.get_or_create(
        code=f"FIG{abs(hash(name)) % 900 + 100}",
        defaults={"name": "Figure check", "faculty": faculty},
    )
    book = Book.objects.create(
        course=course, title=f"Check {name}", kind=result["kind"],
        extraction_note=result["note"][:250], character_count=result["character_count"],
    )
    store_chapters(book, result["chapters"])
    stored = store_figures(book, path, kind)

    ok = report(f"{name}: pictures stored", stored > 0, f"{stored} stored")
    for image in book.images.all():
        where = (
            f"module {image.module.chapter.number}.{image.module.number} "
            f"({image.module.title[:40]})"
            if image.module
            else f"chapter {image.chapter.number} ({image.chapter.title[:40]})"
        )
        print(f"        page {image.page or '-'} -> {where}")
        print(f"          caption: {image.caption[:110]}")
    ok = report(f"{name}: every picture has a section", all(
        image.chapter_id or image.module_id for image in book.images.all()
    )) and ok
    book.delete()
    return ok


def through_the_api(docx_path):
    """Upload the file the way the app does and read a chapter back out of the API."""
    import json

    from django.test import Client

    client = Client()
    login = client.post(
        "/api/auth/login/",
        json.dumps({"email": "faculty@mis3000.edu", "password": "faculty123"}),
        content_type="application/json",
    )
    if login.status_code != 200:
        print("\nSkipping the API check: run  python manage.py seed_demo  first.")
        return True
    token = login.json()["access"]
    auth = {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    courses = client.get("/api/courses/", **auth).json()
    course_id = courses[0]["id"]
    with open(docx_path, "rb") as handle:
        upload = client.post(
            f"/api/courses/{course_id}/books/",
            {"title": "Figure check book", "file": handle},
            **auth,
        )
    ok = report("API: the book uploaded", upload.status_code == 201, str(upload.status_code))
    if upload.status_code != 201:
        return False
    book = upload.json()
    print(f"        {book['extraction_note']}")

    chapter_id = book["chapters"][0]["id"]
    reading = client.get(f"/api/chapters/{chapter_id}/", **auth).json()
    images = reading.get("images") or []
    ok = report("API: the chapter carries its pictures", bool(images),
                f"{len(images)} on chapter 1") and ok
    for image in images:
        ok = report("API: the picture has an address the app can load",
                    image["file_url"].startswith("http")) and ok
        print(f"        {image['file_url']}")
        print(f"          {image['caption'][:100]}")

    module_id = book["chapters"][0]["modules"][0]["id"]
    module = client.get(f"/api/modules/{module_id}/", **auth).json()
    ok = report("API: a module carries only its own pictures",
                isinstance(module.get("images"), list),
                f"{len(module.get('images') or [])} on module 1.1") and ok

    Book.objects.filter(id=book["id"]).delete()
    return ok


def main():
    everything = True
    with tempfile.TemporaryDirectory() as folder:
        docx_path = os.path.join(folder, "worksheet_book.docx")
        pptx_path = os.path.join(folder, "slide_book.pptx")
        pdf_path = os.path.join(folder, "scanned_book.pdf")
        build_docx(docx_path)
        build_pptx(pptx_path)
        build_pdf(pdf_path)
        everything &= run_one(docx_path, "worksheet_book.docx")
        everything &= run_one(pptx_path, "slide_book.pptx")
        everything &= run_one(pdf_path, "scanned_book.pdf")
        print()
        everything &= through_the_api(docx_path)

    print()
    print("All checks passed." if everything else "Something above did not hold.")
    return 0 if everything else 1


if __name__ == "__main__":
    raise SystemExit(main())
