"""End to end check of the whole API. Run with: python manage.py shell < smoke_test.py"""
import json

from django.test import Client

client = Client()


def call(method, url, data=None, token=None, content_type="application/json"):
    headers = {"HTTP_AUTHORIZATION": f"Bearer {token}"} if token else {}
    if method == "GET":
        response = client.get(url, **headers)
    else:
        body = json.dumps(data) if content_type == "application/json" else data
        response = client.post(url, body, content_type=content_type, **headers)
    return response.status_code, (response.json() if response["Content-Type"].startswith("application/json") else {})


status, faculty = call("POST", "/api/auth/login/", {"email": "faculty@mis3000.edu", "password": "faculty123"})
print("faculty login", status, faculty["user"]["role"])
ftoken = faculty["access"]

status, student = call("POST", "/api/auth/login/", {"email": "student@mis3000.edu", "password": "student123"})
print("student login", status, student["user"]["name"])
stoken = student["access"]

status, dash = call("GET", "/api/faculty/dashboard/", token=ftoken)
print("faculty dashboard", status, dash["courses"][0]["code"], "students:", dash["courses"][0]["students_enrolled"])

status, codes = call("GET", "/api/course-codes/", token=stoken)
print("course codes", status, [c["code"] for c in codes])

status, joined = call("POST", "/api/join-course/", {"code": codes[0]["code"]}, token=stoken)
print("join course", status, joined["code"])

status, detail = call("GET", f"/api/courses/{joined['id']}/", token=stoken)
book = detail["books"][0]
print("book", book["title"], "chapters", book["chapter_count"], "modules", book["module_count"])
for chapter in book["chapters"]:
    print("  Chapter", chapter["number"], chapter["title"][:60],
          "->", [m["title"][:32] for m in chapter["modules"]])

chapter_id = book["chapters"][0]["id"]
module_id = book["chapters"][0]["modules"][0]["id"]

status, chapter = call("GET", f"/api/chapters/{chapter_id}/", token=stoken)
print("chapter explanation", status, len(chapter["explanation"]), "chars, raw text",
      len(chapter["raw_text"]), "chars")
print(chapter["explanation"][:220].replace("\n", " | "))

status, module = call("GET", f"/api/modules/{module_id}/", token=stoken)
print("module explanation", status, len(module["explanation"]), "chars")

status, quiz = call("POST", "/api/quizzes/start/", {"module_id": module_id}, token=stoken)
questions = quiz["questions"]
mcq = [q for q in questions if q["kind"] == "MCQ"]
business = [q for q in questions if q["kind"] == "BUSINESS"]
print("quiz started", status, "questions:", len(questions),
      "| multiple choice:", len(mcq), "| business:", len(business),
      "| unique prompts:", len({q["prompt"] for q in questions}),
      "| workbooks:", len({q["workbook"]["file"] for q in questions}))
print("sample question:", mcq[0]["prompt"][:90])
print("business question:", business[0]["prompt"][:150].replace("\n", " "))
print("business answer format:", business[0]["answer_format"], "| rows:",
      len(business[0]["workbook"]["rows"]))
assert all(q["workbook"]["rows"] for q in questions), "every question needs a worksheet"
assert "correct_index" not in questions[0], "answer key must not reach the student app"
assert all(not q["options"] for q in business), "business questions must carry no options"
assert all(q["options"] for q in mcq), "multiple choice questions need options"

answers = [{"question_id": q["id"], "selected_index": 0} for q in mcq]
answers += [{"question_id": q["id"], "typed_answer": "0"} for q in business]
status, result = call("POST", f"/api/quizzes/{quiz['attempt']['id']}/submit/", {"answers": answers}, token=stoken)
print("submitted", status, "correct", result["correct"], "wrong", result["wrong"],
      "percent", result["percentage"],
      "| mcq", result["multiple_choice"], "| business", result["business"])
print("explanation of Q1:", result["questions"][0]["explanation"][:110])

status, second = call("POST", "/api/quizzes/start/", {"module_id": module_id}, token=stoken)
overlap = len({q["prompt"] for q in second["questions"]} & {q["prompt"] for q in questions})
print("second attempt regenerated, identical prompts:", overlap)

status, sdash = call("GET", "/api/student/dashboard/", token=stoken)
print("student dashboard", status, sdash["courses"][0]["marks"], sdash["courses"][0]["average_percentage"])

status, fb = call("GET", f"/api/feedback/course/{joined['id']}/", token=stoken)
print("course feedback", status, fb["marks"], "|", fb["message"][:90])
print("weakest skills", [s["skill"] for s in fb["skills"][:3]])

status, posted = call("POST", "/api/feedback/", {"course": joined["id"], "rating": 4,
                                                 "comment": "The worksheet beside each question helps."}, token=stoken)
print("feedback posted", status)

status, perf = call("GET", f"/api/courses/{joined['id']}/performance/", token=ftoken)
print("faculty performance view", status, perf["students"])

status, preview = call("POST", "/api/quizzes/preview/", {"chapter_id": chapter_id}, token=ftoken)
print("faculty quiz preview", status, len(preview["questions"]), "questions with answers")
print("ALL CHECKS PASSED")

# --- business question marking -------------------------------------------------
from quizzes.business import grade_typed_answer  # noqa: E402

cases = [
    ("12480", "12480", "currency", 1, True),
    ("$12,480.00", "12480", "currency", 1, True),
    ("12,479.60", "12480", "currency", 1, True),
    ("11000", "12480", "currency", 1, False),
    ("18.5", "18.5", "percent", 0.2, True),
    ("0.185", "18.5", "percent", 0.2, True),
    ("21", "18.5", "percent", 0.2, False),
    ("West", "west", "text", 0, True),
    ("North", "West", "text", 0, False),
    ("", "12480", "currency", 1, False),
]
for typed, expected, fmt, tol, want in cases:
    got = grade_typed_answer(typed, expected, fmt, tol)
    assert got is want, f"marking failed on {typed!r} against {expected!r}: got {got}"
print(f"typed answer marking: {len(cases)}/{len(cases)} cases correct")

status, preview2 = call("POST", "/api/quizzes/preview/", {"chapter_id": chapter_id}, token=ftoken)
biz = [q for q in preview2["questions"] if q.get("kind") == "BUSINESS"]
print("faculty preview business questions:", len(biz),
      "| answers shown:", [q["expected_display"] for q in biz])
print("ALL CHECKS PASSED (10 question paper)")
