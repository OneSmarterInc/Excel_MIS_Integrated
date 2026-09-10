from django.conf import settings
from django.db import models

from courses.models import Course


class Feedback(models.Model):
    """A student's own note on a course, kept beside the automatic performance feedback."""

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="feedback")
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="feedback"
    )
    rating = models.IntegerField(default=5)
    comment = models.TextField(blank=True)
    faculty_reply = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.student.email} on {self.course.code}"
