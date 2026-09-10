"""The whole book download, on a generated book that is still in draft.

Run with: python manage.py shell < checks_download.py (after seed_demo, fresh database)
Needs a PDF to build from; point SOURCE at any book-like PDF you have.
"""
import os
import json
from django.test import Client
from courses.models import Book, Chapter, Module

c = Client()
tok = c.post("/api/auth/login/", json.dumps({"email": "faculty@mis3000.edu", "password": "faculty123"}),
             content_type="application/json").json()["access"]
auth = {"HTTP_AUTHORIZATION": f"Bearer {tok}"}

# A generated book, the same shape as the one on screen: drafts, never published.
course = c.post("/api/courses/", json.dumps({"code": "EXCEL1011", "name": "Excel fundamentals"}),
                content_type="application/json", **auth).json()
SOURCE = os.environ.get("SOURCE_PDF", "Excel_Formulas_and_Theory.pdf")
if not os.path.exists(SOURCE):
    raise SystemExit(f"Put a PDF at {SOURCE} or set SOURCE_PDF, then run this again.")
with open(SOURCE, "rb") as handle:
    made = c.post(f"/api/courses/{course['id']}/generate-book/",
                  {"files": [handle], "title": "Excel fundamentals course book"}, **auth).json()
book = Book.objects.get(pk=made["id"])
chapters = list(book.chapters.all())
modules = list(Module.objects.filter(chapter__book=book))
print("generated:", made["chapter_count"], "chapters,", made["module_count"], "modules,",
      "statuses:", sorted({ch.status for ch in chapters}))

response = c.get(f"/api/books/{book.id}/download/", **auth)
text = response.content.decode()
print("download ->", response.status_code,
      response["Content-Disposition"].split("filename=")[-1].strip(), len(text), "characters")

missing_ch = [ch.title for ch in chapters if ch.title not in text]
missing_mod = [m.title for m in modules if m.title not in text]
print("chapters present:", len(chapters) - len(missing_ch), "/", len(chapters))
print("modules present:", len(modules) - len(missing_mod), "/", len(modules))
body_in = sum(1 for m in modules if (m.raw_text or "")[:60].strip() and (m.raw_text or "")[:60].strip() in text)
print("module bodies present:", body_in, "/", len(modules))
assert not missing_ch and not missing_mod and body_in == len(modules)
print("first 240 characters:\n", text[:240])
print("DRAFT BOOK DOWNLOAD OK")
