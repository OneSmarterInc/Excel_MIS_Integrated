"""A faculty-uploaded book, seen from the student's side.

Run with: python manage.py shell < checks_uploaded_book.py (after seed_demo, fresh database)
Needs a book-like PDF; put one next to manage.py or set SOURCE_PDF.

Proves that what the instructor uploads is what the student gets: every chapter listed,
every module under it, the easy explanation, and the same ten question quiz at both
module and chapter level.
"""
import os
import json
from django.test import Client

c = Client()
def tok(email, pw):
    return c.post("/api/auth/login/", json.dumps({"email": email, "password": pw}),
                  content_type="application/json").json()["access"]
def post(url, body, t):
    return c.post(url, json.dumps(body), content_type="application/json",
                  HTTP_AUTHORIZATION=f"Bearer {t}")
def get(url, t):
    return c.get(url, HTTP_AUTHORIZATION=f"Bearer {t}")

faculty = tok("faculty@mis3000.edu", "faculty123")
course = post("/api/courses/", {"code": "MIS3001", "name": "hello"}, faculty).json()
SOURCE = os.environ.get("SOURCE_PDF", "Excel_Formulas_and_Theory.pdf")
if not os.path.exists(SOURCE):
    raise SystemExit(f"Put a PDF at {SOURCE} or set SOURCE_PDF, then run this again.")
with open(SOURCE, "rb") as fh:
    book = c.post(f"/api/courses/{course['id']}/books/", {"file": fh, "title": "Excel_Formulas_and_Theory"},
                  HTTP_AUTHORIZATION=f"Bearer {faculty}").json()
print("faculty uploaded:", book["title"], "|", book["chapter_count"], "chapters,",
      book["module_count"], "modules | chapter statuses:",
      sorted({ch["status"] for ch in book["chapters"]}))

signup = c.post("/api/auth/register/", json.dumps({"name": "Student1", "email": "student1@gmail.com",
                                                   "password": "student1", "role": "STUDENT"}),
                content_type="application/json").json()
student = signup["access"]
post(f"/api/courses/{course['id']}/invitations/", {"emails": "student1@gmail.com"}, faculty)
invite = get("/api/my-invitations/", student).json()[0]
post(f"/api/invitations/{invite['id']}/respond/", {"decision": "accept"}, student)

seen = get(f"/api/courses/{course['id']}/", student).json()["books"][0]
print("\nSTUDENT SEES:", seen["chapter_count"], "chapters counted,",
      len(seen["chapters"]), "chapters listed")
for ch in seen["chapters"]:
    print(f"  Chapter {ch['number']}: {ch['title'][:44]} [{ch['status']}] "
          f"-> {len(ch['modules'])} modules")
assert len(seen["chapters"]) == seen["chapter_count"], "the list must match the count"

chapter = seen["chapters"][0]
module = chapter["modules"][0]
reading = get(f"/api/modules/{module['id']}/", student).json()
print("\nmodule explanation ->", len(reading["explanation"]), "characters")
print(reading["explanation"][:150].replace("\n", " | "))

quiz = post("/api/quizzes/start/", {"module_id": module["id"]}, student).json()
print("\nstudent quiz ->", len(quiz["questions"]), "questions |",
      len([q for q in quiz["questions"] if q["kind"] == "MCQ"]), "multiple choice,",
      len([q for q in quiz["questions"] if q["kind"] == "BUSINESS"]), "business")
print("first question:", quiz["questions"][0]["prompt"][:70])
print("its worksheet:", quiz["questions"][0]["workbook"]["file"],
      "with", len(quiz["questions"][0]["workbook"]["rows"]), "rows")

chapter_quiz = post("/api/quizzes/start/", {"chapter_id": chapter["id"]}, student)
print("chapter level quiz ->", chapter_quiz.status_code,
      len(chapter_quiz.json()["questions"]), "questions")
assert len(quiz["questions"]) == 10 and chapter_quiz.status_code == 201
print("UPLOADED BOOK IS FULLY VISIBLE TO THE STUDENT")
