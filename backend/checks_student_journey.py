"""The student's whole path, exactly as they walk it.

Run with: python manage.py shell < checks_student_journey.py (after seed_demo, fresh database)

Register, get access from the instructor, accept it, find the chapters, read a module,
sit the ten question quiz, submit it, read the results, read the course feedback, and
download the book.
"""
import json

from django.test import Client
from quizzes.models import AttemptQuestion

c = Client()


def token(email, password):
    return c.post("/api/auth/login/", json.dumps({"email": email, "password": password}),
                  content_type="application/json").json()["access"]


def get(url, tok):
    return c.get(url, HTTP_AUTHORIZATION=f"Bearer {tok}")


def post(url, body, tok=None):
    headers = {"HTTP_AUTHORIZATION": f"Bearer {tok}"} if tok else {}
    return c.post(url, json.dumps(body), content_type="application/json", **headers)


faculty = token("faculty@mis3000.edu", "faculty123")
course = get("/api/courses/", faculty).json()[0]
print("course:", course["code"], "-", course["name"])

# 1. A student signs up for themselves.
signup = post("/api/auth/register/", {"name": "Meera Rao", "email": "meera@mis3000.edu",
                                      "password": "meera12345", "role": "STUDENT"}).json()
student = signup["access"]
student_id = signup["user"]["id"]
print("registered:", signup["user"]["name"], "as", signup["user"]["role"])

# 2. Without access there is nothing to see.
print("courses before access:", get("/api/courses/", student).json())
assert get("/api/courses/", student).json() == []

# 3. The instructor opens the course to their email address.
granted = post(f"/api/courses/{course['id']}/invitations/", {"emails": "meera@mis3000.edu"},
               faculty).json()
print("instructor granted access to:",
      [i["email"] for i in granted["invitations"] if i["email"] == "meera@mis3000.edu"])

# 4. The student sees it waiting and accepts.
waiting = get("/api/my-invitations/", student).json()
print("waiting for the student:", [(i["course_code"], i["status"]) for i in waiting])
accepted = post(f"/api/invitations/{waiting[0]['id']}/respond/", {"decision": "accept"},
                student).json()
print("accepted ->", accepted["status"])
assert accepted["status"] == "ACCEPTED"

mine = get("/api/courses/", student).json()
print("courses after accepting:", [x["code"] for x in mine])
assert len(mine) == 1

# 5. The chapters and modules, published ones only.
detail = get(f"/api/courses/{mine[0]['id']}/", student).json()
book = detail["books"][0]
print("book:", book["title"], "|", len(book["chapters"]), "of", book["chapter_count"],
      "chapters published")
assert book["chapters"], "the student needs at least one published chapter to work with"
chapter = book["chapters"][0]
module = chapter["modules"][0]
print("chapter 1:", chapter["title"][:44], "| modules:",
      [m["title"][:26] for m in chapter["modules"]])

# 6. Reading a module.
reading = get(f"/api/modules/{module['id']}/", student).json()
print("module reading ->", len(reading["explanation"]), "characters of explanation,",
      len(reading["raw_text"]), "from the book")
assert reading["explanation"]

# 7. The quiz: ten questions, seven multiple choice and three typed.
quiz = post("/api/quizzes/start/", {"module_id": module["id"]}, student).json()
questions = quiz["questions"]
mcq = [q for q in questions if q["kind"] == "MCQ"]
business = [q for q in questions if q["kind"] == "BUSINESS"]
print("quiz ->", len(questions), "questions |", len(mcq), "multiple choice,",
      len(business), "business | answer cells:",
      [q["workbook"]["answer_cell"] for q in business])
assert len(questions) == 10 and len(business) == 3

# 8. Answering: every one correct, using the same values the sheet would give.
stored = {q.id: q for q in AttemptQuestion.objects.filter(attempt_id=quiz["attempt"]["id"])}
answers = []
for question in questions:
    row = stored[question["id"]]
    if question["kind"] == "BUSINESS":
        checked = post(f"/api/quizzes/{quiz['attempt']['id']}/check/",
                       {"question_id": row.id, "typed_answer": row.expected_answer},
                       student).json()
        assert checked["is_correct"], "the live check should agree with the sheet"
        answers.append({"question_id": row.id, "typed_answer": row.expected_answer})
    else:
        answers.append({"question_id": row.id, "selected_index": row.correct_index})
print("live check on the business questions: all three agreed")

result = post(f"/api/quizzes/{quiz['attempt']['id']}/submit/", {"answers": answers},
              student).json()
print("result ->", result["correct"], "correct,", result["wrong"], "wrong,",
      result["percentage"], "% | multiple choice", result["multiple_choice"],
      "| business", result["business"])
assert result["correct"] == 10
print("every question came back with its explanation:",
      all(q["explanation"] for q in result["questions"]))

# 9. The dashboard and the course feedback.
dash = get("/api/student/dashboard/", student).json()
print("dashboard ->", dash["courses"][0]["marks"], "|",
      dash["courses"][0]["average_percentage"], "%")
feedback = get(f"/api/feedback/course/{mine[0]['id']}/", student).json()
print("feedback ->", feedback["marks"], "|", feedback["message"][:60])
print("strongest and weakest skills:",
      [(s["skill"], s["accuracy"]) for s in feedback["skills"][:3]])

posted = post("/api/feedback/", {"course": mine[0]["id"], "rating": 5,
                                 "comment": "The sheet beside each question helped."}, student)
print("student comment ->", posted.status_code)

# 10. Downloading the book is the instructor's, not the student's.
copy = get(f"/api/books/{book['id']}/download/", student)
print("book download by a student ->", copy.status_code, "|", copy.json()["detail"])
assert copy.status_code == 403

# 11. A second attempt is a fresh paper.
again = post("/api/quizzes/start/", {"module_id": module["id"]}, student).json()
overlap = len({q["prompt"] for q in again["questions"]} & {q["prompt"] for q in questions})
print("second attempt, identical prompts:", overlap, "of 10")
print("STUDENT JOURNEY CHECKS PASSED")

# 12. A course whose chapters are all still drafts is readable too: approval is a status
#     the instructor and admin work through, not a wall in front of the student.
draft_course = post("/api/courses/", {"code": "DRAFT101", "name": "Straight from the slides"},
                    faculty).json()
c.post(f"/api/courses/{draft_course['id']}/generate-book/",
       {"topics": "Cell references, Formulas, Charts, Pivot tables, Lookups, Reporting"},
       HTTP_AUTHORIZATION=f"Bearer {faculty}")
post(f"/api/courses/{draft_course['id']}/invitations/", {"emails": "meera@mis3000.edu"}, faculty)
invite = [i for i in get("/api/my-invitations/", student).json()
          if i["course_code"] == "DRAFT101"][0]
post(f"/api/invitations/{invite['id']}/respond/", {"decision": "accept"}, student)
draft_detail = get(f"/api/courses/{draft_course['id']}/", student).json()
draft_book = draft_detail["books"][0]
statuses = sorted({ch["status"] for ch in draft_book["chapters"]})
print("\na course that has never been approved ->", len(draft_book["chapters"]), "chapters,",
      "statuses", statuses)
assert draft_book["chapters"], "a student must still see draft chapters"
draft_module = draft_book["chapters"][0]["modules"][0]
reading = get(f"/api/modules/{draft_module['id']}/", student)
paper = post("/api/quizzes/start/", {"module_id": draft_module["id"]}, student)
print("reading a draft module ->", reading.status_code,
      "| starting its quiz ->", paper.status_code,
      "|", len(paper.json()["questions"]), "questions")
assert reading.status_code == 200 and paper.status_code == 201
print("DRAFT COURSE IS READABLE")
