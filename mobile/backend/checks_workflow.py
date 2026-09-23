"""The instructor and admin workflow, end to end.

Run with: python manage.py shell < checks_workflow.py (after seed_demo, fresh database)

Covers: editing an extracted chapter, reordering, merging and splitting, resources and a
worked demonstration, submit for approval, an admin asking for changes then approving,
publishing, what a student can and cannot see at each step, rubrics and marking, progress
monitoring and the two downloads.
"""
import io
import json

from django.test import Client

c = Client()


def token(email, password):
    return c.post("/api/auth/login/", json.dumps({"email": email, "password": password}),
                  content_type="application/json").json()["access"]


def call(method, url, body=None, tok=None, files=False):
    headers = {"HTTP_AUTHORIZATION": f"Bearer {tok}"} if tok else {}
    if method == "GET":
        return c.get(url, **headers)
    if method == "DELETE":
        return c.delete(url, **headers)
    if files:
        return c.post(url, body, **headers)
    return getattr(c, method.lower())(url, json.dumps(body or {}),
                                      content_type="application/json", **headers)


admin = token("admin@mis3000.edu", "admin123")
faculty = token("faculty@mis3000.edu", "faculty123")
student = token("student@mis3000.edu", "student123")

course = call("GET", "/api/courses/", tok=faculty).json()[0]
detail = call("GET", f"/api/courses/{course['id']}/", tok=faculty).json()
book = detail["books"][0]
chapters = book["chapters"]
print("book:", book["title"], "|", len(chapters), "chapters")

# ---------------------------------------------------------------- editing what came out
first = chapters[0]
edited = call("PATCH", f"/api/chapters/{first['id']}/edit/",
              {"title": "Preparing Business Data (revised)"}, faculty).json()
print("edit title ->", edited["title"], "| status now", edited["status"])
assert edited["status"] == "DRAFT", "editing published material must send it back to draft"

order = [chapters[1]["id"], chapters[0]["id"], chapters[2]["id"]]
call("POST", f"/api/books/{book['id']}/reorder/", {"order": order}, faculty)
after = call("GET", f"/api/courses/{course['id']}/", tok=faculty).json()["books"][0]["chapters"]
print("reordered ->", [ch["number"] for ch in after], [ch["title"][:26] for ch in after])
assert [ch["id"] for ch in after] == order

split = call("POST", f"/api/chapters/{after[0]['id']}/split/",
             {"at_module_number": 2, "title": "Split half"}, faculty)
print("split ->", split.status_code, "|",
      split.json()["kept"]["title"][:28], "+", split.json()["created"]["title"][:28])
assert split.status_code == 200

merged = call("POST", "/api/chapters/merge/",
              {"keep": split.json()["kept"]["id"], "merge": split.json()["created"]["id"]},
              faculty)
print("merged back ->", merged.status_code, "|", len(merged.json()["modules"]), "modules")
assert merged.status_code == 200

# --------------------------------------------------- resources and a step by step demo
module_id = merged.json()["modules"][0]["id"]
screenshot = io.BytesIO(b"\x89PNG\r\n\x1a\n fake screenshot bytes")
screenshot.name = "autosum.png"
resource = call("POST", "/api/resources/",
                {"module": module_id, "title": "AutoSum on the toolbar",
                 "caption": "The button sits under Editing on the Home tab.",
                 "kind": "IMAGE", "file": screenshot}, faculty, files=True)
print("resource ->", resource.status_code, "|", resource.json().get("title"))
assert resource.status_code == 201

demo = call("POST", "/api/demonstrations/", {
    "module": module_id,
    "title": "Totalling a column the way I do it in class",
    "summary": "Four steps from a raw column to a checked total.",
    "steps": [
        {"title": "Select the column", "instruction": "Click B2 and drag to B6.", "cell": "B2:B6"},
        {"title": "Press AutoSum", "instruction": "Home tab, Editing group.", "formula": "=SUM(B2:B6)"},
        {"title": "Check the range", "instruction": "Look at what Excel highlighted before you accept."},
        {"title": "Format it", "instruction": "Currency, two decimals, so it reads as money."},
    ],
}, faculty)
print("demonstration ->", demo.status_code, "|", demo.json().get("step_count"), "steps")
assert demo.status_code == 201 and demo.json()["step_count"] == 4

# ------------------------------------------------------- approval, then publishing
chapter_id = merged.json()["id"]
blocked = call("POST", f"/api/chapters/{chapter_id}/publish/", {}, faculty)
print("publishing a draft ->", blocked.status_code, "|", blocked.json()["detail"][:52])
assert blocked.status_code == 400

call("POST", f"/api/chapters/{chapter_id}/submit/", {"comment": "Ready for review."}, faculty)
queue = call("GET", "/api/admin/review/", tok=admin).json()
print("admin queue ->", [(row["course_code"], row["title"][:26], row["status"]) for row in queue])
assert any(row["id"] == chapter_id for row in queue)
quality = next(row for row in queue if row["id"] == chapter_id)["quality"]
print("quality read ->", quality["modules"], "modules,", quality["resources"], "resources,",
      quality["demonstrations"], "demonstrations, complete:", quality["complete"])

vague = call("POST", f"/api/admin/review/{chapter_id}/", {"decision": "request_changes"}, admin)
print("asking for changes with no comment ->", vague.status_code)
assert vague.status_code == 400

changes = call("POST", f"/api/admin/review/{chapter_id}/",
               {"decision": "request_changes", "comment": "Module 2 is too thin."}, admin).json()
print("changes requested ->", changes["status"], "|", changes["review_comment"])

student_view = call("GET", f"/api/chapters/{chapter_id}/", tok=student)
print("student reading while it is under review ->", student_view.status_code,
      "| status shown as", student_view.json()["status"])
assert student_view.status_code == 200

call("POST", f"/api/chapters/{chapter_id}/submit/", {}, faculty)
approved = call("POST", f"/api/admin/review/{chapter_id}/",
                {"decision": "approve", "comment": "Good now."}, admin).json()
print("approved ->", approved["status"])
published = call("POST", f"/api/chapters/{chapter_id}/publish/", {}, faculty).json()
print("published ->", published["status"])

now_visible = call("GET", f"/api/chapters/{chapter_id}/", tok=student)
print("student opening published ->", now_visible.status_code)
assert now_visible.status_code == 200

seen = call("GET", f"/api/courses/{course['id']}/", tok=student).json()["books"][0]["chapters"]
print("student sees", len(seen), "of", len(after), "chapters, each labelled with its status:",
      sorted({ch["status"] for ch in seen}))
assert len(seen) == len(after)

# the student sees the instructor's screenshot and walkthrough beside the reading
their_resources = call("GET", f"/api/resources/?module={module_id}", tok=student).json()
their_demo = call("GET", f"/api/demonstrations/?module={module_id}", tok=student).json()
print("student sees", len(their_resources), "resource and", len(their_demo), "walkthrough")
assert their_resources and their_demo

# ------------------------------------------------------------- rubric and marking
rubric = call("POST", "/api/rubrics/", {
    "course": course["id"],
    "title": "Worksheet quality, 20 points",
    "criteria": [
        {"name": "Formula accuracy", "points": 8, "descriptor": "Right formula, right range."},
        {"name": "Formatting", "points": 6, "descriptor": "Formats match the meaning."},
        {"name": "Management sentence", "points": 6, "descriptor": "An action, with evidence."},
    ],
}, faculty).json()
print("rubric ->", rubric["title"], "worth", rubric["total_points"], "points")

students = call("GET", f"/api/courses/{course['id']}/students/", tok=faculty).json()
student_id = call("GET", "/api/auth/profile/", tok=student).json()["id"]
evaluation = call("POST", "/api/evaluations/", {
    "rubric": rubric["id"], "course": course["id"], "student": student_id,
    "scores": [
        {"name": "Formula accuracy", "points": 8, "awarded": 7},
        {"name": "Formatting", "points": 6, "awarded": 4, "note": "Mixed decimal places."},
        {"name": "Management sentence", "points": 6, "awarded": 6},
    ],
    "comment": "Strong formulas. Tidy the number formats before the graded case.",
}, faculty).json()
print("evaluation ->", evaluation["awarded"], "/", evaluation["possible"],
      f"({evaluation['percentage']}%)")
assert evaluation["awarded"] == 17

mine = call("GET", "/api/evaluations/", tok=student).json()
print("student sees their own marking:", len(mine), "|", mine[0]["comment"][:38])
assert len(mine) == 1

# ------------------------------------------------------------------ progress and downloads
progress = call("GET", f"/api/courses/{course['id']}/progress/", tok=faculty).json()
print("class progress ->", [(row["student_name"], row["attempts"], row["marks"])
                            for row in progress["students"]])
one = call("GET", f"/api/courses/{course['id']}/progress/{student_id}/", tok=faculty).json()
print("one student ->", one["student"]["name"], "| attempts", one["attempts_taken"],
      "| evaluations", len(one["evaluations"]))

chapter_file = call("GET", f"/api/chapters/{chapter_id}/download/", tok=faculty)
book_file = call("GET", f"/api/books/{book['id']}/download/", tok=faculty)
print("chapter download ->", chapter_file.status_code,
      chapter_file["Content-Disposition"].split("filename=")[-1],
      len(chapter_file.content), "bytes")
print("book download ->", book_file.status_code, len(book_file.content), "bytes")
assert chapter_file.status_code == 200 and book_file.status_code == 200

# ----------------------------------------------------------------------------- admin
dash = call("GET", "/api/admin/dashboard/", tok=admin).json()
print("admin dashboard ->", dash["totals"]["users"], "users,", dash["totals"]["courses"],
      "courses,", dash["totals"]["chapters"], "chapters,", dash["totals"]["resources"],
      "resources | by status", dash["chapters_by_status"])
people = call("GET", "/api/admin/users/", tok=admin).json()
print("admin users ->", [(p["name"], p["role"]) for p in people])
tree = call("GET", f"/api/admin/books/{book['id']}/", tok=admin).json()
print("book tree ->", tree["title"], "|", len(tree["chapters"]), "chapters with modules")
analytics = call("GET", "/api/admin/analytics/", tok=admin).json()
print("analytics ->", len(analytics["courses"]), "courses,", len(analytics["instructors"]),
      "instructors,", len(analytics["students"]), "students")

refused = call("GET", "/api/admin/users/", tok=faculty)
print("an instructor reaching for the admin API ->", refused.status_code)
assert refused.status_code == 403

changed = call("PATCH", f"/api/admin/users/{student_id}/", {"role": "FACULTY"}, admin).json()
print("role change ->", changed["role"])
call("PATCH", f"/api/admin/users/{student_id}/", {"role": "STUDENT"}, admin)
print("WORKFLOW CHECKS PASSED")

# --- the downloads a person actually clicks -------------------------------------------
whole = call("GET", f"/api/books/{book['id']}/download/", tok=faculty)
print("\nwhole book (faculty) ->", whole.status_code,
      whole["Content-Disposition"].split("filename=")[-1].strip(),
      len(whole.content), "bytes")
body = whole.content.decode()
print("contains every chapter heading:",
      all(f"Chapter {ch['number']}" in body for ch in after))
assert whole.status_code == 200 and "### Module" in body

student_copy = call("GET", f"/api/books/{book['id']}/download/", tok=student)
print("whole book (student) ->", student_copy.status_code,
      "| downloading the book belongs to the instructor")
assert student_copy.status_code == 403
print("DOWNLOAD CHECKS PASSED")
