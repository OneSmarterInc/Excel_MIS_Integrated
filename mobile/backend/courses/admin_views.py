"""What an admin sees: the whole platform, and the queue of chapters waiting on a decision."""
from django.contrib.auth import get_user_model
from django.db.models import Avg, Count, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import IsAdminRole
from quizzes.models import Attempt, AttemptQuestion

from .models import (
    Approval,
    Book,
    Chapter,
    Course,
    Demonstration,
    Enrollment,
    Evaluation,
    Module,
    Resource,
    ReviewNote,
)
from .teaching_serializers import (
    AdminCourseSerializer,
    AdminUserSerializer,
    ChapterReviewSerializer,
)

User = get_user_model()
ADMIN = [IsAuthenticated, IsAdminRole]


@api_view(["GET"])
@permission_classes(ADMIN)
def dashboard(request):
    """Counts first, then the two things an admin actually has to act on."""
    submitted = Attempt.objects.filter(submitted_at__isnull=False)
    score = sum(attempt.score for attempt in submitted)
    total = sum(attempt.total for attempt in submitted)
    by_status = {
        row["status"]: row["n"]
        for row in Chapter.objects.values("status").annotate(n=Count("id"))
    }
    return Response({
        "totals": {
            "users": User.objects.count(),
            "students": User.objects.filter(role=User.Role.STUDENT).count(),
            "instructors": User.objects.filter(role=User.Role.FACULTY).count(),
            "admins": User.objects.filter(role=User.Role.ADMIN).count(),
            "courses": Course.objects.count(),
            "books": Book.objects.count(),
            "chapters": Chapter.objects.count(),
            "modules": Module.objects.count(),
            "resources": Resource.objects.count(),
            "demonstrations": Demonstration.objects.count(),
            "enrolments": Enrollment.objects.count(),
            "quiz_submissions": submitted.count(),
            "evaluations": Evaluation.objects.count(),
            "marks": f"{score} / {total}" if total else "",
            "average_percentage": round(score / total * 100, 1) if total else None,
        },
        "chapters_by_status": {
            key: by_status.get(key, 0)
            for key, _ in Approval.choices
        },
        "waiting_for_review": ChapterReviewSerializer(
            Chapter.objects.filter(status=Approval.UNDER_REVIEW)
            .select_related("book__course__faculty")[:20],
            many=True,
        ).data,
        "recent_courses": AdminCourseSerializer(
            Course.objects.select_related("faculty")[:8], many=True
        ).data,
    })


@api_view(["GET"])
@permission_classes(ADMIN)
def users(request):
    queryset = User.objects.all().order_by("-date_joined")
    role = request.query_params.get("role")
    if role:
        queryset = queryset.filter(role=role.upper())
    search = request.query_params.get("q")
    if search:
        queryset = queryset.filter(Q(name__icontains=search) | Q(email__icontains=search))
    return Response(AdminUserSerializer(queryset[:200], many=True).data)


@api_view(["PATCH", "DELETE"])
@permission_classes(ADMIN)
def user_detail(request, pk):
    try:
        person = User.objects.get(pk=pk)
    except User.DoesNotExist:
        return Response({"detail": "That account no longer exists."}, status=404)
    if person.id == request.user.id and request.method == "DELETE":
        return Response({"detail": "You cannot remove your own admin account."}, status=400)

    if request.method == "DELETE":
        person.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    role = request.data.get("role")
    if role:
        if role.upper() not in dict(User.Role.choices):
            return Response({"detail": "Role must be ADMIN, FACULTY or STUDENT."}, status=400)
        if person.id == request.user.id and role.upper() != User.Role.ADMIN:
            return Response({"detail": "You cannot take away your own admin role."}, status=400)
        person.role = role.upper()
    if "is_active" in request.data:
        person.is_active = bool(request.data["is_active"])
    if "name" in request.data:
        person.name = str(request.data["name"])[:150]
    person.save()
    return Response(AdminUserSerializer(person).data)


@api_view(["GET"])
@permission_classes(ADMIN)
def courses(request):
    queryset = Course.objects.select_related("faculty").order_by("-created_at")
    search = request.query_params.get("q")
    if search:
        queryset = queryset.filter(Q(code__icontains=search) | Q(name__icontains=search))
    return Response(AdminCourseSerializer(queryset[:200], many=True).data)


@api_view(["DELETE"])
@permission_classes(ADMIN)
def course_detail(request, pk):
    try:
        course = Course.objects.get(pk=pk)
    except Course.DoesNotExist:
        return Response({"detail": "That course no longer exists."}, status=404)
    course.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
@permission_classes(ADMIN)
def books(request):
    """Every uploaded or generated book with what came out of it."""
    rows = []
    queryset = Book.objects.select_related("course__faculty").order_by("-uploaded_at")
    course_id = request.query_params.get("course_id")
    if course_id:
        queryset = queryset.filter(course_id=course_id)
    for book in queryset[:100]:
        chapters = book.chapters.all()
        rows.append({
            "id": book.id,
            "title": book.title,
            "kind": book.kind,
            "source": book.source,
            "course_code": book.course.code,
            "course_name": book.course.name,
            "instructor": book.course.faculty.name,
            "uploaded_at": book.uploaded_at,
            "characters": book.character_count,
            "extraction_note": book.extraction_note,
            "chapters": chapters.count(),
            "modules": Module.objects.filter(chapter__book=book).count(),
            "published_chapters": chapters.filter(status=Approval.PUBLISHED).count(),
            "waiting": chapters.filter(status=Approval.UNDER_REVIEW).count(),
        })
    return Response(rows)


@api_view(["GET"])
@permission_classes(ADMIN)
def book_tree(request, pk):
    """The book, chapter and module hierarchy in one call, for the review screen."""
    try:
        book = Book.objects.select_related("course__faculty").get(pk=pk)
    except Book.DoesNotExist:
        return Response({"detail": "Book not found."}, status=404)
    return Response({
        "id": book.id,
        "title": book.title,
        "kind": book.kind,
        "source": book.source,
        "extraction_note": book.extraction_note,
        "course": {"id": book.course.id, "code": book.course.code, "name": book.course.name,
                   "instructor": book.course.faculty.name},
        "chapters": ChapterReviewSerializer(book.chapters.all(), many=True).data,
    })


@api_view(["GET"])
@permission_classes(ADMIN)
def review_queue(request):
    queryset = Chapter.objects.select_related("book__course__faculty")
    wanted = request.query_params.get("status", Approval.UNDER_REVIEW)
    if wanted != "ALL":
        queryset = queryset.filter(status=wanted.upper())
    return Response(ChapterReviewSerializer(queryset[:100], many=True).data)


@api_view(["POST"])
@permission_classes(ADMIN)
def review_chapter(request, pk):
    """Approve, ask for changes, or send it back as a draft, always with a comment."""
    try:
        chapter = Chapter.objects.select_related("book__course").get(pk=pk)
    except Chapter.DoesNotExist:
        return Response({"detail": "Chapter not found."}, status=404)

    decision = str(request.data.get("decision", "")).lower()
    comment = str(request.data.get("comment", ""))[:2000]
    mapping = {
        "approve": Approval.APPROVED,
        "request_changes": Approval.CHANGES,
        "reject": Approval.DRAFT,
    }
    if decision not in mapping:
        return Response(
            {"detail": 'Send decision as "approve", "request_changes" or "reject".'}, status=400
        )
    if decision != "approve" and not comment.strip():
        return Response(
            {"detail": "Say what needs to change, so the instructor knows what to fix."},
            status=400,
        )

    chapter.status = mapping[decision]
    chapter.review_comment = comment
    chapter.reviewed_at = timezone.now()
    if decision != "approve":
        chapter.published_at = None
    chapter.save(update_fields=["status", "review_comment", "reviewed_at", "published_at"])
    chapter.modules.update(status=mapping[decision])
    ReviewNote.objects.create(chapter=chapter, author=request.user,
                              action=decision.upper(), comment=comment)
    return Response(ChapterReviewSerializer(chapter).data)


@api_view(["GET"])
@permission_classes(ADMIN)
def analytics(request):
    """Where the platform is working and where it is not."""
    course_rows = []
    for course in Course.objects.select_related("faculty").annotate(
        students=Count("enrollments", distinct=True)
    ):
        attempts = Attempt.objects.filter(course=course, submitted_at__isnull=False)
        score = sum(attempt.score for attempt in attempts)
        total = sum(attempt.total for attempt in attempts)
        course_rows.append({
            "course_id": course.id,
            "code": course.code,
            "name": course.name,
            "instructor": course.faculty.name,
            "students": course.students,
            "attempts": attempts.count(),
            "average_percentage": round(score / total * 100, 1) if total else None,
            "published_chapters": Chapter.objects.filter(
                book__course=course, status=Approval.PUBLISHED
            ).count(),
            "chapters": Chapter.objects.filter(book__course=course).count(),
        })

    instructor_rows = []
    for instructor in User.objects.filter(role=User.Role.FACULTY):
        taught = Course.objects.filter(faculty=instructor)
        attempts = Attempt.objects.filter(course__in=taught, submitted_at__isnull=False)
        score = sum(attempt.score for attempt in attempts)
        total = sum(attempt.total for attempt in attempts)
        instructor_rows.append({
            "id": instructor.id,
            "name": instructor.name,
            "email": instructor.email,
            "courses": taught.count(),
            "students": Enrollment.objects.filter(course__in=taught).count(),
            "chapters_published": Chapter.objects.filter(
                book__course__in=taught, status=Approval.PUBLISHED
            ).count(),
            "chapters_waiting": Chapter.objects.filter(
                book__course__in=taught, status=Approval.UNDER_REVIEW
            ).count(),
            "average_percentage": round(score / total * 100, 1) if total else None,
        })

    student_rows = []
    for student in User.objects.filter(role=User.Role.STUDENT)[:200]:
        attempts = Attempt.objects.filter(student=student, submitted_at__isnull=False)
        score = sum(attempt.score for attempt in attempts)
        total = sum(attempt.total for attempt in attempts)
        student_rows.append({
            "id": student.id,
            "name": student.name,
            "email": student.email,
            "courses": Enrollment.objects.filter(student=student).count(),
            "attempts": attempts.count(),
            "marks": f"{score} / {total}" if total else "",
            "average_percentage": round(score / total * 100, 1) if total else None,
        })
    student_rows.sort(key=lambda row: (row["average_percentage"] is None,
                                       row["average_percentage"] or 0))

    module_rows = []
    for module in Module.objects.select_related("chapter__book__course")[:400]:
        attempts = Attempt.objects.filter(module=module, submitted_at__isnull=False)
        if not attempts:
            continue
        score = sum(attempt.score for attempt in attempts)
        total = sum(attempt.total for attempt in attempts)
        module_rows.append({
            "id": module.id,
            "title": module.title,
            "chapter": module.chapter.title,
            "course_code": module.chapter.book.course.code,
            "attempts": attempts.count(),
            "average_percentage": round(score / total * 100, 1) if total else None,
        })
    module_rows.sort(key=lambda row: row["average_percentage"] or 0)

    hardest: dict = {}
    for question in AttemptQuestion.objects.filter(attempt__submitted_at__isnull=False)[:4000]:
        row = hardest.setdefault(question.skill or "General",
                                 {"skill": question.skill, "asked": 0, "correct": 0})
        row["asked"] += 1
        row["correct"] += 1 if question.is_correct else 0
    for row in hardest.values():
        row["accuracy"] = round(row["correct"] / max(row["asked"], 1) * 100, 1)

    return Response({
        "courses": course_rows,
        "instructors": instructor_rows,
        "students": student_rows[:50],
        "modules": module_rows[:30],
        "skills": sorted(hardest.values(), key=lambda row: row["accuracy"]),
    })
