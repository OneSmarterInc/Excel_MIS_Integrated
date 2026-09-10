from django.conf import settings
from django.db import models


class Course(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    faculty = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="courses_taught"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.code} - {self.name}"

    def save(self, *args, **kwargs):
        self.code = self.code.strip().upper()
        super().save(*args, **kwargs)


class Enrollment(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollments")
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="enrollments"
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("course", "student")
        ordering = ["-joined_at"]

    def __str__(self):
        return f"{self.student.email} in {self.course.code}"


class Invitation(models.Model):
    """A faculty member naming the students who may take a course.

    The invitation is held against the email address, so it can be sent before the
    student has an account. Accepting it is what creates the enrolment.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Waiting for the student"
        ACCEPTED = "ACCEPTED", "Accepted"
        DECLINED = "DECLINED", "Declined"

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="invitations")
    email = models.EmailField()
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="invitations_sent"
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("course", "email")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.email} invited to {self.course.code} ({self.status})"

    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()
        super().save(*args, **kwargs)


class Book(models.Model):
    class Source(models.TextChoices):
        UPLOADED = "UPLOADED", "Uploaded by the instructor"
        GENERATED = "GENERATED", "Generated from slides or images"

    class Kind(models.TextChoices):
        PDF = "pdf", "PDF"
        DOCX = "docx", "Word"
        PPTX = "pptx", "PowerPoint"
        TXT = "txt", "Text"

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="books")
    title = models.CharField(max_length=250)
    file = models.FileField(upload_to="books/")
    kind = models.CharField(max_length=8, choices=Kind.choices)
    source = models.CharField(max_length=10, choices=Source.choices, default=Source.UPLOADED)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    extraction_note = models.CharField(max_length=250, blank=True)
    character_count = models.IntegerField(default=0)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.title


class Approval(models.TextChoices):
    """Where a piece of course material stands on its way to the students.

    Draft is the instructor's own workspace. Under review sits with an admin. Changes
    requested comes back with a comment. Approved means an admin is satisfied, and the
    instructor is the one who then publishes it, so nothing reaches a student by accident.
    """

    DRAFT = "DRAFT", "Draft"
    UNDER_REVIEW = "UNDER_REVIEW", "Under review"
    CHANGES = "CHANGES", "Changes requested"
    APPROVED = "APPROVED", "Approved"
    PUBLISHED = "PUBLISHED", "Published"


class Chapter(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="chapters")
    number = models.IntegerField()
    title = models.CharField(max_length=250)
    # The text exactly as it was pulled out of the uploaded file.
    raw_text = models.TextField(blank=True)
    explanation = models.TextField(blank=True)
    explained_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=14, choices=Approval.choices, default=Approval.DRAFT)
    review_comment = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["number"]
        unique_together = ("book", "number")

    def __str__(self):
        return f"Chapter {self.number}: {self.title}"

    @property
    def is_published(self):
        return self.status == Approval.PUBLISHED


class Module(models.Model):
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name="modules")
    number = models.IntegerField()
    title = models.CharField(max_length=250)
    raw_text = models.TextField(blank=True)
    explanation = models.TextField(blank=True)
    explained_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=14, choices=Approval.choices, default=Approval.DRAFT)
    review_comment = models.TextField(blank=True)

    class Meta:
        ordering = ["number"]
        unique_together = ("chapter", "number")

    def __str__(self):
        return f"Module {self.chapter.number}.{self.number}: {self.title}"


class ReviewNote(models.Model):
    """The trail of what an admin asked for and what the instructor did about it."""

    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name="review_notes")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="review_notes"
    )
    action = models.CharField(max_length=20)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} on {self.chapter}"


class Resource(models.Model):
    """A screenshot, handout or link the instructor puts beside a chapter or a module.

    Students see it in the same place they read the explanation, which is the point: a
    reference screenshot is only useful next to the text it refers to.
    """

    class Kind(models.TextChoices):
        IMAGE = "IMAGE", "Image"
        FILE = "FILE", "File"
        LINK = "LINK", "Link"

    chapter = models.ForeignKey(
        Chapter, null=True, blank=True, on_delete=models.CASCADE, related_name="resources"
    )
    module = models.ForeignKey(
        Module, null=True, blank=True, on_delete=models.CASCADE, related_name="resources"
    )
    title = models.CharField(max_length=200)
    caption = models.TextField(blank=True)
    kind = models.CharField(max_length=6, choices=Kind.choices, default=Kind.IMAGE)
    file = models.FileField(upload_to="resources/", blank=True)
    url = models.URLField(blank=True)
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="resources"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return self.title


class Demonstration(models.Model):
    """A worked walkthrough the instructor records for a chapter or module.

    The steps are held as a list of {title, instruction, cell, formula} so the app can show
    them in order beside the sheet, the way the instructor would at the front of the room.
    """

    chapter = models.ForeignKey(
        Chapter, null=True, blank=True, on_delete=models.CASCADE, related_name="demonstrations"
    )
    module = models.ForeignKey(
        Module, null=True, blank=True, on_delete=models.CASCADE, related_name="demonstrations"
    )
    title = models.CharField(max_length=200)
    summary = models.TextField(blank=True)
    steps = models.JSONField(default=list)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="demonstrations",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return self.title


class Rubric(models.Model):
    """An instructor's own marking scheme, with criteria they wrote themselves."""

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="rubrics")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    # [{"name": "Formula accuracy", "points": 5, "descriptor": "..."}]
    criteria = models.JSONField(default=list)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="rubrics"
    )
    # The rubric the progress screen scores this course against. One per course.
    tracks_progress = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.course.code})"

    @property
    def total_points(self):
        return sum(int(item.get("points", 0) or 0) for item in self.criteria)


class Evaluation(models.Model):
    """One student marked against one rubric, plus the instructor's written feedback."""

    rubric = models.ForeignKey(
        Rubric, null=True, blank=True, on_delete=models.SET_NULL, related_name="evaluations"
    )
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="evaluations")
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="evaluations"
    )
    assessor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="evaluations_given",
    )
    # [{"name": "Formula accuracy", "points": 5, "awarded": 4, "note": "..."}]
    scores = models.JSONField(default=list)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.student.email} on {self.course.code}"

    @property
    def awarded(self):
        return sum(float(item.get("awarded", 0) or 0) for item in self.scores)

    @property
    def possible(self):
        return sum(float(item.get("points", 0) or 0) for item in self.scores)
