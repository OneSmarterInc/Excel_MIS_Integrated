"""The thinnest case the user described: montage images and a list of topic names."""
import json
from django.test import Client
from django.core.files.uploadedfile import SimpleUploadedFile

c = Client()
auth = {"HTTP_AUTHORIZATION": "Bearer " + c.post(
    "/api/auth/login/", json.dumps({"email": "faculty@mis3000.edu", "password": "faculty123"}),
    content_type="application/json").json()["access"]}

course = c.post("/api/courses/", json.dumps({"code": "MIS4400", "name": "Systems Analysis Studio"}),
                content_type="application/json", **auth).json()

with open("/mnt/user-data/uploads/MIS3250_Week01_StudioPack_Montage.png", "rb") as handle:
    montage = SimpleUploadedFile("MIS3250_Week01_StudioPack_Montage.png", handle.read())

response = c.post(f"/api/courses/{course['id']}/generate-book/", {
    "files": [montage],
    "topics": ("Systems thinking and the analyst mindset\n"
               "Seeing the system before the features\n"
               "Turning features into analyst questions\n"
               "Need first, feature second\n"
               "Meeting the stakeholder\n"
               "Practising the analyst mindset"),
}, **auth)
book = response.json()
print(response.status_code, "|", book.get("extraction_note"))
print("chapters", book.get("chapter_count"), "modules", book.get("module_count"))
for chapter in book.get("chapters", []):
    print(f"  Ch {chapter['number']}: {chapter['title'][:50]} -> "
          f"{[m['title'][:28] for m in chapter['modules']]}")
assert response.status_code == 201 and book["module_count"] >= 3

# And with nothing at all, the platform says so rather than inventing a book.
empty = c.post(f"/api/courses/{course['id']}/generate-book/", {"topics": ""}, **auth)
print("nothing supplied ->", empty.status_code, empty.json().get("detail", "")[:60])
assert empty.status_code == 400
print("MONTAGE CHECKS PASSED")
