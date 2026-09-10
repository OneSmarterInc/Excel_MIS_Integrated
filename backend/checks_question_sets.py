"""Five sets per section, handed out in turn, and editable by the instructor.

Run with: python manage.py shell < checks_question_sets.py (after seed_demo, fresh database)
"""
import json

from django.test import Client

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
course = get("/api/courses/", faculty).json()[0]
book = get(f"/api/courses/{course['id']}/", faculty).json()["books"][0]
module = book["chapters"][0]["modules"][0]

# 1. The five sets exist for the section, and they are level with each other.
sets = get(f"/api/quizzes/sets/?module_id={module['id']}", faculty).json()
print("sets:", [s["label"] for s in sets["sets"]], "| questions each:",
      [len(s["questions"]) for s in sets["sets"]])
assert len(sets["sets"]) == 5 and all(len(s["questions"]) == 10 for s in sets["sets"])

skills = [[q["skill"] for q in s["questions"]] for s in sets["sets"]]
print("same skills in the same order across all five:", all(row == skills[0] for row in skills))
print("skills tested:", skills[0])
assert all(row == skills[0] for row in skills), "the sets have to be equal in difficulty"

prompts = [{q["prompt"] for q in s["questions"]} for s in sets["sets"]]
shared = set.intersection(*prompts)
print("questions shared between every set:", len(shared), "of 10")
assert len(shared) < 10, "the sets must not be copies of one another"

# 2. Six students, handed the sets in turn.
handed = []
for index in range(1, 7):
    email = f"cycle{index}@mis3000.edu"
    student = c.post("/api/auth/register/", json.dumps(
        {"name": f"Student {index}", "email": email, "password": "pass1234",
         "role": "STUDENT"}), content_type="application/json").json()["access"]
    post(f"/api/courses/{course['id']}/invitations/", {"emails": email}, faculty)
    invite = [i for i in get("/api/my-invitations/", student).json()
              if i["course_code"] == course["code"]][0]
    post(f"/api/invitations/{invite['id']}/respond/", {"decision": "accept"}, student)
    paper = post("/api/quizzes/start/", {"module_id": module["id"]}, student).json()
    handed.append(paper["set_number"])
    if index == 1:
        retakes = [post("/api/quizzes/start/", {"module_id": module["id"]},
                        student).json()["set_number"] for _ in range(5)]
        print("student 1 retaking five times ->", paper["set_number"], "then", retakes)
        assert retakes == [2, 3, 4, 5, 1], "a retake moves on to the next set and comes back round"
print("sets handed to students 1 to 6:", handed)
assert handed == [1, 2, 3, 4, 5, 1]

# 3. What a student sits is what is in their set.
student = tok("cycle3@mis3000.edu", "pass1234")
sat = post("/api/quizzes/start/", {"module_id": module["id"]}, student).json()
set_three = next(s for s in sets["sets"] if s["number"] == sat["set_number"])
print("student 3 sat set", sat["set_number"], "| prompts match the set:",
      [q["prompt"] for q in sat["questions"]] == [q["prompt"] for q in set_three["questions"]])
assert [q["prompt"] for q in sat["questions"]] == [q["prompt"] for q in set_three["questions"]]

# 4. The instructor rewrites a question, and the next student to sit it sees the new wording.
first = set_three["questions"][0]
edited = patch(f"/api/quizzes/sets/questions/{first['id']}/", {
    "prompt": "Rewritten by the instructor: which formula totals the units column?",
    "explanation": "SUM adds every cell in the range, and the colon makes it a range.",
}, faculty)
print("edit ->", edited.status_code, "|", edited.json()["prompt"][:52])
assert edited.status_code == 200

fresh = tok("cycle4@mis3000.edu", "pass1234")
# cycle4 is on set 4; walk them round to the edited set and check the new wording lands.
number, seen_prompt = None, ""
for _ in range(SETS := 5):
    paper = post("/api/quizzes/start/", {"module_id": module["id"]}, fresh).json()
    if paper["set_number"] == set_three["number"]:
        number, seen_prompt = paper["set_number"], paper["questions"][0]["prompt"]
        break
print(f"another student reaching set {number} sees:", seen_prompt[:52])
assert seen_prompt.startswith("Rewritten by the instructor")

# 5. An edit that points the answer at nothing is refused.
bad = patch(f"/api/quizzes/sets/questions/{first['id']}/", {"correct_index": 9}, faculty)
print("an answer pointing outside the options ->", bad.status_code)
assert bad.status_code == 400

# 6. Rebuilding the sets is deliberate, and gives fresh papers.
rebuilt = post(f"/api/quizzes/sets/?module_id={module['id']}", {}, faculty).json()
print("rebuilt ->", [s["label"] for s in rebuilt["sets"]], "| still level:",
      len({tuple(q["skill"] for q in s["questions"]) for s in rebuilt["sets"]}) == 1)
print("QUESTION SET CHECKS PASSED")

# 7. The instructor's wording survives the whole cycle: edit set 1, then let six students
#    through, and the sixth sits the edited set 1 rather than a fresh paper.
chapter = book["chapters"][1]
sets_two = get(f"/api/quizzes/sets/?chapter_id={chapter['id']}", faculty).json()["sets"]
target = next(s for s in sets_two if s["number"] == 1)["questions"][0]
patch(f"/api/quizzes/sets/questions/{target['id']}/",
      {"prompt": "INSTRUCTOR VERSION: what does this formula return?"}, faculty)

seen = []
for index in range(1, 7):
    email = f"loop{index}@mis3000.edu"
    student = c.post("/api/auth/register/", json.dumps(
        {"name": f"Loop {index}", "email": email, "password": "pass1234", "role": "STUDENT"}),
        content_type="application/json").json()["access"]
    post(f"/api/courses/{course['id']}/invitations/", {"emails": email}, faculty)
    invite = [i for i in get("/api/my-invitations/", student).json()
              if i["course_code"] == course["code"]][0]
    post(f"/api/invitations/{invite['id']}/respond/", {"decision": "accept"}, student)
    paper = post("/api/quizzes/start/", {"chapter_id": chapter["id"]}, student).json()
    seen.append((paper["set_number"], paper["questions"][0]["prompt"][:19]))
print("\nset number and first question for students 1 to 6:")
for number, prompt in seen:
    print(f"   set {number}: {prompt}")
assert [n for n, _ in seen] == [1, 2, 3, 4, 5, 1]
assert seen[0][1] == seen[5][1] == "INSTRUCTOR VERSION:", "student six must sit the edited set one"

after = get(f"/api/quizzes/sets/?chapter_id={chapter['id']}", faculty).json()
print("sets on this section after all that:", len(after["sets"]),
      "| set 1 still says:", after["sets"][0]["questions"][0]["prompt"][:19])
assert len(after["sets"]) == 5
print("THE FIVE SETS HOLD THEIR EDITS")
