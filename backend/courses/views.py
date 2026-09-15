import os
import re
import tempfile

from django.core.files.base import ContentFile
from django.db.models import Count, Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsFaculty, IsStudent

from .explain import build_explanation, ollama_status
from .extraction import detect_kind, extract
from .figure_store import collect_figures, describe_pending, save_figures, store_figures
from .generate import build_book, gather, read_source
from .models import Approval, Book, Chapter, Course, Enrollment, Invitation, Module
from .serializers import (
    BookSerializer,
    ChapterDetailSerializer,
    CourseDetailSerializer,
    CourseSerializer,
    EnrollmentSerializer,
    InvitationSerializer,
    ModuleDetailSerializer,
)


def percentage_of(scored, possible) -> float:
    """One definition of an average used everywhere: marks earned over marks available."""
    if not possible:
        return 0.0
    return round(scored / possible * 100, 1)


def visible_courses(user):
    if user.is_faculty:
        return Course.objects.filter(faculty=user)
    return Course.objects.filter(enrollments__student=user)


def can_read_course(user, course) -> bool:
    if user.is_faculty:
        return course.faculty_id == user.id
    return Enrollment.objects.filter(course=course, student=user).exists()



class CourseListView(APIView):
    """Faculty see the courses they created. Students see the ones they joined."""

    def get(self, request):
        courses = visible_courses(request.user).distinct()
        return Response(CourseSerializer(courses, many=True).data)

    def post(self, request):
        if not request.user.is_faculty:
            return Response({"detail": "Only faculty can create a course."},
                            status=status.HTTP_403_FORBIDDEN)
        serializer = CourseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        course = serializer.save(faculty=request.user)
        return Response(CourseSerializer(course).data, status=status.HTTP_201_CREATED)


class CourseDetailView(APIView):
    def get_object(self, request, pk):
        try:
            course = Course.objects.get(pk=pk)
        except Course.DoesNotExist:
            return None, Response({"detail": "That course no longer exists."},
                                  status=status.HTTP_404_NOT_FOUND)
        if not can_read_course(request.user, course):
            return None, Response({"detail": "You do not have access to this course."},
                                  status=status.HTTP_403_FORBIDDEN)
        return course, None

    def get(self, request, pk):
        course, error = self.get_object(request, pk)
        if error:
            return error
        return Response(CourseDetailSerializer(course, context={"request": request}).data)

    def patch(self, request, pk):
        course, error = self.get_object(request, pk)
        if error:
            return error
        if not request.user.is_faculty:
            return Response({"detail": "Only faculty can edit a course."},
                            status=status.HTTP_403_FORBIDDEN)
        serializer = CourseSerializer(course, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        course, error = self.get_object(request, pk)
        if error:
            return error
        if not request.user.is_faculty:
            return Response({"detail": "Only faculty can delete a course."},
                            status=status.HTTP_403_FORBIDDEN)
        course.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class BookUploadView(APIView):
    """Take the uploaded book apart into chapters and modules and store the real text."""

    permission_classes = [IsAuthenticated, IsFaculty]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        try:
            course = Course.objects.get(pk=pk, faculty=request.user)
        except Course.DoesNotExist:
            return Response({"detail": "Course not found for this faculty account."},
                            status=status.HTTP_404_NOT_FOUND)

        upload = request.FILES.get("file")
        if upload is None:
            return Response({"detail": "Attach a PDF, Word, PowerPoint or text file."},
                            status=status.HTTP_400_BAD_REQUEST)

        kind = detect_kind(upload.name)
        title = (request.data.get("title") or os.path.splitext(upload.name)[0])[:250]

        suffix = os.path.splitext(upload.name)[1] or ".txt"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as scratch:
            for chunk in upload.chunks():
                scratch.write(chunk)
            scratch_path = scratch.name
        try:
            result = extract(scratch_path, upload.name, course_hint=course.name)
        except Exception as exc:
            os.unlink(scratch_path)
            return Response(
                {"detail": f"The file could not be read: {exc}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not result["chapters"]:
            os.unlink(scratch_path)
            return Response(
                {"detail": "No readable text was found. A scanned image PDF needs OCR first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        upload.seek(0)
        book = Book.objects.create(
            course=course, title=title, file=upload, kind=kind,
            extraction_note=result["note"][:250],
            character_count=result["character_count"],
        )
        store_chapters(book, result["chapters"])

        # The same file is read a second time for its pictures, which is why the scratch
        # copy is only removed now. A book with no figures in it, or a reader that cannot
        # get at them, simply stores none and the upload is unaffected.
        pictures = store_figures(book, scratch_path, kind)
        os.unlink(scratch_path)
        if pictures:
            note = f"{book.extraction_note} {pictures} pictures were taken from the file."
            book.extraction_note = note.strip()[:250]
            book.save(update_fields=["extraction_note"])
        return Response(BookSerializer(book, context={"request": request}).data,
                        status=status.HTTP_201_CREATED)


def store_chapters(book, chapters):
    for chapter_data in chapters:
        chapter = Chapter.objects.create(
            book=book,
            number=chapter_data["number"],
            title=chapter_data["title"],
            raw_text=chapter_data["raw_text"],
        )
        for module_data in chapter_data["modules"]:
            Module.objects.create(
                chapter=chapter,
                number=module_data["number"],
                title=module_data["title"],
                raw_text=module_data["raw_text"],
            )


class BookGenerateView(APIView):
    """Build a book when the instructor has slides, a montage or only topic names.

    Files come in under `files`, and anything readable in them supplies the outline and
    the source material. Images carry no text, so their file names stand in as topics.
    A `topics` field can be sent on its own if there are no files at all.
    """

    permission_classes = [IsAuthenticated, IsFaculty]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        try:
            course = Course.objects.get(pk=pk, faculty=request.user)
        except Course.DoesNotExist:
            return Response({"detail": "Course not found for this faculty account."},
                            status=status.HTTP_404_NOT_FOUND)

        uploads = request.FILES.getlist("files")
        topics = request.data.get("topics", "")
        if not uploads and not topics.strip():
            return Response(
                {"detail": "Send slides, images or a list of topic names to build from."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sources, names, figures = [], [], []
        for upload in uploads:
            suffix = os.path.splitext(upload.name)[1] or ".txt"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as scratch:
                for chunk in upload.chunks():
                    scratch.write(chunk)
                scratch_path = scratch.name
            try:
                sources.append(read_source(scratch_path, upload.name))
                names.append(upload.name)
                # Slides carry their screenshots with them, so the pictures are taken here
                # while the scratch copy still exists and saved once the book is written.
                figures.extend(collect_figures(scratch_path, detect_kind(upload.name)))
            except Exception:
                pass
            finally:
                os.unlink(scratch_path)

        material = gather(sources, topics)
        if not material["headings"]:
            return Response(
                {"detail": "Nothing readable came out of those files. Add a few topic names "
                           "and try again."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = build_book(course.name, material)
        title = (request.data.get("title") or f"{course.name} course book")[:250]
        written_by = "Ollama" if ollama_status()["running"] else "the built in writer"
        book = Book.objects.create(
            course=course,
            title=title,
            file=ContentFile(result["text"].encode(), name=f"{course.code}_generated.txt"),
            kind=Book.Kind.TXT,
            source=Book.Source.GENERATED,
            extraction_note=(
                f"Written by {written_by} from "
                + (
                    f"{len(names)} {'files' if len(names) != 1 else 'file'} you supplied: "
                    + ", ".join(names[:4])
                    if names
                    else "the topic list you typed"
                )
            )[:250],
            character_count=result["character_count"],
        )
        store_chapters(book, result["chapters"])
        save_figures(book, figures)
        return Response(BookSerializer(book, context={"request": request}).data,
                        status=status.HTTP_201_CREATED)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated, IsFaculty])
def delete_book(request, pk):
    try:
        book = Book.objects.get(pk=pk, course__faculty=request.user)
    except Book.DoesNotExist:
        return Response({"detail": "Book not found."}, status=status.HTTP_404_NOT_FOUND)
    book.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


def _explain(request, obj, kind, serializer_class):
    refresh = request.query_params.get("refresh") == "1"
    if refresh or not obj.explanation:
        obj.explanation = build_explanation(obj.title, obj.raw_text, kind)
        obj.explained_at = timezone.now()
        obj.save(update_fields=["explanation", "explained_at"])
    # Any picture in this section that has not been described yet is captioned now, with
    # the explanation above it for context. A few at a time, so the page still opens.
    describe_pending(obj, kind)
    return Response(serializer_class(obj, context={"request": request}).data)


class ChapterView(APIView):
    def get(self, request, pk):
        try:
            chapter = Chapter.objects.select_related("book__course").get(pk=pk)
        except Chapter.DoesNotExist:
            return Response({"detail": "Chapter not found."}, status=status.HTTP_404_NOT_FOUND)
        if not can_read_course(request.user, chapter.book.course):
            return Response({"detail": "You do not have access to this chapter."},
                            status=status.HTTP_403_FORBIDDEN)
        return _explain(request, chapter, "chapter", ChapterDetailSerializer)


class ModuleView(APIView):
    def get(self, request, pk):
        try:
            module = Module.objects.select_related("chapter__book__course").get(pk=pk)
        except Module.DoesNotExist:
            return Response({"detail": "Module not found."}, status=status.HTTP_404_NOT_FOUND)
        if not can_read_course(request.user, module.chapter.book.course):
            return Response({"detail": "You do not have access to this module."},
                            status=status.HTTP_403_FORBIDDEN)
        return _explain(request, module, "module", ModuleDetailSerializer)


@api_view(["GET"])
def ai_status(request):
    """Lets the app say plainly whether the local model is writing the explanations."""
    status_payload = ollama_status()
    status_payload["writer"] = "Ollama" if status_payload["running"] else "Built in writer"
    return Response(status_payload)


@api_view(["GET"])
def course_codes(request):
    """Fills the course code dropdown in the student app."""
    joined = set(
        Enrollment.objects.filter(student=request.user).values_list("course_id", flat=True)
    )
    invited = set(
        Invitation.objects.filter(email__iexact=request.user.email)
        .values_list("course_id", flat=True)
    )
    data = [
        {
            "id": course.id,
            "code": course.code,
            "name": course.name,
            "faculty_name": course.faculty.name,
            "joined": course.id in joined,
        }
        for course in Course.objects.select_related("faculty").filter(id__in=invited)
    ]
    return Response(data)


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsStudent])
def join_course(request):
    code = (request.data.get("code") or "").strip().upper()
    if not code:
        return Response({"detail": "Pick a course code first."},
                        status=status.HTTP_400_BAD_REQUEST)
    try:
        course = Course.objects.get(code=code)
    except Course.DoesNotExist:
        return Response({"detail": f"No course is registered under {code}."},
                        status=status.HTTP_404_NOT_FOUND)
    invitation = Invitation.objects.filter(
        course=course, email__iexact=request.user.email
    ).first()
    if invitation is None:
        return Response(
            {"detail": f"{course.code} has not been opened to your email address. Ask your "
                       "instructor to add you, then accept it under Courses provided."},
            status=status.HTTP_403_FORBIDDEN,
        )
    Enrollment.objects.get_or_create(course=course, student=request.user)
    if invitation.status != Invitation.Status.ACCEPTED:
        invitation.status = Invitation.Status.ACCEPTED
        invitation.responded_at = timezone.now()
        invitation.save(update_fields=["status", "responded_at"])
    return Response(CourseSerializer(course).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsFaculty])
def course_students(request, pk):
    enrollments = Enrollment.objects.filter(
        course_id=pk, course__faculty=request.user
    ).select_related("student")
    return Response(EnrollmentSerializer(enrollments, many=True).data)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated, IsFaculty])
def course_invitations(request, pk):
    """Faculty naming who may take a course, and seeing who has accepted."""
    try:
        course = Course.objects.get(pk=pk, faculty=request.user)
    except Course.DoesNotExist:
        return Response({"detail": "Course not found for this faculty account."}, status=404)

    if request.method == "POST":
        raw = request.data.get("emails", "")
        if isinstance(raw, list):
            candidates = raw
        else:
            candidates = re.split(r"[\s,;]+", str(raw))
        added, already, bad = [], [], []
        for candidate in candidates:
            email = candidate.strip().lower()
            if not email:
                continue
            if "@" not in email or "." not in email.split("@")[-1]:
                bad.append(email)
                continue
            invitation, created = Invitation.objects.get_or_create(
                course=course, email=email, defaults={"invited_by": request.user}
            )
            (added if created else already).append(email)
        return Response({
            "added": added, "already_invited": already, "not_an_email": bad,
            "invitations": InvitationSerializer(course.invitations.all(), many=True).data,
        }, status=201 if added else 200)

    return Response(InvitationSerializer(course.invitations.all(), many=True).data)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated, IsFaculty])
def delete_invitation(request, pk):
    try:
        invitation = Invitation.objects.get(pk=pk, course__faculty=request.user)
    except Invitation.DoesNotExist:
        return Response({"detail": "Invitation not found."}, status=404)
    Enrollment.objects.filter(course=invitation.course, student__email=invitation.email).delete()
    invitation.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsStudent])
def my_invitations(request):
    """The courses a student has been given access to, waiting to be accepted."""
    invitations = Invitation.objects.filter(
        email__iexact=request.user.email
    ).select_related("course", "course__faculty")
    return Response(InvitationSerializer(invitations, many=True).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsStudent])
def respond_to_invitation(request, pk):
    try:
        invitation = Invitation.objects.get(pk=pk, email__iexact=request.user.email)
    except Invitation.DoesNotExist:
        return Response({"detail": "That invitation is not yours."}, status=404)

    # The decision has to be said out loud. Defaulting a malformed request to accept would
    # enrol somebody who never pressed anything.
    decision = str(request.data.get("decision") or request.data.get("action") or "").lower()
    if decision not in ("accept", "decline"):
        return Response({"detail": 'Send decision as either "accept" or "decline".'}, status=400)
    if decision == "accept":
        Enrollment.objects.get_or_create(course=invitation.course, student=request.user)
        invitation.status = Invitation.Status.ACCEPTED
    else:
        Enrollment.objects.filter(course=invitation.course, student=request.user).delete()
        invitation.status = Invitation.Status.DECLINED
    invitation.responded_at = timezone.now()
    invitation.save(update_fields=["status", "responded_at"])
    return Response(InvitationSerializer(invitation).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsFaculty])
def faculty_dashboard(request):
    from quizzes.models import Attempt

    rows = []
    courses = Course.objects.filter(faculty=request.user).annotate(
        students=Count("enrollments", distinct=True)
    )
    marks_scored = marks_possible = 0
    for course in courses:
        attempts = Attempt.objects.filter(course=course, submitted_at__isnull=False)
        summary = attempts.aggregate(taken=Count("id"), scored=Sum("score"), possible=Sum("total"))
        taken = summary["taken"] or 0
        scored = summary["scored"] or 0
        possible = summary["possible"] or 0
        marks_scored += scored
        marks_possible += possible
        rows.append({
            "course_id": course.id,
            "code": course.code,
            "name": course.name,
            "students_enrolled": course.students,
            "quizzes_taken": taken,
            # An average over marks, not an average of averages, so a seven mark paper and a
            # ten mark paper carry their true weight. None until somebody has actually sat one.
            "average_percentage": percentage_of(scored, possible) if taken else None,
            "marks": f"{scored} / {possible}" if taken else "",
            "books": course.books.count(),
            "chapters": Chapter.objects.filter(book__course=course).count(),
            "modules": Module.objects.filter(chapter__book__course=course).count(),
        })
    taken_total = sum(r["quizzes_taken"] for r in rows)
    totals = {
        "courses": len(rows),
        "students": sum(r["students_enrolled"] for r in rows),
        "quizzes_taken": taken_total,
        "average_percentage": percentage_of(marks_scored, marks_possible) if taken_total else None,
        "marks": f"{marks_scored} / {marks_possible}" if taken_total else "",
    }
    return Response({"totals": totals, "courses": rows})


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsStudent])
def student_dashboard(request):
    from quizzes.models import Attempt

    rows = []
    marks_scored = marks_possible = 0
    for enrollment in Enrollment.objects.filter(student=request.user).select_related("course"):
        course = enrollment.course
        attempts = Attempt.objects.filter(
            course=course, student=request.user, submitted_at__isnull=False
        )
        summary = attempts.aggregate(taken=Count("id"), scored=Sum("score"), possible=Sum("total"))
        taken = summary["taken"] or 0
        scored = summary["scored"] or 0
        possible = summary["possible"] or 0
        best = attempts.order_by("-percentage").first()
        marks_scored += scored
        marks_possible += possible
        rows.append({
            "course_id": course.id,
            "code": course.code,
            "name": course.name,
            "faculty_name": course.faculty.name,
            "quizzes_taken": taken,
            "average_percentage": percentage_of(scored, possible) if taken else None,
            "best_percentage": round(best.percentage, 1) if best else None,
            "marks": f"{scored} / {possible}" if taken else "",
        })
    taken_total = sum(r["quizzes_taken"] for r in rows)
    totals = {
        "courses": len(rows),
        "quizzes_taken": taken_total,
        "average_percentage": percentage_of(marks_scored, marks_possible) if taken_total else None,
        "marks": f"{marks_scored} / {marks_possible}" if taken_total else "",
    }
    return Response({"totals": totals, "courses": rows})
