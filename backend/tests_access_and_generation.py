"""Faculty with no book, plus access provision, end to end on the real uploaded files."""
import json
from django.test import Client
from django.core.files.uploadedfile import SimpleUploadedFile
from courses.models import Invitation

c = Client()


def login(email, password):
    r = c.post("/api/auth/login/", json.dumps({"email": email, "password": password}),
               content_type="application/json").json()
    return {"HTTP_AUTHORIZATION": f"Bearer {r['access']}"}


def post(url, payload, auth):
    return c.post(url, json.dumps(payload), content_type="application/json", **auth)


faculty = login("faculty@mis3000.edu", "faculty123")

# 1. A course with no book of its own.
course = post("/api/courses/", {"code": "MIS3250", "name": "Analysis and Design of Information Systems",
                                "description": "Built from lecture slides."}, faculty).json()
print("course created:", course["code"])

# 2. Build the book from the real lecture deck, the studio pack and the montage image.
files = []
for path in ["/mnt/user-data/uploads/MIS3250_Week01_Lecture.pptx",
             "/mnt/user-data/uploads/MIS3250_Week01_StudioPack.pptx",
             "/mnt/user-data/uploads/MIS3250_Week01_Lecture_Montage.png"]:
    with open(path, "rb") as handle:
        files.append(SimpleUploadedFile(path.split("/")[-1], handle.read()))
response = c.post(f"/api/courses/{course['id']}/generate-book/",
                  {"files": files, "title": "Systems Analysis and Design, Week 1",
                   "topics": "The SDLC; The analyst's role; Structured, object oriented and agile"},
                  **faculty)
book = response.json()
print("generated book:", response.status_code, "|", book.get("title"))
print("note:", book.get("extraction_note"))
print("chapters", book.get("chapter_count"), "modules", book.get("module_count"),
      "characters", book.get("character_count"))
for chapter in book.get("chapters", []):
    print(f"   Chapter {chapter['number']}: {chapter['title'][:52]}")
    for module in chapter["modules"]:
        print(f"        Module {module['number']}: {module['title'][:46]}")
assert response.status_code == 201 and book["chapter_count"] >= 3

# 3. Access provision: the faculty names who may take it.
granted = post(f"/api/courses/{course['id']}/invitations/",
               {"emails": "student@mis3000.edu, ram@example.edu, not-an-email"}, faculty).json()
print("\ninvited:", granted["added"], "| not an email:", granted["not_an_email"])

student = login("student@mis3000.edu", "student123")

# 4. A student nobody invited cannot get in by typing the code.
c.post("/api/auth/register/", json.dumps({"name": "Uninvited", "email": "nobody@mis3000.edu",
                                          "password": "nobody123", "role": "STUDENT"}),
       content_type="application/json")
outsider = login("nobody@mis3000.edu", "nobody123")
blocked = post("/api/join-course/", {"code": "MIS3250"}, outsider)
print("uninvited join ->", blocked.status_code, blocked.json().get("detail", "")[:70])
assert blocked.status_code == 403
codes = c.get("/api/course-codes/", **outsider).json()
print("uninvited dropdown shows", len(codes), "courses")
assert not any(item["code"] == "MIS3250" for item in codes)

mine = c.get("/api/my-invitations/", **student).json()
pending = [i for i in mine if i["course_code"] == "MIS3250"]
print("student sees the invitation:", [(i["course_code"], i["status"]) for i in pending])
assert pending

accepted = post(f"/api/invitations/{pending[0]['id']}/respond/", {"decision": "accept"}, student).json()
print("after accepting:", accepted["status"])

detail = c.get(f"/api/courses/{course['id']}/", **student).json()
print("student can now open the course:", detail["code"], "with", len(detail["books"]), "book")

chapter = detail["books"][0]["chapters"][0]
reading = c.get(f"/api/chapters/{chapter['id']}/", **student).json()
print("explanation written:", len(reading["explanation"]), "characters")

quiz = post("/api/quizzes/start/", {"chapter_id": chapter["id"]}, student).json()
print("quiz on the generated chapter:", len(quiz["questions"]), "questions")
assert len(quiz["questions"]) == 10

# 5. Declining takes the course away again.
declined = post(f"/api/invitations/{pending[0]['id']}/respond/", {"decision": "decline"}, student).json()
after = c.get(f"/api/courses/{course['id']}/", **student)
print("after declining, access is", after.status_code)
assert after.status_code == 403
print("FULL FLOW CHECKS PASSED")
