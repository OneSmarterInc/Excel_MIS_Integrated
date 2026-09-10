"""Serializers for the material an instructor adds and for what an admin reviews."""
from rest_framework import serializers

from .rubric_terms import normalise
from .models import (
    Chapter,
    Course,
    Demonstration,
    Evaluation,
    Module,
    Resource,
    ReviewNote,
    Rubric,
)


class ResourceSerializer(serializers.ModelSerializer):
    added_by_name = serializers.CharField(source="added_by.name", read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Resource
        fields = ["id", "chapter", "module", "title", "caption", "kind", "url",
                  "file", "file_url", "added_by_name", "created_at"]
        read_only_fields = ["id", "created_at", "added_by_name", "file_url"]

    def get_file_url(self, obj):
        if not obj.file:
            return ""
        request = self.context.get("request")
        return request.build_absolute_uri(obj.file.url) if request else obj.file.url


class DemonstrationSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.name", read_only=True)
    step_count = serializers.SerializerMethodField()

    class Meta:
        model = Demonstration
        fields = ["id", "chapter", "module", "title", "summary", "steps",
                  "created_by_name", "step_count", "created_at"]
        read_only_fields = ["id", "created_at", "created_by_name", "step_count"]

    def get_step_count(self, obj):
        return len(obj.steps or [])

    def validate_steps(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Steps must be a list.")
        cleaned = []
        for position, step in enumerate(value[:30], start=1):
            if isinstance(step, str):
                step = {"instruction": step}
            if not isinstance(step, dict):
                raise serializers.ValidationError("Each step is a line of instruction.")
            cleaned.append({
                "order": position,
                "title": str(step.get("title", ""))[:120],
                "instruction": str(step.get("instruction", ""))[:600],
                "cell": str(step.get("cell", ""))[:12],
                "formula": str(step.get("formula", ""))[:120],
            })
        return cleaned


class RubricSerializer(serializers.ModelSerializer):
    course_code = serializers.CharField(source="course.code", read_only=True)
    total_points = serializers.IntegerField(read_only=True)
    created_by_name = serializers.CharField(source="created_by.name", read_only=True)

    class Meta:
        model = Rubric
        fields = ["id", "course", "course_code", "title", "description", "criteria",
                  "total_points", "tracks_progress", "created_by_name", "created_at"]
        read_only_fields = ["id", "created_at", "total_points", "course_code", "created_by_name"]

    def validate_criteria(self, value):
        """Standard terms only need an importance; the rest is filled in from the catalogue."""
        if not isinstance(value, list) or not value:
            raise serializers.ValidationError("A rubric needs at least one term.")
        for item in value[:20]:
            if isinstance(item, dict) and not str(
                item.get("name") or item.get("key") or ""
            ).strip():
                raise serializers.ValidationError("Every term needs a name or a standard key.")
        cleaned = normalise(value[:20])
        if not cleaned:
            raise serializers.ValidationError("None of those terms could be read.")
        if not any(item["points"] > 0 for item in cleaned):
            raise serializers.ValidationError(
                "Give at least one term an importance above zero."
            )
        return cleaned


class EvaluationSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.name", read_only=True)
    student_email = serializers.CharField(source="student.email", read_only=True)
    assessor_name = serializers.CharField(source="assessor.name", read_only=True)
    rubric_title = serializers.CharField(source="rubric.title", read_only=True)
    awarded = serializers.FloatField(read_only=True)
    possible = serializers.FloatField(read_only=True)
    percentage = serializers.SerializerMethodField()

    class Meta:
        model = Evaluation
        fields = ["id", "rubric", "rubric_title", "course", "student", "student_name",
                  "student_email", "assessor_name", "scores", "comment", "awarded",
                  "possible", "percentage", "created_at"]
        read_only_fields = ["id", "created_at", "awarded", "possible", "percentage",
                            "student_name", "student_email", "assessor_name", "rubric_title"]

    def get_percentage(self, obj):
        return round(obj.awarded / obj.possible * 100, 1) if obj.possible else None


class ReviewNoteSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.name", read_only=True)

    class Meta:
        model = ReviewNote
        fields = ["id", "action", "comment", "author_name", "created_at"]


class ChapterReviewSerializer(serializers.ModelSerializer):
    """What an admin sees in the review queue: enough to judge without opening everything."""

    course_code = serializers.CharField(source="book.course.code", read_only=True)
    course_name = serializers.CharField(source="book.course.name", read_only=True)
    instructor = serializers.CharField(source="book.course.faculty.name", read_only=True)
    book_title = serializers.CharField(source="book.title", read_only=True)
    book_source = serializers.CharField(source="book.source", read_only=True)
    modules = serializers.SerializerMethodField()
    quality = serializers.SerializerMethodField()
    notes = ReviewNoteSerializer(source="review_notes", many=True, read_only=True)

    class Meta:
        model = Chapter
        fields = ["id", "number", "title", "status", "review_comment", "reviewed_at",
                  "published_at", "course_code", "course_name", "instructor", "book_title",
                  "book_source", "modules", "quality", "notes"]

    def get_modules(self, obj):
        return [
            {
                "id": module.id,
                "number": module.number,
                "title": module.title,
                "status": module.status,
                "characters": len(module.raw_text or ""),
                "has_explanation": bool(module.explanation),
                "resources": module.resources.count(),
                "demonstrations": module.demonstrations.count(),
            }
            for module in obj.modules.all()
        ]

    def get_quality(self, obj):
        """A blunt completeness read, so a reviewer knows where to look first."""
        modules = list(obj.modules.all())
        thin = [m.title for m in modules if len(m.raw_text or "") < 320]
        return {
            "modules": len(modules),
            "characters": len(obj.raw_text or ""),
            "thin_modules": thin,
            "has_explanation": bool(obj.explanation),
            "resources": obj.resources.count() + sum(m.resources.count() for m in modules),
            "demonstrations": (
                obj.demonstrations.count() + sum(m.demonstrations.count() for m in modules)
            ),
            "complete": bool(modules) and not thin,
        }


class AdminUserSerializer(serializers.ModelSerializer):
    courses_taught = serializers.SerializerMethodField()
    courses_joined = serializers.SerializerMethodField()

    class Meta:
        model = None  # set in __init__ to avoid importing the user model at module load
        fields = ["id", "name", "email", "role", "is_active", "date_joined",
                  "courses_taught", "courses_joined"]
        read_only_fields = ["id", "email", "date_joined"]

    def __init__(self, *args, **kwargs):
        from django.contrib.auth import get_user_model

        self.Meta.model = get_user_model()
        super().__init__(*args, **kwargs)

    def get_courses_taught(self, obj):
        return obj.courses_taught.count() if obj.is_faculty else 0

    def get_courses_joined(self, obj):
        return obj.enrollments.count() if obj.is_student else 0


class AdminCourseSerializer(serializers.ModelSerializer):
    instructor = serializers.CharField(source="faculty.name", read_only=True)
    instructor_email = serializers.CharField(source="faculty.email", read_only=True)
    students = serializers.SerializerMethodField()
    books = serializers.SerializerMethodField()
    chapters = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = ["id", "code", "name", "instructor", "instructor_email", "students",
                  "books", "chapters", "created_at"]

    def get_students(self, obj):
        return obj.enrollments.count()

    def get_books(self, obj):
        return obj.books.count()

    def get_chapters(self, obj):
        return Chapter.objects.filter(book__course=obj).count()
