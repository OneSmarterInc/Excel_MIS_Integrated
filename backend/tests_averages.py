"""Averages must be marks over marks available, not an average of percentages."""
import json
from django.test import Client
from django.utils import timezone
from accounts.models import User
from courses.models import Course, Enrollment, Invitation
from quizzes.models import Attempt

c = Client()
faculty = User.objects.get(email="faculty@mis3000.edu")
student, _ = User.objects.get_or_create(
    email="avg.student@wright.edu", defaults={"name": "Average Tester", "role": "STUDENT"})
student.set_password("avg12345")
student.save()

course, _ = Course.objects.get_or_create(
    code="AVG101", defaults={"name": "Averages test course", "faculty": faculty})
empty, _ = Course.objects.get_or_create(
    code="AVG102", defaults={"name": "Nobody has sat this one", "faculty": faculty})
Invitation.objects.get_or_create(course=course, email=student.email,
                                 defaults={"invited_by": faculty})
Enrollment.objects.get_or_create(course=course, student=student)
Attempt.objects.filter(course=course).delete()

# One ten mark paper at 60 percent and one four mark paper at 0 percent.
Attempt.objects.create(student=student, course=course, scope="CHAPTER",
                       score=6, total=10, percentage=60.0, submitted_at=timezone.now())
Attempt.objects.create(student=student, course=course, scope="CHAPTER",
                       score=0, total=4, percentage=0.0, submitted_at=timezone.now())

token = c.post("/api/auth/login/", json.dumps({"email": "faculty@mis3000.edu", "password": "faculty123"}),
               content_type="application/json").json()["access"]
fa = {"HTTP_AUTHORIZATION": f"Bearer {token}"}

dash = c.get("/api/faculty/dashboard/", **fa).json()
row = [r for r in dash["courses"] if r["code"] == "AVG101"][0]
blank = [r for r in dash["courses"] if r["code"] == "AVG102"][0]
print("marks", row["marks"], "-> course average", row["average_percentage"], "%")
print("averaging the two percentages instead would give", round((60 + 0) / 2, 1), "%")
print("course nobody has sat ->", blank["average_percentage"], repr(blank["marks"]))
assert row["average_percentage"] == 42.9, row["average_percentage"]
assert blank["average_percentage"] is None

perf = c.get(f"/api/courses/{course.id}/performance/", **fa).json()
print("class average", perf["average_percentage"], "% on", perf["marks"], "over",
      perf["attempts"], "attempts")
assert perf["average_percentage"] == 42.9
assert perf["students"][0]["percentage"] == 42.9

stoken = c.post("/api/auth/login/", json.dumps({"email": student.email, "password": "avg12345"}),
                content_type="application/json").json()["access"]
sdash = c.get("/api/student/dashboard/", HTTP_AUTHORIZATION=f"Bearer {stoken}").json()
mine = [r for r in sdash["courses"] if r["code"] == "AVG101"][0]
print("student sees", mine["marks"], "->", mine["average_percentage"], "%, best",
      mine["best_percentage"], "%")
assert mine["average_percentage"] == 42.9 and mine["best_percentage"] == 60.0
print("AVERAGE CHECKS PASSED: course average, class average and student average all agree")
