"""Write a book from lecture slides, a montage image or a bare topic list.

Run with: python manage.py shell < checks_generation.py
Point MATERIALS at your own slides to try it on real material; the check still runs
without them, using the topic list on its own.
"""
import json
import os

from django.test import Client

MATERIALS = [
    "/mnt/user-data/uploads/MIS3250_Week01_Lecture.pptx",
    "/mnt/user-data/uploads/MIS3250_Week01_StudioPack.pptx",
    "/mnt/user-data/uploads/MIS3250_Week01_Lecture_Montage.png",
]

c = Client()
token = c.post("/api/auth/login/", json.dumps({"email": "faculty@mis3000.edu",
                                               "password": "faculty123"}),
               content_type="application/json").json()["access"]
auth = {"HTTP_AUTHORIZATION": f"Bearer {token}"}


def new_course(code, name):
    return c.post("/api/courses/", json.dumps({"code": code, "name": name}),
                  content_type="application/json", **auth).json()


present = [path for path in MATERIALS if os.path.exists(path)]
if present:
    course = new_course("GEN101", "Analysis and Design of Information Systems")
    handles = [open(path, "rb") for path in present]
    response = c.post(f"/api/courses/{course['id']}/generate-book/",
                      {"files": handles, "title": "Week 1 course book"}, **auth)
    for handle in handles:
        handle.close()
    book = response.json()
    print("from slides ->", response.status_code, "|", book["extraction_note"])
    print("chapters:", book["chapter_count"], "modules:", book["module_count"])
    for chapter in book["chapters"]:
        print(f"  Chapter {chapter['number']}: {chapter['title'][:58]}")
        for module in chapter["modules"]:
            print(f"      {chapter['number']}.{module['number']} {module['title'][:50]}")
    assert response.status_code == 201 and book["chapter_count"] >= 2
else:
    print("No slide files on this machine, so the slide path is skipped.")

course = new_course("GEN102", "Digital Strategy")
response = c.post(f"/api/courses/{course['id']}/generate-book/", {
    "topics": "Business models, Platform economics, Data as an asset, Cloud sourcing, "
              "Change management, Measuring digital value"}, **auth)
book = response.json()
print("\nfrom a topic list ->", response.status_code, "|", book["extraction_note"])
print("chapters:", book["chapter_count"], "modules:", book["module_count"])
titles = [chapter["title"] for chapter in book["chapters"]]
print("chapter titles:", titles)
assert response.status_code == 201
assert all(len(title) < 60 for title in titles), "a whole topic list must not become one title"

empty = new_course("GEN103", "Nothing supplied")
response = c.post(f"/api/courses/{empty['id']}/generate-book/", {}, **auth)
print("\nnothing supplied ->", response.status_code, "|", response.json().get("detail"))
assert response.status_code == 400
print("GENERATION CHECKS PASSED")
