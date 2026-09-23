"""Access provision: granting a course by email, accepting it and being kept out until then.

Run with: python manage.py shell < checks_invitations.py (after seed_demo, on a fresh database)
"""
import json
from django.test import Client

c = Client()
def post(url, body, token=None, **extra):
    headers = {"HTTP_AUTHORIZATION": f"Bearer {token}"} if token else {}
    return c.post(url, json.dumps(body), content_type="application/json", **headers, **extra)
def get(url, token):
    return c.get(url, HTTP_AUTHORIZATION=f"Bearer {token}")

ft = post("/api/auth/login/", {"email": "faculty@mis3000.edu", "password": "faculty123"}).json()["access"]
course = get("/api/courses/", ft).json()[0]
print("course:", course["code"])

# A brand new student who has not been invited yet.
newcomer = post("/api/auth/register/", {"name": "Ravi Shah", "email": "ravi@mis3000.edu",
                                        "password": "ravi12345", "role": "STUDENT"}).json()
st = newcomer["access"]

blocked = post("/api/join-course/", {"code": course["code"]}, st)
print("join without an invitation:", blocked.status_code, "|", blocked.json().get("detail", "")[:80])
assert blocked.status_code == 403

visible = get("/api/course-codes/", st).json()
print("course codes visible to an uninvited student:", visible)

# Faculty grants access by email.
granted = post(f"/api/courses/{course['id']}/invitations/",
               {"emails": "ravi@mis3000.edu, someone.else@mis3000.edu"}, ft).json()
print("invitations after granting:", [(i["email"], i["status"]) for i in granted["invitations"]])

waiting = get("/api/my-invitations/", st).json()
print("student sees:", [(i["course_code"], i["course_name"][:24], i["status"]) for i in waiting])
assert waiting, "the invited student should see the course"

# Before accepting there is still no access.
detail = get(f"/api/courses/{course['id']}/", st)
print("reading the course before accepting:", detail.status_code)
assert detail.status_code == 403

accepted = post(f"/api/invitations/{waiting[0]['id']}/respond/", {"decision": "accept"}, st)
print("accept:", accepted.status_code, "|", accepted.json().get("status"))
print("courses after accepting:", [c["code"] for c in get("/api/courses/", st).json()])
assert get(f"/api/courses/{course['id']}/", st).status_code == 200

# Declining removes the invitation from the student's list without granting access.
second = post("/api/courses/", {"code": "MIS3100", "name": "Business Data Analysis"}, ft).json()
post(f"/api/courses/{second['id']}/invitations/", {"emails": "ravi@mis3000.edu"}, ft)
mine = [i for i in get("/api/my-invitations/", st).json() if i["course_code"] == second["code"]]
declined = post(f"/api/invitations/{mine[0]['id']}/respond/", {"decision": "decline"}, st)
print("decline:", declined.status_code, "|", declined.json().get("status"))
assert get(f"/api/courses/{second['id']}/", st).status_code == 403

roster = get(f"/api/courses/{course['id']}/invitations/", ft).json()
bad = post(f"/api/invitations/{mine[0]['id']}/respond/", {"decision": "maybe"}, st)
print("a decision that is neither:", bad.status_code)
assert bad.status_code == 400

print("faculty roster:", [(i["email"], i["status"]) for i in roster])
print("INVITATION FLOW CHECKS PASSED")
