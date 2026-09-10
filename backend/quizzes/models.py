from django.conf import settings
from django.db import models

from courses.models import Chapter, Course, Module


class Attempt(models.Model):
    class Scope(models.TextChoices):
        CHAPTER = "CHAPTER", "Chapter"
        MODULE = "MODULE", "Module"

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="attempts"
    )
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="attempts")
    scope = models.CharField(max_length=8, choices=Scope.choices)
    chapter = models.ForeignKey(Chapter, null=True, blank=True, on_delete=models.CASCADE)
    module = models.ForeignKey(Module, null=True, blank=True, on_delete=models.CASCADE)
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    score = models.IntegerField(default=0)
    total = models.IntegerField(default=0)
    percentage = models.FloatField(default=0)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.student.email} {self.scope} {self.score}/{self.total}"

    @property
    def label(self):
        if self.scope == self.Scope.MODULE and self.module:
            return f"Module {self.module.chapter.number}.{self.module.number}: {self.module.title}"
        if self.chapter:
            return f"Chapter {self.chapter.number}: {self.chapter.title}"
        return "Quiz"


class AttemptQuestion(models.Model):
    class Kind(models.TextChoices):
        MCQ = "MCQ", "Multiple choice"
        BUSINESS = "BUSINESS", "Business question"

    attempt = models.ForeignKey(Attempt, on_delete=models.CASCADE, related_name="questions")
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.MCQ)
    order = models.IntegerField()
    prompt = models.TextField()
    options = models.JSONField(default=list)
    # Multiple choice questions use correct_index. Business questions leave it at -1
    # and are marked against expected_answer instead, within a tolerance.
    correct_index = models.IntegerField(default=-1)
    expected_answer = models.CharField(max_length=120, blank=True)
    answer_format = models.CharField(max_length=12, blank=True)
    tolerance = models.FloatField(default=0)
    steps = models.CharField(max_length=250, blank=True)
    explanation = models.TextField(blank=True)
    skill = models.CharField(max_length=80, blank=True)
    # The worksheet shown beside this question. Every question carries its own.
    workbook = models.JSONField(default=dict)
    selected_index = models.IntegerField(null=True, blank=True)
    typed_answer = models.CharField(max_length=120, blank=True)
    is_correct = models.BooleanField(default=False)

    class Meta:
        ordering = ["order"]
        unique_together = ("attempt", "order")

    def __str__(self):
        return f"Q{self.order} of attempt {self.attempt_id}"


class QuestionSet(models.Model):
    """One of the five fixed papers that exist for a chapter or a module.

    Generating a fresh paper for every student made the questions impossible for an
    instructor to review. Instead each section has five sets, built from the same list of
    skills in the same order so they are equal in difficulty, and differing only in the
    figures and the scenario. Students are handed the sets in turn, so the sixth student
    on a section sees set one again.
    """

    SETS_PER_SECTION = 5

    chapter = models.ForeignKey(
        Chapter, null=True, blank=True, on_delete=models.CASCADE, related_name="question_sets"
    )
    module = models.ForeignKey(
        Module, null=True, blank=True, on_delete=models.CASCADE, related_name="question_sets"
    )
    number = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["number"]
        unique_together = (("chapter", "module", "number"),)

    def __str__(self):
        return f"Set {self.number} for {self.module or self.chapter}"

    @property
    def label(self):
        return f"Set {self.number}"


class SetQuestion(models.Model):
    """A question inside a set. This is what an instructor edits, and what a student sits."""

    question_set = models.ForeignKey(
        QuestionSet, on_delete=models.CASCADE, related_name="questions"
    )
    order = models.IntegerField()
    kind = models.CharField(max_length=10, choices=AttemptQuestion.Kind.choices,
                            default=AttemptQuestion.Kind.MCQ)
    prompt = models.TextField()
    options = models.JSONField(default=list)
    correct_index = models.IntegerField(default=-1)
    expected_answer = models.CharField(max_length=120, blank=True)
    answer_format = models.CharField(max_length=12, blank=True)
    tolerance = models.FloatField(default=0)
    steps = models.CharField(max_length=250, blank=True)
    explanation = models.TextField(blank=True)
    skill = models.CharField(max_length=80, blank=True)
    workbook = models.JSONField(default=dict)
    edited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="edited_questions",
    )

    class Meta:
        ordering = ["order"]
        unique_together = ("question_set", "order")

    def __str__(self):
        return f"Q{self.order} of {self.question_set}"


class SetAssignment(models.Model):
    """Which set a student was handed for a section, kept so they always get the same one."""

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="set_assignments"
    )
    chapter = models.ForeignKey(Chapter, null=True, blank=True, on_delete=models.CASCADE)
    module = models.ForeignKey(Module, null=True, blank=True, on_delete=models.CASCADE)
    number = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (("student", "chapter", "module"),)

    def __str__(self):
        return f"{self.student.email} -> set {self.number}"
