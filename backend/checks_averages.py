"""Prove the averages by hand: known scores in, known percentages out.

Run with: python manage.py shell < checks_averages.py (after seed_demo, on a fresh database)
"""
import json
from django.test import Client
from django.utils import timezone
from courses.models import Course, Enrollment
from accounts.models import User
from quizzes.models import Attempt

c = Client()
faculty = User.objects.get(email="faculty@mis3000.edu")
course = Course.objects.get(code="MIS3000")
asha = User.objects.get(email="student@mis3000.edu")
ravi = User.objects.create_user(email="ravi2@mis3000.edu", password="ravi12345",
                                name="Ravi Shah", role=User.Role.STUDENT)
Enrollment.objects.get_or_create(course=course, student=ravi)

def sat(student, score, total=10):
    Attempt.objects.create(student=student, course=course, scope=Attempt.Scope.CHAPTER,
                           score=score, total=total, percentage=round(score / total * 100, 1),
                           submitted_at=timezone.now())

sat(asha, 10)          # one perfect paper
sat(ravi, 4)           # two weaker ones from the same student
sat(ravi, 6)
Attempt.objects.create(student=ravi, course=course, scope=Attempt.Scope.CHAPTER,
                       score=0, total=10)   # started, never submitted: must not count

token = c.post("/api/auth/login/", json.dumps({"email": "faculty@mis3000.edu",
                                               "password": "faculty123"}),
               content_type="application/json").json()["access"]
auth = {"HTTP_AUTHORIZATION": f"Bearer {token}"}

dash = c.get("/api/faculty/dashboard/", **auth).json()
row = next(r for r in dash["courses"] if r["code"] == "MIS3000")
print("dashboard:", row["quizzes_taken"], "quizzes |", row["marks"], "|", row["average_percentage"], "%")
assert row["quizzes_taken"] == 3, row["quizzes_taken"]
assert row["marks"] == "20 / 30"
assert row["average_percentage"] == 66.7, row["average_percentage"]

perf = c.get(f"/api/courses/{course.id}/performance/", **auth).json()
print("class average:", perf["average_percentage"], "% on", perf["marks"],
      "across", perf["attempts"], "attempts")
print("per student:", [(s["student_name"], s["score"], s["total"], s["percentage"])
                       for s in perf["students"]])
assert perf["average_percentage"] == 66.7
assert [s["percentage"] for s in perf["students"]] == [100.0, 50.0]

stoken = c.post("/api/auth/login/", json.dumps({"email": "ravi2@mis3000.edu",
                                                "password": "ravi12345"}),
                content_type="application/json").json()["access"]
mine = c.get("/api/student/dashboard/", HTTP_AUTHORIZATION=f"Bearer {stoken}").json()
srow = mine["courses"][0]
print("student view:", srow["marks"], "|", srow["average_percentage"], "% | best",
      srow["best_percentage"], "%")
assert srow["marks"] == "10 / 20" and srow["average_percentage"] == 50.0
assert srow["best_percentage"] == 60.0

empty = Course.objects.create(code="MIS9999", name="Nothing taken yet", faculty=faculty)
dash = c.get("/api/faculty/dashboard/", **auth).json()
blank = next(r for r in dash["courses"] if r["code"] == "MIS9999")
print("a course nobody has sat:", blank["average_percentage"], "|", repr(blank["marks"]))
assert blank["average_percentage"] is None, "no attempts must read as no data, not as zero"
print("AVERAGE CHECKS PASSED")
