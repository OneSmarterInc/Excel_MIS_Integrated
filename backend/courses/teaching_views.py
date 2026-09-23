"""What an instructor does with a course after the chapters exist.

Editing and reshaping chapters, hanging resources and worked demonstrations off them,
writing a rubric and marking against it, watching a student's progress, sending the work
for approval and publishing it once an admin agrees, and downloading any of it.
"""
from django.db.models import Avg, Count, Max
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import IsFaculty

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
    Rubric,
)
from .rubric_terms import CATALOGUE, gather_facts, score_against
from .serializers import ChapterDetailSerializer, ModuleDetailSerializer
from .teaching_serializers import (
    DemonstrationSerializer,
    EvaluationSerializer,
    ResourceSerializer,
    RubricSerializer,
)
from .views import can_read_course


def owns(user, course):
    return user.is_authenticated and user.is_faculty and course.faculty_id == user.id


def chapter_for_editing(request, pk):
    try:
        chapter = Chapter.objects.select_related("book__course").get(pk=pk)
    except Chapter.DoesNotExist:
        return None, Response({"detail": "Chapter not found."}, status=404)
    if not owns(request.user, chapter.book.course):
        return None, Response({"detail": "This chapter belongs to another instructor."},
                              status=403)
    return chapter, None


def renumber(book):
    """Keep chapter numbers as 1, 2, 3 after a move, a merge or a removal."""
    for position, chapter in enumerate(book.chapters.order_by("number", "id"), start=1):
        if chapter.number != position:
            chapter.number = position
            chapter.save(update_fields=["number"])


def reopen(chapter, reason):
    """Any edit to approved or published material sends it back to draft.

    Students should never be reading something an admin approved and an instructor then
    quietly rewrote, so the edit costs the approval.
    """
    if chapter.status in (Approval.APPROVED, Approval.PUBLISHED):
        chapter.status = Approval.DRAFT
        chapter.published_at = None
        chapter.save(update_fields=["status", "published_at"])
        ReviewNote.objects.create(chapter=chapter, action="REOPENED", comment=reason)


# --------------------------------------------------------------------- editing chapters

@api_view(["PATCH", "DELETE"])
@permission_classes([IsAuthenticated, IsFaculty])
def edit_chapter(request, pk):
    chapter, error = chapter_for_editing(request, pk)
    if error:
        return error

    if request.method == "DELETE":
        book = chapter.book
        chapter.delete()
        renumber(book)
        return Response(status=status.HTTP_204_NO_CONTENT)

    for field in ("title", "raw_text", "explanation"):
        if field in request.data:
            setattr(chapter, field, request.data[field])
    chapter.save()
    reopen(chapter, "The instructor edited the chapter after it was approved.")
    return Response(ChapterDetailSerializer(chapter).data)


@api_view(["PATCH", "DELETE"])
@permission_classes([IsAuthenticated, IsFaculty])
def edit_module(request, pk):
    try:
        module = Module.objects.select_related("chapter__book__course").get(pk=pk)
    except Module.DoesNotExist:
        return Response({"detail": "Module not found."}, status=404)
    if not owns(request.user, module.chapter.book.course):
        return Response({"detail": "This module belongs to another instructor."}, status=403)

    if request.method == "DELETE":
        chapter = module.chapter
        module.delete()
        for position, remaining in enumerate(chapter.modules.order_by("number", "id"), start=1):
            if remaining.number != position:
                remaining.number = position
                remaining.save(update_fields=["number"])
        reopen(chapter, "The instructor removed a module after it was approved.")
        return Response(status=status.HTTP_204_NO_CONTENT)

    for field in ("title", "raw_text", "explanation"):
        if field in request.data:
            setattr(module, field, request.data[field])
    module.save()
    reopen(module.chapter, "The instructor edited a module after it was approved.")
    return Response(ModuleDetailSerializer(module).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsFaculty])
def reorder_chapters(request, pk):
    """Send the chapter ids in the order you want them."""
    try:
        book = Book.objects.select_related("course").get(pk=pk)
    except Book.DoesNotExist:
        return Response({"detail": "Book not found."}, status=404)
    if not owns(request.user, book.course):
        return Response({"detail": "This book belongs to another instructor."}, status=403)

    order = [int(value) for value in request.data.get("order", [])]
    chapters = {chapter.id: chapter for chapter in book.chapters.all()}
    if set(order) != set(chapters):
        return Response(
            {"detail": "Send every chapter id of this book exactly once."}, status=400
        )
    # Numbers are unique per book, so move them out of the way before writing the new order.
    for chapter in chapters.values():
        chapter.number += 1000
        chapter.save(update_fields=["number"])
    for position, chapter_id in enumerate(order, start=1):
        chapter = chapters[chapter_id]
        chapter.number = position
        chapter.save(update_fields=["number"])
    return Response({"order": order})


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsFaculty])
def merge_chapters(request):
    """Fold the second chapter into the first, modules and all."""
    first_id = request.data.get("keep")
    second_id = request.data.get("merge")
    keep, error = chapter_for_editing(request, first_id) if first_id else (None, None)
    if error:
        return error
    absorb, error = chapter_for_editing(request, second_id) if second_id else (None, None)
    if error:
        return error
    if not keep or not absorb or keep.id == absorb.id:
        return Response({"detail": "Send two different chapter ids as keep and merge."},
                        status=400)
    if keep.book_id != absorb.book_id:
        return Response({"detail": "Both chapters have to come from the same book."}, status=400)

    offset = keep.modules.count()
    for position, module in enumerate(absorb.modules.order_by("number"), start=1):
        module.chapter = keep
        module.number = offset + position
        module.save(update_fields=["chapter", "number"])
    for resource in absorb.resources.all():
        resource.chapter = keep
        resource.save(update_fields=["chapter"])
    keep.raw_text = f"{keep.raw_text}\n\n{absorb.raw_text}".strip()
    keep.title = request.data.get("title") or keep.title
    keep.explanation = ""
    keep.save()
    book = absorb.book
    absorb.delete()
    renumber(book)
    reopen(keep, "The instructor merged another chapter into this one.")
    return Response(ChapterDetailSerializer(keep).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsFaculty])
def split_chapter(request, pk):
    """Break a chapter in two at a module boundary."""
    chapter, error = chapter_for_editing(request, pk)
    if error:
        return error
    modules = list(chapter.modules.order_by("number"))
    try:
        at = int(request.data.get("at_module_number", 0))
    except (TypeError, ValueError):
        at = 0
    if not 2 <= at <= len(modules):
        return Response(
            {"detail": f"Give the module number to split at, between 2 and {len(modules)}."},
            status=400,
        )

    moving = [module for module in modules if module.number >= at]
    book = chapter.book

    # Shift all later chapters up by 1 to make room right after this chapter
    for later in book.chapters.filter(number__gt=chapter.number).order_by("-number"):
        later.number += 1
        later.save(update_fields=["number"])

    new_title = (request.data.get("title") or "").strip() or f"{chapter.title} (Part 2)"
    fresh = Chapter.objects.create(
        book=book,
        number=chapter.number + 1,
        title=new_title,
        raw_text="\n\n".join(module.raw_text for module in moving),
    )
    for position, module in enumerate(moving, start=1):
        module.chapter = fresh
        module.number = position
        module.save(update_fields=["chapter", "number"])

    kept_modules = [module for module in modules if module.number < at]
    for position, module in enumerate(kept_modules, start=1):
        if module.number != position:
            module.number = position
            module.save(update_fields=["number"])

    chapter.raw_text = "\n\n".join(module.raw_text for module in kept_modules)
    chapter.explanation = ""
    chapter.save(update_fields=["raw_text", "explanation"])
    renumber(book)
    chapter.refresh_from_db()
    fresh.refresh_from_db()

    reopen(chapter, "The instructor split this chapter.")
    notify(
        request.user,
        "Chapter split",
        f"Chapter '{chapter.title}' was split. Created Chapter {fresh.number}: '{fresh.title}'.",
        kind=Notification.Kind.SYSTEM,
    )
    return Response({
        "kept": ChapterDetailSerializer(chapter).data,
        "created": ChapterDetailSerializer(fresh).data,
    })


# ------------------------------------------------------------- approval and publishing

@api_view(["POST"])
@permission_classes([IsAuthenticated, IsFaculty])
def submit_chapter(request, pk):
    chapter, error = chapter_for_editing(request, pk)
    if error:
        return error
    if chapter.status == Approval.UNDER_REVIEW:
        return Response({"detail": "This chapter is already with an admin."}, status=400)
    chapter.status = Approval.UNDER_REVIEW
    chapter.review_comment = ""
    chapter.save(update_fields=["status", "review_comment"])
    chapter.modules.update(status=Approval.UNDER_REVIEW)
    ReviewNote.objects.create(chapter=chapter, author=request.user, action="SUBMITTED",
                              comment=request.data.get("comment", "")[:1000])

    from accounts.models import User
    for admin_user in User.objects.filter(role=User.Role.ADMIN):
        notify(
            admin_user,
            "Chapter submitted for review",
            f"{request.user.name} submitted Chapter {chapter.number}: '{chapter.title}' ({chapter.book.course.code}) for your approval.",
            kind=Notification.Kind.APPROVAL_REQUEST,
            sender=request.user,
        )

    return Response({"id": chapter.id, "status": chapter.status})


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsFaculty])
def publish_chapter(request, pk):
    chapter, error = chapter_for_editing(request, pk)
    if error:
        return error
    if chapter.status != Approval.APPROVED:
        return Response(
            {"detail": "An admin has to approve this chapter before it can be published."},
            status=400,
        )
    chapter.status = Approval.PUBLISHED
    chapter.published_at = timezone.now()
    chapter.save(update_fields=["status", "published_at"])
    chapter.modules.update(status=Approval.PUBLISHED)
    ReviewNote.objects.create(chapter=chapter, author=request.user, action="PUBLISHED")

    course = chapter.book.course
    for enrollment in course.enrollments.select_related("student"):
        notify(
            enrollment.student,
            "New chapter published",
            f"Chapter {chapter.number}: '{chapter.title}' is now published and open for you in {course.code}!",
            kind=Notification.Kind.PUBLISHED,
            sender=request.user,
        )

    return Response({"id": chapter.id, "status": chapter.status,
                     "published_at": chapter.published_at})


# ---------------------------------------------------------- resources and demonstrations

@api_view(["GET", "POST"])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def resources(request):
    """Screenshots and handouts, listed for readers and added by the instructor."""
    chapter_id = request.data.get("chapter") or request.query_params.get("chapter")
    module_id = request.data.get("module") or request.query_params.get("module")

    if request.method == "GET":
        queryset = Resource.objects.all()
        if module_id:
            queryset = queryset.filter(module_id=module_id)
        elif chapter_id:
            queryset = queryset.filter(chapter_id=chapter_id)
        else:
            return Response({"detail": "Ask for a chapter or a module."}, status=400)
        first = queryset.first()
        if first:
            course = (first.module.chapter.book.course if first.module
                      else first.chapter.book.course)
            if not can_read_course(request.user, course):
                return Response({"detail": "You do not have access to this course."}, status=403)
        return Response(
            ResourceSerializer(queryset, many=True, context={"request": request}).data
        )

    serializer = ResourceSerializer(data=request.data, context={"request": request})
    serializer.is_valid(raise_exception=True)
    target = serializer.validated_data.get("module") or serializer.validated_data.get("chapter")
    if target is None:
        return Response({"detail": "Attach the resource to a chapter or a module."}, status=400)
    course = (target.chapter.book.course if isinstance(target, Module)
              else target.book.course)
    if not owns(request.user, course):
        return Response({"detail": "Only the course instructor can add resources."}, status=403)
    resource = serializer.save(added_by=request.user)
    return Response(ResourceSerializer(resource, context={"request": request}).data, status=201)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated, IsFaculty])
def delete_resource(request, pk):
    try:
        resource = Resource.objects.get(pk=pk)
    except Resource.DoesNotExist:
        return Response({"detail": "Resource not found."}, status=404)
    course = (resource.module.chapter.book.course if resource.module
              else resource.chapter.book.course)
    if not owns(request.user, course):
        return Response({"detail": "This resource belongs to another course."}, status=403)
    resource.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET", "POST"])
def demonstrations(request):
    chapter_id = request.data.get("chapter") or request.query_params.get("chapter")
    module_id = request.data.get("module") or request.query_params.get("module")

    if request.method == "GET":
        queryset = Demonstration.objects.all()
        if module_id:
            queryset = queryset.filter(module_id=module_id)
        elif chapter_id:
            queryset = queryset.filter(chapter_id=chapter_id)
        else:
            return Response({"detail": "Ask for a chapter or a module."}, status=400)
        first = queryset.first()
        if first:
            course = (first.module.chapter.book.course if first.module
                      else first.chapter.book.course)
            if not can_read_course(request.user, course):
                return Response({"detail": "You do not have access to this course."}, status=403)
        return Response(DemonstrationSerializer(queryset, many=True).data)

    serializer = DemonstrationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    target = serializer.validated_data.get("module") or serializer.validated_data.get("chapter")
    if target is None:
        return Response({"detail": "Attach the walkthrough to a chapter or a module."},
                        status=400)
    course = (target.chapter.book.course if isinstance(target, Module) else target.book.course)
    if not owns(request.user, course):
        return Response({"detail": "Only the course instructor can add a walkthrough."},
                        status=403)
    demonstration = serializer.save(created_by=request.user)
    return Response(DemonstrationSerializer(demonstration).data, status=201)


@api_view(["PATCH", "DELETE"])
@permission_classes([IsAuthenticated, IsFaculty])
def edit_demonstration(request, pk):
    try:
        demonstration = Demonstration.objects.get(pk=pk)
    except Demonstration.DoesNotExist:
        return Response({"detail": "Walkthrough not found."}, status=404)
    course = (demonstration.module.chapter.book.course if demonstration.module
              else demonstration.chapter.book.course)
    if not owns(request.user, course):
        return Response({"detail": "This walkthrough belongs to another course."}, status=403)
    if request.method == "DELETE":
        demonstration.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    serializer = DemonstrationSerializer(demonstration, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


# --------------------------------------------------------------- rubrics and evaluation

@api_view(["GET"])
def rubric_catalogue(request):
    """The standard terms, with the importance each one carries by default."""
    return Response({
        "terms": CATALOGUE,
        "note": (
            "Set the importance of each term to suit your course. Measured terms are scored "
            "from what the student has done in the platform; judged terms wait for you."
        ),
    })


@api_view(["GET", "POST"])
def rubrics(request):
    if request.method == "POST":
        if not request.user.is_faculty:
            return Response({"detail": "Only an instructor can write a rubric."}, status=403)
        serializer = RubricSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not owns(request.user, serializer.validated_data["course"]):
            return Response({"detail": "That is not your course."}, status=403)
        rubric = serializer.save(created_by=request.user)
        if rubric.tracks_progress:
            Rubric.objects.filter(course=rubric.course).exclude(pk=rubric.pk).update(
                tracks_progress=False
            )
        return Response(RubricSerializer(rubric).data, status=201)

    queryset = Rubric.objects.select_related("course")
    if request.user.is_faculty:
        queryset = queryset.filter(course__faculty=request.user)
    else:
        queryset = queryset.filter(course__enrollments__student=request.user).distinct()
    course_id = request.query_params.get("course_id")
    if course_id:
        queryset = queryset.filter(course_id=course_id)
    return Response(RubricSerializer(queryset, many=True).data)


@api_view(["PATCH", "DELETE"])
@permission_classes([IsAuthenticated, IsFaculty])
def edit_rubric(request, pk):
    try:
        rubric = Rubric.objects.get(pk=pk, course__faculty=request.user)
    except Rubric.DoesNotExist:
        return Response({"detail": "Rubric not found."}, status=404)
    if request.method == "DELETE":
        rubric.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    serializer = RubricSerializer(rubric, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    updated = serializer.save()
    if updated.tracks_progress:
        Rubric.objects.filter(course=updated.course).exclude(pk=updated.pk).update(
            tracks_progress=False
        )
    return Response(RubricSerializer(updated).data)


@api_view(["GET", "POST"])
def evaluations(request):
    """Marking a student against a rubric, and the written feedback that goes with it."""
    if request.method == "POST":
        if not request.user.is_faculty:
            return Response({"detail": "Only an instructor can mark work."}, status=403)
        serializer = EvaluationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        course = serializer.validated_data["course"]
        if not owns(request.user, course):
            return Response({"detail": "That is not your course."}, status=403)
        student = serializer.validated_data["student"]
        if not Enrollment.objects.filter(course=course, student=student).exists():
            return Response({"detail": "That student has not joined this course."}, status=400)
        rubric = serializer.validated_data.get("rubric")
        scores = serializer.validated_data.get("scores") or []
        if rubric and not scores:
            # Marking against a rubric with no scores sent: start from the rubric itself.
            scores = [{"name": item["name"], "points": item["points"], "awarded": 0}
                      for item in rubric.criteria]
        evaluation = serializer.save(assessor=request.user, scores=scores)
        return Response(EvaluationSerializer(evaluation).data, status=201)

    queryset = Evaluation.objects.select_related("student", "course", "rubric")
    if request.user.is_faculty:
        queryset = queryset.filter(course__faculty=request.user)
    else:
        queryset = queryset.filter(student=request.user)
    for key, field in (("course_id", "course_id"), ("student_id", "student_id")):
        value = request.query_params.get(key)
        if value:
            queryset = queryset.filter(**{field: value})
    return Response(EvaluationSerializer(queryset, many=True).data)


# ------------------------------------------------------------------- watching a student

def tracking_rubric(course):
    return (Rubric.objects.filter(course=course, tracks_progress=True).first()
            or Rubric.objects.filter(course=course).first())


def judged_from_evaluations(course, student_id) -> dict:
    """What the instructor has already marked by hand, keyed by term name."""
    given = {}
    for evaluation in Evaluation.objects.filter(course=course, student_id=student_id):
        for row in evaluation.scores or []:
            name = str(row.get("name", "")).strip().lower()
            if name and row.get("awarded") is not None:
                given[name] = row["awarded"]
    return given


def rubric_progress(course, student_id, sections_available: int, rubric=None) -> dict | None:
    """Score one student against the rubric this course is tracked against."""
    from quizzes.models import Attempt, AttemptQuestion

    rubric = rubric or tracking_rubric(course)
    if rubric is None:
        return None
    attempts = list(Attempt.objects.filter(course=course, student_id=student_id))
    questions = AttemptQuestion.objects.filter(attempt__in=attempts,
                                               attempt__submitted_at__isnull=False)
    facts = gather_facts(attempts, questions, sections_available)
    result = score_against(rubric.criteria, facts,
                           judged_from_evaluations(course, student_id))
    result["rubric"] = {"id": rubric.id, "title": rubric.title}
    return result


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsFaculty])
def student_progress(request, pk, student_id):
    """One student's whole picture on one course: reading, quizzes, question by question."""
    from quizzes.models import Attempt, AttemptQuestion
    from quizzes.views import QuestionResultSerializer

    try:
        course = Course.objects.get(pk=pk, faculty=request.user)
    except Course.DoesNotExist:
        return Response({"detail": "Course not found for this instructor."}, status=404)
    try:
        enrollment = Enrollment.objects.select_related("student").get(
            course=course, student_id=student_id
        )
    except Enrollment.DoesNotExist:
        return Response({"detail": "That student has not joined this course."}, status=404)

    attempts = Attempt.objects.filter(
        course=course, student_id=student_id, submitted_at__isnull=False
    ).select_related("chapter", "module").order_by("-submitted_at")

    score = sum(attempt.score for attempt in attempts)
    total = sum(attempt.total for attempt in attempts)
    skills: dict = {}
    for question in AttemptQuestion.objects.filter(attempt__in=attempts):
        row = skills.setdefault(question.skill or "General", {"skill": question.skill,
                                                              "asked": 0, "correct": 0})
        row["asked"] += 1
        row["correct"] += 1 if question.is_correct else 0
    for row in skills.values():
        row["accuracy"] = round(row["correct"] / max(row["asked"], 1) * 100, 1)

    detail = []
    for attempt in attempts[:12]:
        detail.append({
            "attempt_id": attempt.id,
            "label": attempt.label,
            "score": attempt.score,
            "total": attempt.total,
            "percentage": attempt.percentage,
            "submitted_at": attempt.submitted_at,
            "questions": QuestionResultSerializer(attempt.questions.all(), many=True).data,
        })

    sections = Module.objects.filter(chapter__book__course=course).count() or (
        Chapter.objects.filter(book__course=course).count()
    )
    return Response({
        "rubric_progress": rubric_progress(course, student_id, sections),
        "student": {"id": enrollment.student.id, "name": enrollment.student.name,
                    "email": enrollment.student.email, "joined_at": enrollment.joined_at},
        "course": {"id": course.id, "code": course.code, "name": course.name},
        "marks": f"{score} / {total}" if total else "",
        "percentage": round(score / total * 100, 1) if total else None,
        "attempts_taken": attempts.count(),
        "skills": sorted(skills.values(), key=lambda row: row["accuracy"]),
        "attempts": detail,
        "evaluations": EvaluationSerializer(
            Evaluation.objects.filter(course=course, student_id=student_id), many=True
        ).data,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsFaculty])
def course_progress(request, pk):
    """The class list with where each student has got to."""
    from quizzes.models import Attempt

    try:
        course = Course.objects.get(pk=pk, faculty=request.user)
    except Course.DoesNotExist:
        return Response({"detail": "Course not found for this instructor."}, status=404)

    published = Chapter.objects.filter(book__course=course, status=Approval.PUBLISHED).count()
    sections = Module.objects.filter(chapter__book__course=course).count() or (
        Chapter.objects.filter(book__course=course).count()
    )
    rubric = tracking_rubric(course)
    rows = []
    for enrollment in Enrollment.objects.filter(course=course).select_related("student"):
        attempts = Attempt.objects.filter(
            course=course, student=enrollment.student, submitted_at__isnull=False
        )
        score = sum(attempt.score for attempt in attempts)
        total = sum(attempt.total for attempt in attempts)
        covered = attempts.values("chapter_id").distinct().count()
        rows.append({
            "student_id": enrollment.student.id,
            "student_name": enrollment.student.name,
            "student_email": enrollment.student.email,
            "attempts": attempts.count(),
            "marks": f"{score} / {total}" if total else "",
            "percentage": round(score / total * 100, 1) if total else None,
            "chapters_touched": covered,
            "chapters_published": published,
            "last_seen": attempts.aggregate(last=Max("submitted_at"))["last"],
            "evaluations": Evaluation.objects.filter(
                course=course, student=enrollment.student
            ).count(),
            "rubric_progress": rubric_progress(course, enrollment.student_id, sections, rubric),
        })
    rows.sort(key=lambda row: (row["percentage"] is None, -(row["percentage"] or 0)))
    return Response({
        "course": {"id": course.id, "code": course.code, "name": course.name},
        "rubric": ({"id": rubric.id, "title": rubric.title,
                    "criteria": rubric.criteria} if rubric else None),
        "students": rows,
    })


# ------------------------------------------------------------------------- downloading

def chapter_markdown(chapter) -> str:
    lines = [f"# Chapter {chapter.number}: {chapter.title}", ""]
    if chapter.explanation:
        lines += ["## Easy explanation", "", chapter.explanation, ""]
    lines += ["## From the book", "", chapter.raw_text or "", ""]
    for module in chapter.modules.all():
        lines += [f"### Module {chapter.number}.{module.number}: {module.title}", ""]
        if module.explanation:
            lines += [module.explanation, ""]
        lines += [module.raw_text or "", ""]
        for resource in module.resources.all():
            lines.append(f"Resource: {resource.title} {resource.url}".strip())
        for demo in module.demonstrations.all():
            lines.append(f"Demonstration: {demo.title}")
            for step in demo.steps or []:
                lines.append(
                    f"  {step.get('order')}. {step.get('title')} {step.get('instruction')}".strip()
                )
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def as_pdf_download(pdf_bytes: bytes, filename: str):
    from django.http import HttpResponse

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@api_view(["GET"])
def download_chapter(request, pk):
    try:
        chapter = Chapter.objects.select_related("book__course__faculty").get(pk=pk)
    except Chapter.DoesNotExist:
        return Response({"detail": "Chapter not found."}, status=404)
    course = chapter.book.course
    if not can_read_course(request.user, course):
        return Response({"detail": "You do not have access to this chapter."}, status=403)
    if request.user.is_student and chapter.status != Approval.PUBLISHED:
        return Response({"detail": "This chapter has not been published yet."}, status=403)

    from .pdf_generator import generate_chapter_pdf
    pdf = generate_chapter_pdf(chapter)
    name = f"{course.code}_chapter_{chapter.number}.pdf"
    return as_pdf_download(pdf, name)


@api_view(["GET"])
def download_module(request, pk):
    try:
        module = Module.objects.select_related("chapter__book__course__faculty").get(pk=pk)
    except Module.DoesNotExist:
        return Response({"detail": "Module not found."}, status=404)
    chapter = module.chapter
    course = chapter.book.course
    if not can_read_course(request.user, course):
        return Response({"detail": "You do not have access to this module."}, status=403)
    if request.user.is_student and chapter.status != Approval.PUBLISHED:
        return Response({"detail": "This module has not been published yet."}, status=403)

    from .pdf_generator import generate_module_pdf
    pdf = generate_module_pdf(module)
    name = f"{course.code}_module_{chapter.number}_{module.number}.pdf"
    return as_pdf_download(pdf, name)


@api_view(["GET"])
def download_book(request, pk):
    """The whole book in one PDF, chapters in order."""
    try:
        book = Book.objects.select_related("course__faculty").get(pk=pk)
    except Book.DoesNotExist:
        return Response({"detail": "Book not found."}, status=404)
    course = book.course
    if not can_read_course(request.user, course):
        return Response({"detail": "You do not have access to this book."}, status=403)

    if request.user.is_student:
        return Response(
            {"detail": "Downloading the full book is for the course instructor."}, status=403
        )

    from .pdf_generator import generate_book_pdf
    pdf = generate_book_pdf(book)
    return as_pdf_download(pdf, f"{course.code}_{book.id}_book.pdf")
