<<<<<<< HEAD
from django.db import models
from rest_framework import serializers

from .models import Book, BookImage, Chapter, Course, Enrollment, Invitation, Module


class BookImageSerializer(serializers.ModelSerializer):
    """A picture taken out of the book, with the address the app can actually load."""

    file_url = serializers.SerializerMethodField()
    label = serializers.CharField(read_only=True)

    class Meta:
        model = BookImage
        fields = ["id", "label", "page", "order", "width", "height", "caption",
                  "file_url", "described_at"]

    def get_file_url(self, obj):
        if not obj.file:
            return ""
        request = self.context.get("request")
        return request.build_absolute_uri(obj.file.url) if request else obj.file.url
=======
from rest_framework import serializers

from .models import Book, Chapter, Course, Enrollment, Invitation, Module
>>>>>>> origin/main


class ModuleBriefSerializer(serializers.ModelSerializer):
    has_explanation = serializers.SerializerMethodField()

    class Meta:
        model = Module
        fields = ["id", "number", "title", "has_explanation"]

    def get_has_explanation(self, obj):
        return bool(obj.explanation)


class ChapterBriefSerializer(serializers.ModelSerializer):
    modules = ModuleBriefSerializer(many=True, read_only=True)
    has_explanation = serializers.SerializerMethodField()

    class Meta:
        model = Chapter
        fields = ["id", "number", "title", "status", "review_comment", "published_at",
                  "has_explanation", "modules"]

    def get_has_explanation(self, obj):
        return bool(obj.explanation)


class ChapterDetailSerializer(serializers.ModelSerializer):
    modules = ModuleBriefSerializer(many=True, read_only=True)
    book_title = serializers.CharField(source="book.title", read_only=True)
    book_id = serializers.IntegerField(source="book.id", read_only=True)
    course_id = serializers.IntegerField(source="book.course_id", read_only=True)
<<<<<<< HEAD
    images = serializers.SerializerMethodField()
=======
>>>>>>> origin/main

    class Meta:
        model = Chapter
        fields = [
            "id", "number", "title", "raw_text", "explanation", "status",
            "review_comment", "published_at", "explained_at", "book_title",
<<<<<<< HEAD
            "book_id", "course_id", "modules", "images",
        ]

    def get_images(self, obj):
        """Everything from this chapter, including what sits inside its modules.

        Reading a whole chapter should show every figure printed in it. Opening one
        module shows only that module's own, which is handled below.
        """
        images = BookImage.objects.filter(
            models.Q(chapter=obj) | models.Q(module__chapter=obj)
        ).distinct()
        return BookImageSerializer(images, many=True, context=self.context).data

=======
            "book_id", "course_id", "modules",
        ]

>>>>>>> origin/main

class ModuleDetailSerializer(serializers.ModelSerializer):
    chapter_number = serializers.IntegerField(source="chapter.number", read_only=True)
    chapter_title = serializers.CharField(source="chapter.title", read_only=True)
    course_id = serializers.IntegerField(source="chapter.book.course_id", read_only=True)
<<<<<<< HEAD
    images = BookImageSerializer(many=True, read_only=True)
=======
>>>>>>> origin/main

    class Meta:
        model = Module
        fields = [
            "id", "number", "title", "raw_text", "explanation", "explained_at",
<<<<<<< HEAD
            "chapter_number", "chapter_title", "course_id", "images",
=======
            "chapter_number", "chapter_title", "course_id",
>>>>>>> origin/main
        ]


class BookSerializer(serializers.ModelSerializer):
    chapters = serializers.SerializerMethodField()
    chapter_count = serializers.SerializerMethodField()
    module_count = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = [
            "id", "title", "kind", "source", "uploaded_at", "extraction_note",
            "character_count", "chapter_count", "module_count", "chapters",
        ]

    def get_chapters(self, obj):
        """Everyone on the course sees every chapter.

        Approval is tracked on each chapter and shown as a status, but it does not hold
        the reading back: a student can work through the material while an admin is still
        looking at it.
        """
        return ChapterBriefSerializer(obj.chapters.all(), many=True).data

    def get_chapter_count(self, obj):
        return obj.chapters.count()

    def get_module_count(self, obj):
        return Module.objects.filter(chapter__book=obj).count()


class CourseSerializer(serializers.ModelSerializer):
    faculty_name = serializers.CharField(source="faculty.name", read_only=True)
    student_count = serializers.SerializerMethodField()
    book_count = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            "id", "code", "name", "description", "faculty_name",
            "student_count", "book_count", "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_student_count(self, obj):
        return obj.enrollments.count()

    def get_book_count(self, obj):
        return obj.books.count()

    def validate_code(self, value):
        value = value.strip().upper()
        if len(value) < 3:
            raise serializers.ValidationError("A course code needs at least three characters.")
        queryset = Course.objects.filter(code=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError("That course code is already in use.")
        return value


class CourseDetailSerializer(CourseSerializer):
    books = BookSerializer(many=True, read_only=True)

    class Meta(CourseSerializer.Meta):
        fields = CourseSerializer.Meta.fields + ["books"]


class InvitationSerializer(serializers.ModelSerializer):
    course_code = serializers.CharField(source="course.code", read_only=True)
    course_name = serializers.CharField(source="course.name", read_only=True)
    faculty_name = serializers.CharField(source="course.faculty.name", read_only=True)
    student_name = serializers.SerializerMethodField()

    class Meta:
        model = Invitation
        fields = ["id", "course", "course_code", "course_name", "faculty_name",
                  "email", "status", "student_name", "created_at", "responded_at"]
        read_only_fields = ["id", "status", "created_at", "responded_at"]

    def get_student_name(self, obj):
        from accounts.models import User

        user = User.objects.filter(email=obj.email).first()
        return user.name if user else ""


class EnrollmentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.name", read_only=True)
    student_email = serializers.CharField(source="student.email", read_only=True)

    class Meta:
        model = Enrollment
        fields = ["id", "student_name", "student_email", "joined_at"]
