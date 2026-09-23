import random

from django.db.models import Count
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import IsFaculty, IsStudent
<<<<<<< HEAD
from courses.explain import build_explanation
=======
<<<<<<< HEAD
from courses.explain import build_explanation
=======
>>>>>>> origin/main
>>>>>>> 93b7e4dae038f4c3f883e22ae5a0f0900a8e697a
from courses.models import Approval, Chapter, Module
from courses.views import can_read_course, percentage_of

from .business import BUSINESS_PER_QUIZ, generate_business_questions, grade_typed_answer
from .generator import QUESTIONS_PER_QUIZ, TOTAL_PER_QUIZ, generate_questions
from .models import Attempt, AttemptQuestion, QuestionSet, SetAssignment, SetQuestion
from .sets import SETS_PER_SECTION, build_sets, set_for_student, touch


class QuestionPaperSerializer(serializers.ModelSerializer):
    """What a student sees while the quiz is open. The answer key stays on the server."""

    class Meta:
        model = AttemptQuestion
        fields = ["id", "order", "kind", "prompt", "options", "skill", "workbook",
                  "answer_format", "steps"]


class QuestionResultSerializer(serializers.ModelSerializer):
    correct_answer = serializers.SerializerMethodField()
    your_answer = serializers.SerializerMethodField()

    class Meta:
        model = AttemptQuestion
        fields = [
            "id", "order", "kind", "prompt", "options", "skill", "workbook",
            "correct_index", "selected_index", "typed_answer", "expected_answer",
            "answer_format", "steps", "is_correct", "correct_answer", "your_answer",
            "explanation",
        ]

    def get_correct_answer(self, obj):
        if obj.kind == AttemptQuestion.Kind.BUSINESS:
            return display_answer(obj.expected_answer, obj.answer_format)
        try:
            return obj.options[obj.correct_index]
        except (IndexError, TypeError):
            return ""

    def get_your_answer(self, obj):
        if obj.kind == AttemptQuestion.Kind.BUSINESS:
            return obj.typed_answer or "Not answered"
        if obj.selected_index is None:
            return "Not answered"
        try:
            return obj.options[obj.selected_index]
        except (IndexError, TypeError):
            return "Not answered"


def display_answer(value, answer_format):
    """Show an expected answer the way a worksheet would show it."""
    if answer_format == "text":
        return str(value)
    try:
        number = float(str(value).replace(",", ""))
    except ValueError:
        return str(value)
    if answer_format == "currency":
        return f"${number:,.2f}"
    if answer_format == "percent":
        return f"{number:g}%"
    return f"{number:,.10g}"


class AttemptSerializer(serializers.ModelSerializer):
    label = serializers.CharField(read_only=True)
    course_code = serializers.CharField(source="course.code", read_only=True)
    student_name = serializers.CharField(source="student.name", read_only=True)

    class Meta:
        model = Attempt
        fields = [
            "id", "scope", "label", "course_code", "student_name", "chapter", "module",
            "started_at", "submitted_at", "score", "total", "percentage",
        ]


<<<<<<< HEAD
=======
<<<<<<< HEAD
>>>>>>> 93b7e4dae038f4c3f883e22ae5a0f0900a8e697a
def study_text(obj, kind: str) -> str:
    """The passage the quiz is written from: the explanation the student was just given.

    A quiz should ask about what the student actually read. The explanation is the page
    they read, so it leads the passage, and the book's own words follow it as supporting
    detail. If the section has never been opened the explanation does not exist yet, so
    it is written here first, the same way the reading screen writes it.
    """
    if not obj.explanation:
        try:
            obj.explanation = build_explanation(obj.title, obj.raw_text, kind)
            obj.explained_at = timezone.now()
            obj.save(update_fields=["explanation", "explained_at"])
        except Exception:
            pass
    explanation = (obj.explanation or "").strip()
    if explanation:
        return f"{obj.title}\n{explanation}\n\nFrom the book:\n{obj.raw_text}"[:7000]
    return f"{obj.title}\n{obj.raw_text}"[:6000]


<<<<<<< HEAD
=======
=======
>>>>>>> origin/main
>>>>>>> 93b7e4dae038f4c3f883e22ae5a0f0900a8e697a
def _resolve_target(request):
    chapter_id = request.data.get("chapter_id") or request.query_params.get("chapter_id")
    module_id = request.data.get("module_id") or request.query_params.get("module_id")
    if module_id:
        try:
            module = Module.objects.select_related("chapter__book__course").get(pk=module_id)
        except Module.DoesNotExist:
            return None, Response({"detail": "Module not found."}, status=404)
        return {
            "scope": Attempt.Scope.MODULE, "module": module, "chapter": module.chapter,
            "course": module.chapter.book.course,
            "context": f"{module.chapter.title} / {module.title}",
<<<<<<< HEAD
            "source_text": study_text(module, "module"),
=======
<<<<<<< HEAD
            "source_text": study_text(module, "module"),
=======
            "source_text": f"{module.title}\n{module.raw_text}"[:6000],
>>>>>>> origin/main
>>>>>>> 93b7e4dae038f4c3f883e22ae5a0f0900a8e697a
        }, None
    if chapter_id:
        try:
            chapter = Chapter.objects.select_related("book__course").get(pk=chapter_id)
        except Chapter.DoesNotExist:
            return None, Response({"detail": "Chapter not found."}, status=404)
        return {
            "scope": Attempt.Scope.CHAPTER, "module": None, "chapter": chapter,
            "course": chapter.book.course, "context": chapter.title,
<<<<<<< HEAD
            "source_text": study_text(chapter, "chapter"),
=======
<<<<<<< HEAD
            "source_text": study_text(chapter, "chapter"),
=======
            "source_text": f"{chapter.title}\n{chapter.raw_text}"[:6000],
>>>>>>> origin/main
>>>>>>> 93b7e4dae038f4c3f883e22ae5a0f0900a8e697a
        }, None
    return None, Response({"detail": "Send a chapter_id or a module_id."}, status=400)


def build_paper(context: str, source_text: str = "") -> list[dict]:
    """Seven multiple choice questions, then three long business questions.

    Both banks are drawn against the text of the section, so a module about lookups is
    asked about lookups rather than about whatever the random draw happened to pick.
    """
    seed = random.randrange(1, 10_000_000)
    paper = generate_questions(QUESTIONS_PER_QUIZ, seed=seed, context=context,
                               source_text=source_text)
    paper += generate_business_questions(
        BUSINESS_PER_QUIZ, seed=seed + 1, start_order=QUESTIONS_PER_QUIZ + 1, context=context,
        source_text=source_text,
    )
    return paper


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsStudent])
def start_quiz(request):
    """Build a fresh ten question paper. Every start produces new questions."""
    target, error = _resolve_target(request)
    if error:
        return error
    if not can_read_course(request.user, target["course"]):
        return Response({"detail": "Join this course with its course code first."}, status=403)

    # A retake moves the student on to the next set, counted from the papers they have
    # already opened on this section.
    already = Attempt.objects.filter(student=request.user, course=target["course"])
    already = (already.filter(module=target["module"]) if target["module"]
               else already.filter(chapter=target["chapter"], module__isnull=True))
    paper = set_for_student(
        request.user,
        chapter=None if target["module"] else target["chapter"],
        module=target["module"],
        context=target["context"],
        source_text=target.get("source_text", ""),
        taken_before=already.count(),
    )
    attempt = Attempt.objects.create(
        student=request.user, course=target["course"], scope=target["scope"],
        chapter=target["chapter"], module=target["module"],
        total=paper.questions.count() or TOTAL_PER_QUIZ,
    )
    # The set is copied into the attempt, so marking and the results screen work exactly as
    # before, and an instructor editing a set later does not rewrite a paper already sat.
    for question in paper.questions.all():
        AttemptQuestion.objects.create(
            attempt=attempt,
            kind=question.kind,
            order=question.order,
            prompt=question.prompt,
            options=question.options,
            correct_index=question.correct_index,
            expected_answer=question.expected_answer,
            answer_format=question.answer_format,
            tolerance=question.tolerance,
            steps=question.steps,
            explanation=question.explanation,
            skill=question.skill,
            workbook=question.workbook,
        )
    return Response({
        "attempt": AttemptSerializer(attempt).data,
        "set_number": paper.number,
        "questions": QuestionPaperSerializer(attempt.questions.all(), many=True).data,
    }, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsStudent])
def submit_quiz(request, pk):
    try:
        attempt = Attempt.objects.get(pk=pk, student=request.user)
    except Attempt.DoesNotExist:
        return Response({"detail": "Attempt not found."}, status=404)
    if attempt.submitted_at:
        return Response({"detail": "This quiz was already submitted."}, status=400)

    given = {}
    for entry in request.data.get("answers", []):
        if entry.get("question_id") is not None:
            given[int(entry["question_id"])] = entry

    score = 0
    for question in attempt.questions.all():
        entry = given.get(question.id, {})
        if question.kind == AttemptQuestion.Kind.BUSINESS:
            typed = str(entry.get("typed_answer") or "").strip()[:120]
            question.typed_answer = typed
            question.is_correct = grade_typed_answer(
                typed, question.expected_answer, question.answer_format, question.tolerance
            )
            question.save(update_fields=["typed_answer", "is_correct"])
        else:
            chosen = entry.get("selected_index")
            question.selected_index = chosen if chosen is not None else None
            question.is_correct = chosen is not None and chosen == question.correct_index
            question.save(update_fields=["selected_index", "is_correct"])
        score += 1 if question.is_correct else 0

    attempt.score = score
    attempt.total = attempt.questions.count()
    attempt.percentage = round(score / max(attempt.total, 1) * 100, 1)
    attempt.submitted_at = timezone.now()
    attempt.save(update_fields=["score", "total", "percentage", "submitted_at"])
    return Response(_result_payload(attempt))


def _result_payload(attempt):
    questions = attempt.questions.all()
    weak = sorted({q.skill for q in questions if not q.is_correct})
    strong = sorted({q.skill for q in questions if q.is_correct})
    business = [q for q in questions if q.kind == AttemptQuestion.Kind.BUSINESS]
    business_score = sum(1 for q in business if q.is_correct)
    if attempt.percentage >= 85:
        summary = ("Strong work. You read the worksheet before answering, which is the habit "
                   "that carries into the graded case.")
    elif attempt.percentage >= 60:
        summary = ("A solid pass with room to tighten up. Re read the explanations below and "
                   "rebuild the two worksheets you missed in Excel before moving on.")
    else:
        summary = ("This one did not go your way. Work back through the easy explanation for "
                   "this section, then take the quiz again for a fresh set of questions.")
    if business and business_score < len(business):
        summary += (f" The business questions went {business_score} out of {len(business)}. "
                    "Those are the ones that carry the real work, so read their steps again and "
                    "rebuild the sheet by hand.")
    return {
        "attempt": AttemptSerializer(attempt).data,
        "correct": attempt.score,
        "wrong": attempt.total - attempt.score,
        "percentage": attempt.percentage,
        "summary": summary,
        "multiple_choice": {
            "correct": sum(1 for q in questions
                           if q.kind == AttemptQuestion.Kind.MCQ and q.is_correct),
            "total": sum(1 for q in questions if q.kind == AttemptQuestion.Kind.MCQ),
        },
        "business": {"correct": business_score, "total": len(business)},
        "skills_to_review": weak,
        "skills_secure": strong,
        "questions": QuestionResultSerializer(questions, many=True).data,
    }


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsStudent])
def check_answer(request, pk):
    """Check one business answer while the quiz is still open.

    The typed answer is stored and the student is told whether it holds up, but the
    expected value never leaves the server, so a wrong answer can be reworked in the
    sheet rather than guessed at.
    """
    try:
        attempt = Attempt.objects.get(pk=pk, student=request.user)
    except Attempt.DoesNotExist:
        return Response({"detail": "Attempt not found."}, status=404)
    if attempt.submitted_at:
        return Response({"detail": "This quiz was already submitted."}, status=400)

    try:
        question = attempt.questions.get(pk=request.data.get("question_id"))
    except AttemptQuestion.DoesNotExist:
        return Response({"detail": "That question is not on this paper."}, status=404)
    if question.kind != AttemptQuestion.Kind.BUSINESS:
        return Response({"detail": "Only business questions are checked this way."}, status=400)

    typed = str(request.data.get("typed_answer") or "").strip()[:120]
    question.typed_answer = typed
    question.is_correct = grade_typed_answer(
        typed, question.expected_answer, question.answer_format, question.tolerance
    )
    question.save(update_fields=["typed_answer", "is_correct"])
    return Response({
        "question_id": question.id,
        "typed_answer": typed,
        "is_correct": question.is_correct,
        "message": (
            "That matches the worksheet."
            if question.is_correct
            else "Not what the sheet gives. Rework it and check again before you submit."
        ),
    })


@api_view(["GET"])
def attempt_detail(request, pk):
    try:
        attempt = Attempt.objects.select_related("course").get(pk=pk)
    except Attempt.DoesNotExist:
        return Response({"detail": "Attempt not found."}, status=404)
    owner = attempt.student_id == request.user.id
    faculty = request.user.is_faculty and attempt.course.faculty_id == request.user.id
    if not (owner or faculty):
        return Response({"detail": "You cannot open this attempt."}, status=403)
    if not attempt.submitted_at:
        return Response({
            "attempt": AttemptSerializer(attempt).data,
            "questions": QuestionPaperSerializer(attempt.questions.all(), many=True).data,
        })
    return Response(_result_payload(attempt))


@api_view(["GET"])
def attempt_list(request):
    queryset = Attempt.objects.select_related("course")
    if request.user.is_faculty:
        queryset = queryset.filter(course__faculty=request.user)
    else:
        queryset = queryset.filter(student=request.user)
    course_id = request.query_params.get("course_id")
    if course_id:
        queryset = queryset.filter(course_id=course_id)
    return Response(AttemptSerializer(queryset[:100], many=True).data)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated, IsFaculty])
def preview_quiz(request):
    """Faculty can look at a generated paper, answers included, without it being graded."""
    target, error = _resolve_target(request)
    if error:
        return error
    if target["course"].faculty_id != request.user.id:
        return Response({"detail": "This is not your course."}, status=403)
    paper = build_paper(target["context"], target.get("source_text", ""))
    for question in paper:
        if question.get("kind") == "BUSINESS":
            question["expected_display"] = display_answer(
                question["expected"], question.get("format", "")
            )
    return Response({"context": target["context"], "questions": paper})


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsFaculty])
def course_performance(request, pk):
    attempts = Attempt.objects.filter(
        course_id=pk, course__faculty=request.user, submitted_at__isnull=False
    ).select_related("student")
    by_student: dict = {}
    for attempt in attempts:
        row = by_student.setdefault(attempt.student_id, {
            "student_name": attempt.student.name,
            "student_email": attempt.student.email,
            "attempts": 0, "score": 0, "total": 0,
        })
        row["attempts"] += 1
        row["score"] += attempt.score
        row["total"] += attempt.total
    rows = []
    scored = possible = 0
    for row in by_student.values():
        row["percentage"] = percentage_of(row["score"], row["total"])
        scored += row["score"]
        possible += row["total"]
        rows.append(row)
    rows.sort(key=lambda r: r["percentage"], reverse=True)
    return Response({
        # The class average is the class's marks over the marks available, which is what a
        # gradebook means by it. Averaging each attempt's percentage gives a different number
        # whenever the papers are not all the same length.
        "average_percentage": percentage_of(scored, possible) if rows else None,
        "marks": f"{scored} / {possible}" if rows else "",
        "attempts": attempts.count(),
        "students": rows,
    })


class SetQuestionSerializer(serializers.ModelSerializer):
    correct_answer = serializers.SerializerMethodField()

    class Meta:
        model = SetQuestion
        fields = ["id", "order", "kind", "prompt", "options", "correct_index",
                  "expected_answer", "answer_format", "tolerance", "steps", "explanation",
                  "skill", "workbook", "correct_answer"]
        read_only_fields = ["id", "order", "kind", "skill", "correct_answer"]

    def get_correct_answer(self, obj):
        if obj.kind == AttemptQuestion.Kind.BUSINESS:
            return display_answer(obj.expected_answer, obj.answer_format)
        try:
            return obj.options[obj.correct_index]
        except (IndexError, TypeError):
            return ""


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated, IsFaculty])
def question_sets(request):
    """The five sets for a section. POST rebuilds them from scratch."""
    target, error = _resolve_target(request)
    if error:
        return error
    if target["course"].faculty_id != request.user.id:
        return Response({"detail": "This is not your course."}, status=403)

    sets = build_sets(
        chapter=None if target["module"] else target["chapter"],
        module=target["module"],
        context=target["context"],
        source_text=target.get("source_text", ""),
        replace=request.method == "POST",
    )
    where = {"module": target["module"]} if target["module"] else {"chapter": target["chapter"]}
    handed_out = {
        row["number"]: row["n"]
        for row in SetAssignment.objects.filter(**where).values("number")
        .annotate(n=Count("id"))
    }
    return Response({
        "context": target["context"],
        "sets_per_section": SETS_PER_SECTION,
        "sets": [
            {
                "id": item.id,
                "number": item.number,
                "label": item.label,
                "edited_at": item.edited_at,
                "students_using_it": handed_out.get(item.number, 0),
                "questions": SetQuestionSerializer(item.questions.all(), many=True).data,
            }
            for item in sets
        ],
    })


@api_view(["PATCH"])
@permission_classes([IsAuthenticated, IsFaculty])
def edit_set_question(request, pk):
    """Rewrite one question in a set. Students sitting it afterwards get the new wording."""
    try:
        question = SetQuestion.objects.select_related(
            "question_set__module__chapter__book__course", "question_set__chapter__book__course"
        ).get(pk=pk)
    except SetQuestion.DoesNotExist:
        return Response({"detail": "Question not found."}, status=404)

    parent = question.question_set
    course = (parent.module.chapter.book.course if parent.module
              else parent.chapter.book.course)
    if course.faculty_id != request.user.id:
        return Response({"detail": "This question belongs to another instructor."}, status=403)

    serializer = SetQuestionSerializer(question, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    updated = serializer.save(edited_by=request.user)

    if updated.kind == AttemptQuestion.Kind.MCQ:
        if not updated.options or not 0 <= updated.correct_index < len(updated.options):
            return Response(
                {"detail": "Point the correct answer at one of the options you kept."},
                status=400,
            )
    elif not str(updated.expected_answer).strip():
        return Response({"detail": "A typed answer question needs an expected answer."},
                        status=400)

    touch(parent)
    return Response(SetQuestionSerializer(updated).data)
