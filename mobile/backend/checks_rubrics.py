"""The rubric an instructor sets up, and progress scored against it.

Run with: python manage.py shell < checks_rubrics.py (after seed_demo, fresh database)
"""
import json

from django.test import Client
from quizzes.models import AttemptQuestion

c = Client()


def tok(email, password):
    return c.post("/api/auth/login/", json.dumps({"email": email, "password": password}),
                  content_type="application/json").json()["access"]


def post(url, body, t):
    return c.post(url, json.dumps(body), content_type="application/json",
                  HTTP_AUTHORIZATION=f"Bearer {t}")


def patch(url, body, t):
    return c.patch(url, json.dumps(body), content_type="application/json",
                   HTTP_AUTHORIZATION=f"Bearer {t}")


def get(url, t):
    return c.get(url, HTTP_AUTHORIZATION=f"Bearer {t}")


faculty = tok("faculty@mis3000.edu", "faculty123")
student = tok("student@mis3000.edu", "student123")
course = get("/api/courses/", faculty).json()[0]
book = get(f"/api/courses/{course['id']}/", faculty).json()["books"][0]
module = book["chapters"][0]["modules"][0]
student_id = get("/api/auth/profile/", student).json()["id"]

# 1. The standard terms are there to start from.
catalogue = get("/api/rubrics/catalogue/", faculty).json()["terms"]
print("standard terms:")
for term in catalogue:
    print(f"   {term['name']:26} importance {term['points']:>2}  ({term['source']})")
assert len(catalogue) >= 6
assert {t["source"] for t in catalogue} == {"measured", "judged"}

# 2. The instructor only sets importance, and adds one term of their own.
chosen = [
    {"key": "quiz_accuracy", "points": 12},
    {"key": "applied_analysis", "points": 10},
    {"key": "coverage", "points": 4},
    {"key": "recommendation", "points": 8},
    {"name": "Turned work in on time", "points": 3, "descriptor": "My own term."},
]
rubric = post("/api/rubrics/", {"course": course["id"], "title": "MIS 3000 marking",
                                "criteria": chosen}, faculty).json()
print("\nrubric ->", rubric["title"], "worth", rubric["total_points"], "points")
for item in rubric["criteria"]:
    print(f"   {item['name']:26} {item['points']:>2}  {item['source']}")
assert rubric["total_points"] == 37
names = {item["name"] for item in rubric["criteria"]}
assert "Quiz accuracy" in names, "a standard term fills in its own name and description"
assert "Turned work in on time" in names, "an instructor's own term is kept"
assert next(i for i in rubric["criteria"] if i["name"] == "Turned work in on time")[
    "source"] == "judged", "the platform cannot measure a term it has never heard of"

# 3. Editing it: change an importance, drop a term, add another.
edited = patch(f"/api/rubrics/{rubric['id']}/", {"criteria": [
    {"key": "quiz_accuracy", "points": 20},
    {"key": "applied_analysis", "points": 10},
    {"key": "coverage", "points": 4},
    {"key": "recommendation", "points": 8},
    {"name": "Turned work in on time", "points": 3},
    {"name": "Helped the group", "points": 5},
]}, faculty).json()
print("\nafter editing ->", edited["total_points"], "points across",
      len(edited["criteria"]), "terms")
assert edited["total_points"] == 50

# 4. A rubric with nothing weighted is refused.
empty = post("/api/rubrics/", {"course": course["id"], "title": "Nothing counts",
                               "criteria": [{"key": "coverage", "points": 0}]}, faculty)
print("a rubric where everything is worth zero ->", empty.status_code)
assert empty.status_code == 400

# 5. Progress before the student has done anything.
progress = get(f"/api/courses/{course['id']}/progress/", faculty).json()
row = next(r for r in progress["students"] if r["student_id"] == student_id)
print("\ntracked against:", progress["rubric"]["title"])
print("before any work ->", row["rubric_progress"]["percentage"], "| waiting on",
      len(row["rubric_progress"]["waiting_on"]), "terms")
assert row["rubric_progress"]["percentage"] is None

# 6. The student sits a quiz and gets everything right.
paper = post("/api/quizzes/start/", {"module_id": module["id"]}, student).json()
stored = {q.id: q for q in AttemptQuestion.objects.filter(attempt_id=paper["attempt"]["id"])}
answers = []
for question in paper["questions"]:
    row_q = stored[question["id"]]
    answers.append({"question_id": row_q.id, "typed_answer": row_q.expected_answer}
                   if question["kind"] == "BUSINESS"
                   else {"question_id": row_q.id, "selected_index": row_q.correct_index})
post(f"/api/quizzes/{paper['attempt']['id']}/submit/", {"answers": answers}, student)

detail = get(f"/api/courses/{course['id']}/progress/{student_id}/", faculty).json()
scored = detail["rubric_progress"]
print("\nafter one perfect quiz, scored against the instructor's own rubric:")
for item in scored["criteria"]:
    shown = "not yet" if item["awarded"] is None else f"{item['awarded']}/{item['points']}"
    print(f"   {item['name']:26} {shown:>10}  {item['note']}")
print("   total ->", scored["awarded"], "/", scored["possible"],
      f"({scored['percentage']}%)")
assert scored["criteria"][0]["awarded"] == 20, "full marks on quiz accuracy"
assert any(item["awarded"] is None for item in scored["criteria"]), "judged terms wait"

# 7. Marking a judged term by hand brings it into the total.
post("/api/evaluations/", {
    "course": course["id"], "student": student_id, "rubric": rubric["id"],
    "scores": [{"name": "Management recommendation", "points": 8, "awarded": 6}],
    "comment": "The recommendation names an action but not what would change it.",
}, faculty)
after = get(f"/api/courses/{course['id']}/progress/{student_id}/", faculty).json()[
    "rubric_progress"]
marked = next(i for i in after["criteria"] if i["name"] == "Management recommendation")
print("\nafter marking the recommendation by hand ->", marked["awarded"], "/",
      marked["points"], "| total now", after["awarded"], "/", after["possible"])
assert marked["awarded"] == 6

# 8. Changing the rubric changes what progress means, with no new quiz taken.
patch(f"/api/rubrics/{rubric['id']}/", {"criteria": [
    {"key": "applied_analysis", "points": 30},
    {"key": "coverage", "points": 2},
]}, faculty)
reweighted = get(f"/api/courses/{course['id']}/progress/{student_id}/", faculty).json()[
    "rubric_progress"]
print("\nsame student, rubric reweighted ->", reweighted["awarded"], "/",
      reweighted["possible"], f"({reweighted['percentage']}%)",
      "| terms:", [i["name"] for i in reweighted["criteria"]])
assert len(reweighted["criteria"]) == 2
print("RUBRIC CHECKS PASSED")
